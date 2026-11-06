"""The config flow and the options flow, in a real Home Assistant."""
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.lu_alert.const import DOMAIN
from helpers import alert, mock_feed, setup_entry


async def test_the_user_step_creates_the_entry(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker):
    mock_feed(aioclient_mock, [alert("a")])
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"min_severity": "minor"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "LU-Alert" and result["data"] == {"min_severity": "minor"}
    await hass.async_block_till_done()
    [entry] = hass.config_entries.async_entries(DOMAIN)
    assert entry.state is ConfigEntryState.LOADED


async def test_only_one_instance(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker):
    mock_feed(aioclient_mock, [])
    await setup_entry(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_the_options_flow_stores_every_option(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker):
    mock_feed(aioclient_mock, [alert("a", level="N3", headline="minor"), alert("b", level="N2", headline="severe")])
    entry = await setup_entry(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "init"
    options = {"min_severity": "severe", "language": "de", "location_mode": "flag", "latitude": 49.6, "longitude": 6.1,
               "watchlist_keywords": "flood, storm", "allergens": ["Peanuts", "Kiwi"], "show_test_alerts": True}
    result = await hass.config_entries.options.async_configure(result["flow_id"], options)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert dict(entry.options) == options
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED                                   # reloaded with the new options
    assert [a["headline"] for a in hass.states.get("sensor.lu_alert").attributes["alerts"]] == ["severe"]


async def test_the_options_form_starts_with_what_is_set(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker):
    mock_feed(aioclient_mock, [])
    entry = await setup_entry(hass, options={"language": "fr"}, data={"min_severity": "Moderate"})
    result = await hass.config_entries.options.async_init(entry.entry_id)
    defaults = {str(key): key.default() for key in result["data_schema"].schema if key.default is not None
                and callable(key.default) and key.default() is not None}
    assert defaults["min_severity"] == "moderate"                                   # from the data of the first set-up
    assert defaults["language"] == "fr"
    assert defaults["location_mode"] == "off"


async def test_half_a_location_is_refused(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker):
    mock_feed(aioclient_mock, [])
    entry = await setup_entry(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"min_severity": "unknown", "language": "en", "location_mode": "only", "latitude": 49.6,
                            "show_test_alerts": False})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "location_incomplete"}


async def test_a_location_out_of_range_is_refused(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker):
    mock_feed(aioclient_mock, [])
    entry = await setup_entry(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    try:
        await hass.config_entries.options.async_configure(
            result["flow_id"], {"min_severity": "Unknown", "language": "en", "location_mode": "only", "latitude": 99,
                                "longitude": 6, "show_test_alerts": False})
    except Exception as exc:                                                        # the schema rejects the answer
        assert "latitude" in str(exc) or "99" in str(exc) or "Invalid" in type(exc).__name__ or "expected" in str(exc)
    else:
        raise AssertionError("a latitude of 99 was accepted")
