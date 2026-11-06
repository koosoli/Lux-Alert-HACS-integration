"""Which alert files to read, what is cached, concurrent downloads. Knows neither Home Assistant nor the HTTP details.

The dataset has one file per CAP message and its description lists them all. A file never changes once it is
published (a change of an alert is a new message), so a file is downloaded once and kept in memory under its URL and
its last-modified stamp. A poll therefore costs one request for the description plus one per *new* file; only the
first poll after a start reads up to ``max_resources`` files.
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any, NamedTuple

from .api import DATA, TOO_LARGE, ApiError, Client, Resource
from .cap import CapError, parse_cap
from .const import FETCH_WORKERS
from .model import CapAlert

_LOGGER = logging.getLogger(__name__)

# runs a blocking function somewhere else than the event loop (hass.async_add_executor_job fits)
Executor = Callable[..., Awaitable[Any]]


class FeedResult(NamedTuple):
    cap_alerts: list[CapAlert]
    listed: int                         # alert files within the limit
    fetched: int                        # downloaded in this refresh
    cached: int                         # taken from the cache
    failed: int                         # not readable right now (network, HTTP): tried again at the next poll
    unreadable: int                     # not CAP or too large: not tried again for this version of the file
    errors: list[str]                   # a few examples of what went wrong


async def _inline(func: Callable[..., Any], *args: Any) -> Any:
    return func(*args)


class Feed:
    def __init__(self, client: Client, max_resources: int, workers: int = FETCH_WORKERS,
                 executor: Executor | None = None) -> None:
        self.client = client
        self.max_resources = max_resources
        self.workers = workers
        self._executor = executor or _inline
        # url -> (version, alerts or None when the file is not readable for good)
        self._cache: dict[str, tuple[str, list[CapAlert] | None]] = {}

    async def refresh(self) -> FeedResult:
        """Read the dataset description and the new files. Raises ApiError when the description cannot be read."""
        resources = await self.client.list_resources(self.max_resources)
        todo = []
        for resource in resources:
            entry = self._cache.get(resource.url)
            if entry is None or entry[0] != resource.modified:
                todo.append(resource)
        for url in set(self._cache) - {r.url for r in resources}:
            del self._cache[url]                                # a file that dropped out of the list: forget it
        _LOGGER.debug("The dataset lists %d alert files (limit %d): %d to read, %d cached",
                      len(resources), self.max_resources, len(todo), len(resources) - len(todo))

        semaphore = asyncio.Semaphore(max(1, self.workers))
        outcomes = await asyncio.gather(*(self._read_one(r, semaphore) for r in todo))

        fetched, failed, errors = 0, 0, []
        for resource, outcome in zip(todo, outcomes, strict=True):
            if isinstance(outcome, ApiError) and outcome.kind not in (DATA, TOO_LARGE):
                failed += 1                                     # the network or the server: try again at the next poll
                errors.append("%s: %s" % (resource.url, outcome))
                _LOGGER.debug("Could not read %s: %s", resource.url, outcome)
            elif isinstance(outcome, (ApiError, CapError)):
                self._cache[resource.url] = (resource.modified, None)   # this version will never be readable
                errors.append("%s: %s" % (resource.url, outcome))
                _LOGGER.debug("Unreadable alert file %s: %s", resource.url, outcome)
            else:
                fetched += 1
                self._cache[resource.url] = (resource.modified, outcome)
                _LOGGER.debug("Read %s: %d message(s)", resource.url, len(outcome))

        alerts: list[CapAlert] = []
        unreadable = 0
        for resource in resources:
            entry = self._cache.get(resource.url)
            if entry is None:
                continue
            if entry[1] is None:
                unreadable += 1                                 # counted at every poll, so a report does not blink
            else:
                alerts.extend(entry[1])
        return FeedResult(alerts, len(resources), fetched, len(resources) - len(todo), failed, unreadable, errors[:3])

    async def _read_one(self, resource: Resource, semaphore: asyncio.Semaphore) -> list[CapAlert] | Exception:
        """The messages of one file, or the exception that says why not (never raises)."""
        try:
            async with semaphore:
                body = await self.client.get_xml(resource.url)
            return await self._executor(parse_cap, body)
        except (ApiError, CapError) as exc:
            return exc
        except Exception as exc:                                # a parser bug must not take the poll down
            return CapError("%s: %s" % (type(exc).__name__, exc))
