"""The dashboard card is served by the integration and registered as an extra module of the frontend."""
from pathlib import Path

import aiohttp
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.lu_alert.const import CARD_FILE, DOMAIN, STATIC_URL
from helpers import alert, mock_feed, setup_entry

WWW = Path(__file__).parent.parent / "custom_components" / DOMAIN / "www"


@pytest.fixture
async def integration_http_session(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, monkeypatch):
    """Use a test-owned session for the coordinator, avoiding the optional pycares resolver thread."""
    connector = aiohttp.TCPConnector(resolver=aiohttp.ThreadedResolver())
    session = aiohttp.ClientSession(connector=connector)
    object.__setattr__(session, "_request", aioclient_mock.match_request)
    monkeypatch.setattr(
        "custom_components.lu_alert.coordinator.async_get_clientsession",
        lambda _hass: session,
    )
    try:
        yield session
    finally:
        await session.close()


async def test_the_card_and_leaflet_are_served(
        hass: HomeAssistant, hass_client, aioclient_mock: AiohttpClientMocker, integration_http_session):
    mock_feed(aioclient_mock, [alert("a")])
    assert await async_setup_component(hass, "http", {})
    await setup_entry(hass)
    client = await hass_client()

    for name in (CARD_FILE, "leaflet.js", "leaflet.css"):
        response = await client.get(f"{STATIC_URL}/{name}")
        assert response.status == 200, name
        assert await response.read() == (WWW / name).read_bytes()
    assert (await client.get(f"{STATIC_URL}/lu-alert-card.js")).content_type in ("text/javascript", "application/javascript")


async def test_the_card_module_is_loaded_by_the_frontend(
        hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, integration_http_session):
    from homeassistant.components.frontend import DATA_EXTRA_MODULE_URL, UrlManager

    # The real frontend needs the hass_frontend package (50 MB) that the test plugin does not install: what matters
    # here is that the integration registers its module with the list of extra modules the frontend keeps.
    assert await async_setup_component(hass, "http", {})
    hass.config.components.add("frontend")
    hass.data[DATA_EXTRA_MODULE_URL] = UrlManager(lambda *args: None, [])
    mock_feed(aioclient_mock, [])
    await setup_entry(hass)
    urls = [str(u) for u in hass.data[DATA_EXTRA_MODULE_URL].urls]
    assert any(u.startswith(f"{STATIC_URL}/{CARD_FILE}?v=0.1.0") for u in urls), urls


async def test_without_a_frontend_the_set_up_still_works(
        hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, integration_http_session):
    mock_feed(aioclient_mock, [alert("a")])
    entry = await setup_entry(hass)
    assert hass.states.get("sensor.lu_alert").state == "1"
    assert entry.runtime_data is not None
