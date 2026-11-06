"""The HTTP client: https only, only the portal's own hosts, size limits, redirects, conditional requests."""
import aiohttp
import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.lu_alert import api
from custom_components.lu_alert.api import ApiError, Client, newest_xml_files
from custom_components.lu_alert.const import DATASET_URL

FILE = "https://data.public.lu/f/a.xml"


@pytest.fixture
async def client(aioclient_mock: AiohttpClientMocker):
    """Use a test-owned session so its resolver can be shut down deterministically."""
    connector = aiohttp.TCPConnector(resolver=aiohttp.ThreadedResolver())
    session = aiohttp.ClientSession(connector=connector)
    # Match the test utility's create_session() behavior without using HA's
    # shared session (which uses the optional aiodns/pycares resolver).
    object.__setattr__(session, "_request", aioclient_mock.match_request)
    try:
        yield Client(session, DATASET_URL)
    finally:
        await session.close()


async def test_the_listing_is_newest_first_and_only_xml(client, aioclient_mock: AiohttpClientMocker):
    aioclient_mock.get(DATASET_URL, json={"resources": [
        {"format": "xml", "url": "https://data.public.lu/f/1.xml", "last_modified": "2026-11-01T10:00:00"},
        {"format": "csv", "url": "https://data.public.lu/f/x.csv", "last_modified": "2026-11-09T10:00:00"},
        {"format": "", "mime": "application/xml", "url": "https://data.public.lu/f/3.xml", "last_modified": "2026-11-03T10:00:00"},
        {"format": "xml", "url": "https://data.public.lu/f/2.xml", "last_modified": "2026-11-02T10:00:00"},
        {"format": "xml"}, "junk", None,
    ]})
    listed = await client.list_resources(10)
    assert [r.url.rsplit("/", 1)[-1] for r in listed] == ["3.xml", "2.xml", "1.xml"]
    assert len(await client.list_resources(2)) == 2


def test_the_stamp_includes_the_checksum_so_a_changed_file_is_read_again():
    [one] = newest_xml_files([{"format": "xml", "url": "u", "last_modified": "t", "checksum": {"value": "abc"}}])
    [two] = newest_xml_files([{"format": "xml", "url": "u", "last_modified": "t", "checksum": {"value": "abd"}}])
    assert one.modified != two.modified


@pytest.mark.parametrize("url", ["http://data.public.lu/f/a.xml", "https://evil.example.com/a.xml",
                                 "https://192.168.1.10/a.xml", "https://public.lu.evil.com/a.xml", "https:///a.xml"])
async def test_a_file_outside_the_portal_is_never_requested(client, aioclient_mock: AiohttpClientMocker, url):
    with pytest.raises(ApiError) as caught:
        await client.get_xml(url)
    assert caught.value.kind in (api.CONFIG, api.BLOCKED)
    assert aioclient_mock.call_count == 0


async def test_the_domain_of_the_portal_is_allowed(client):
    assert client.host_allowed("https://data.public.lu/x")
    assert client.host_allowed("https://static.data.public.lu/x")
    assert client.host_allowed("https://public.lu/x")
    assert not client.host_allowed("https://notpublic.lu/x")
    assert not client.host_allowed("https://public.lu.example.com/x")


async def test_a_redirect_to_another_host_is_refused(client, aioclient_mock: AiohttpClientMocker):
    aioclient_mock.get(FILE, status=302, headers={"Location": "https://192.168.1.10/secret"})
    with pytest.raises(ApiError) as caught:
        await client.get_xml(FILE)
    assert caught.value.kind == api.BLOCKED
    assert aioclient_mock.call_count == 1


async def test_a_redirect_to_http_is_refused(client, aioclient_mock: AiohttpClientMocker):
    aioclient_mock.get(FILE, status=301, headers={"Location": "http://data.public.lu/f/a.xml"})
    with pytest.raises(ApiError) as caught:
        await client.get_xml(FILE)
    assert caught.value.kind == api.CONFIG


async def test_a_redirect_inside_the_portal_is_followed(client, aioclient_mock: AiohttpClientMocker):
    aioclient_mock.get(FILE, status=302, headers={"Location": "/f/b.xml"})
    aioclient_mock.get("https://data.public.lu/f/b.xml", text="<alert/>")
    assert await client.get_xml(FILE) == b"<alert/>"


async def test_redirects_in_a_circle_end(client, aioclient_mock: AiohttpClientMocker):
    aioclient_mock.get(FILE, status=302, headers={"Location": FILE})
    with pytest.raises(ApiError, match="redirects"):
        await client.get_xml(FILE)


async def test_an_answer_that_is_too_large_is_refused(client, aioclient_mock: AiohttpClientMocker, monkeypatch):
    monkeypatch.setattr(api, "MAX_XML_BYTES", 100)
    aioclient_mock.get(FILE, text="x" * 101)
    with pytest.raises(ApiError) as caught:
        await client.get_xml(FILE)
    assert caught.value.kind == api.TOO_LARGE
    aioclient_mock.clear_requests()
    aioclient_mock.get(FILE, text="x" * 100)
    assert len(await client.get_xml(FILE)) == 100


@pytest.mark.parametrize("status", [404, 500, 503])
async def test_an_http_error_is_an_error_with_the_status(client, aioclient_mock: AiohttpClientMocker, status):
    aioclient_mock.get(DATASET_URL, status=status)
    with pytest.raises(ApiError, match="HTTP %d" % status) as caught:
        await client.list_resources(10)
    assert caught.value.kind == api.HTTP


async def test_a_dataset_that_is_not_json_or_has_no_resources(client, aioclient_mock: AiohttpClientMocker):
    for body, kwargs in (("<html>maintenance</html>", {}), ('{"resources": "no"}', {}), ("[]", {})):
        aioclient_mock.clear_requests()
        aioclient_mock.get(DATASET_URL, text=body, **kwargs)
        with pytest.raises(ApiError) as caught:
            await client.list_resources(10)
        assert caught.value.kind == api.DATA


async def test_the_dataset_request_is_conditional_when_the_server_says_so(client, aioclient_mock: AiohttpClientMocker):
    aioclient_mock.get(DATASET_URL, json={"resources": [{"format": "xml", "url": FILE, "last_modified": "t"}]},
                       headers={"ETag": '"v1"', "Last-Modified": "Mon, 02 Nov 2026 10:00:00 GMT"})
    first = await client.list_resources(10)
    assert "If-None-Match" not in aioclient_mock.mock_calls[0][3]

    aioclient_mock.clear_requests()
    aioclient_mock.get(DATASET_URL, status=304)
    again = await client.list_resources(10)
    assert again == first                                                           # the cached copy
    headers = aioclient_mock.mock_calls[0][3]
    assert headers["If-None-Match"] == '"v1"' and headers["If-Modified-Since"].startswith("Mon, 02 Nov 2026")


async def test_a_304_without_a_cached_copy_is_an_error(client, aioclient_mock: AiohttpClientMocker):
    aioclient_mock.get(DATASET_URL, status=304)
    with pytest.raises(ApiError):
        await client.list_resources(10)


async def test_the_client_names_itself(client, aioclient_mock: AiohttpClientMocker):
    aioclient_mock.get(DATASET_URL, json={"resources": []})
    await client.list_resources(10)
    assert aioclient_mock.mock_calls[0][3]["User-Agent"].startswith("Lux-Alert-HACS-integration")
