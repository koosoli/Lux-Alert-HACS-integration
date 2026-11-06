"""Async HTTP client for the LU-Alert dataset on data.public.lu. No Home Assistant imports except the aiohttp session.

Two requests exist: the description of the dataset (a JSON document that lists one file per CAP message) and one
alert file. Both go over https only (a redirect to http is refused), the certificate is always verified, every answer
is size-limited (also after decompression), and the dataset request is conditional (ETag / Last-Modified) when the
server supports it.

The file addresses come out of the dataset description, so they are not trusted blindly: a file is only requested
from the host of the dataset or from a host in the same domain (``data.public.lu`` -> ``*.public.lu``). An address
anywhere else is never requested, and neither is a redirect to one: it could point Home Assistant at a device in your
own network.
"""
from __future__ import annotations

import asyncio
import ipaddress
import json
from collections.abc import Iterable
from typing import Any, NamedTuple
from urllib.parse import urljoin, urlsplit

import aiohttp

from .const import HTTP_TIMEOUT, MAX_DATASET_BYTES, MAX_XML_BYTES, PROJECT_URL

USER_AGENT = "Lux-Alert-HACS-integration (+%s)" % PROJECT_URL
MAX_REDIRECTS = 5

# error kinds: the coordinator decides what to tell the person from them
NETWORK, HTTP, DATA, TOO_LARGE, CONFIG, BLOCKED = "network", "http", "data", "too-large", "config", "blocked"


class ApiError(Exception):
    def __init__(self, message: str, kind: str = NETWORK) -> None:
        super().__init__(message)
        self.kind = kind


class Resource(NamedTuple):
    """One alert file of the dataset."""

    url: str
    modified: str                   # "last_modified|checksum": tells whether the file changed, and sorts by age
    title: str = ""


def _family(host: str) -> str:
    """The domain a file may come from: the last two labels of a host name (``data.public.lu`` -> ``public.lu``);
    an IP address or a single-label name stands for itself."""
    try:
        ipaddress.ip_address(host)
        return host
    except ValueError:
        pass
    labels = host.split(".")
    return ".".join(labels[-2:]) if len(labels) > 2 else host


async def _read_limited(response: aiohttp.ClientResponse, limit: int, what: str) -> bytes:
    """The body of a response, decompressed, at most ``limit`` bytes (an ApiError otherwise).

    aiohttp decompresses while it reads, so the limit applies to the decompressed bytes: a gzip bomb stops at the limit.
    """
    declared = response.headers.get("Content-Length")
    if declared and declared.isdigit() and int(declared) > limit and not response.headers.get("Content-Encoding"):
        raise ApiError("%s is larger than %d bytes" % (what, limit), TOO_LARGE)
    chunks: list[bytes] = []
    size = 0
    try:
        async for chunk in response.content.iter_chunked(64 * 1024):
            size += len(chunk)
            if size > limit:
                raise ApiError("%s is larger than %d bytes" % (what, limit), TOO_LARGE)
            chunks.append(chunk)
    except aiohttp.ClientPayloadError as exc:
        raise ApiError("%s: the answer was cut off or is not valid compressed data: %s" % (what, exc), DATA) from exc
    return b"".join(chunks)


class Client:
    def __init__(self, session: aiohttp.ClientSession, dataset_url: str, timeout: int = HTTP_TIMEOUT,
                 user_agent: str = USER_AGENT, allowed_hosts: Iterable[str] = ()) -> None:
        self._session = session
        self.dataset_url = dataset_url
        self.timeout = timeout
        self.user_agent = user_agent
        self._home = (urlsplit(dataset_url).hostname or "").lower().rstrip(".")
        self._family = _family(self._home)
        self._extra = tuple(h.lower().strip().strip(".") for h in allowed_hosts if h.strip().strip("."))
        self._etag: str | None = None
        self._modified: str | None = None
        self._last_list: list[Resource] | None = None

    def host_allowed(self, url: str) -> bool:
        """May this client request ``url``? The dataset's own host, its domain, or an extra allowed host."""
        try:
            host = (urlsplit(url).hostname or "").lower().rstrip(".")
        except ValueError:
            return False
        if not host:
            return False
        if host == self._home or host == self._family or host.endswith("." + self._family):
            return True
        return any(host == extra or host.endswith("." + extra) for extra in self._extra)

    # -- requests -------------------------------------------------------------------------------------------
    async def _get(self, url: str, accept: str, limit: int, what: str,
                   headers: dict[str, str] | None = None) -> tuple[bytes | None, Any]:
        """(body, response headers) of ``url``; (None, None) for HTTP 304. Raises ApiError."""
        request_headers = {"User-Agent": self.user_agent, "Accept": accept, **(headers or {})}
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        current = url
        for _ in range(MAX_REDIRECTS + 1):
            if urlsplit(current).scheme.lower() != "https":
                raise ApiError("%s: only https URLs are used, got %s" % (what, current.split("?")[0]), CONFIG)
            if not self.host_allowed(current):
                raise ApiError("%s: %s is not a host of the data portal (%s) and is not requested"
                               % (what, urlsplit(current).hostname or "?", self._family), BLOCKED)
            try:
                async with self._session.get(current, headers=request_headers, timeout=timeout,
                                             allow_redirects=False) as response:
                    if response.status == 304:
                        return None, None
                    if response.status in (301, 302, 303, 307, 308):
                        location = response.headers.get("Location")
                        if not location:
                            raise ApiError("%s: HTTP %d without a Location" % (what, response.status), HTTP)
                        current = urljoin(current, location)
                        continue
                    if response.status >= 400:
                        raise ApiError("%s: HTTP %d" % (what, response.status), HTTP)
                    return await _read_limited(response, limit, what), response.headers
            except ApiError:
                raise
            except asyncio.TimeoutError as exc:
                raise ApiError("%s: no answer within %d s" % (what, self.timeout), NETWORK) from exc
            except aiohttp.ClientConnectorCertificateError as exc:
                raise ApiError("%s: TLS error: the certificate of the server is not trusted (%s)"
                               % (what, exc), NETWORK) from exc
            except (aiohttp.ClientError, OSError, ValueError) as exc:
                raise ApiError("%s: %s: %s" % (what, type(exc).__name__, exc), NETWORK) from exc
        raise ApiError("%s: more than %d redirects" % (what, MAX_REDIRECTS), HTTP)

    async def list_resources(self, max_resources: int) -> list[Resource]:
        """The newest alert files of the dataset, newest first."""
        headers = {}
        if self._etag and self._last_list is not None:
            headers["If-None-Match"] = self._etag
        if self._modified and self._last_list is not None:
            headers["If-Modified-Since"] = self._modified
        body, seen = await self._get(self.dataset_url, "application/json", MAX_DATASET_BYTES,
                                     "dataset description", headers)
        if body is None:
            if self._last_list is None:
                raise ApiError("dataset description: HTTP 304 without a cached copy", DATA)
            return self._last_list[:max_resources]
        try:
            data = json.loads(body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise ApiError("dataset description: the answer is not JSON (did the data portal change its API?)",
                           DATA) from exc
        resources = data.get("resources") if isinstance(data, dict) else None
        if not isinstance(resources, list):
            raise ApiError("dataset description: no 'resources' list in the answer", DATA)
        listed = newest_xml_files(resources)
        self._last_list = listed
        self._etag = seen.get("ETag") if seen is not None else None
        self._modified = seen.get("Last-Modified") if seen is not None else None
        return listed[:max_resources]

    async def get_xml(self, url: str) -> bytes:
        body, _ = await self._get(url, "application/xml, text/xml", MAX_XML_BYTES, "alert file")
        if body is None:
            raise ApiError("alert file: unexpected HTTP 304", DATA)
        return body


def newest_xml_files(resources: list[Any]) -> list[Resource]:
    found = []
    for item in resources:
        if not isinstance(item, dict) or not isinstance(item.get("url"), str):
            continue
        fmt = str(item.get("format") or "").lower()
        mime = str(item.get("mime") or "").lower()
        if fmt != "xml" and "xml" not in mime:
            continue
        checksum = item.get("checksum")
        digest = checksum.get("value", "") if isinstance(checksum, dict) else ""
        stamp = str(item.get("last_modified") or item.get("published") or item.get("created_at") or "")
        found.append(Resource(item["url"], "%s|%s" % (stamp, digest), str(item.get("title") or "")))
    found.sort(key=lambda r: r.modified, reverse=True)
    return found
