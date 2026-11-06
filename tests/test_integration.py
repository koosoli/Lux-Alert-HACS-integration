"""The integration in a real Home Assistant: set-up, entities, outage, expiry, options, location, card."""
from datetime import timedelta

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import async_fire_time_changed
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from cap_samples import CITY, ESCH, HOME, cap_xml, info_xml, reference
from helpers import alert, mock_feed, now, setup_entry, times

ESCH_HOME = (49.4958, 5.9806)                                                        # inside the ESCH polygon
MAIN = "sensor.lu_alert"
HIGHEST = "sensor.lu_alert_highest_severity"
FEED = "binary_sensor.lu_alert_feed_connection"


async def test_the_entities_have_the_ids_the_readme_names(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker):
    mock_feed(aioclient_mock, [alert("LU.1")])
    entry = await setup_entry(hass)
    assert entry.state is ConfigEntryState.LOADED
    assert sorted(hass.states.async_entity_ids()) == sorted([
        "sensor.lu_alert", "sensor.lu_alert_highest_severity", "sensor.lu_alert_1", "sensor.lu_alert_2",
        "sensor.lu_alert_3", "binary_sensor.lu_alert_critical_alert_active", "binary_sensor.lu_alert_severe_alert_active",
        "binary_sensor.lu_alert_extreme_alert_active", "binary_sensor.lu_alert_local_alert_active",
        "binary_sensor.lu_alert_watchlist_match", "binary_sensor.lu_alert_allergen_match", FEED])


async def test_an_alert_in_force(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker):
    mock_feed(aioclient_mock, [alert("LU.1", polygon=CITY, categories=("Met", "Safety"))])
    await setup_entry(hass)
    assert hass.states.get(MAIN).state == "1"
    assert hass.states.get(HIGHEST).state == "Severe"
    assert hass.states.get("binary_sensor.lu_alert_critical_alert_active").state == "on"
    assert hass.states.get("binary_sensor.lu_alert_severe_alert_active").state == "on"
    assert hass.states.get("binary_sensor.lu_alert_extreme_alert_active").state == "off"
    assert hass.states.get(FEED).state == "on"

    first = hass.states.get("sensor.lu_alert_1")
    assert first.state == "Storm warning for the whole country"
    attrs = first.attributes
    assert attrs["description"] == "Strong winds expected. Gusts up to 110 km/h."     # plain text, not <ns0:p ...>
    assert attrs["severity"] == "Severe" and attrs["level_code"] == "N2"
    assert attrs["category"] == ["Met", "Safety"]
    assert attrs["area"][0]["polygons"] == [CITY]
    assert hass.states.get("sensor.lu_alert_2").state == "No Alert"
    assert hass.states.get(MAIN).attributes["alerts"][0]["identifier"] == "LU.1"
    assert hass.states.get(MAIN).attributes["severe_alerts"] == 1


async def test_nothing_in_force_is_all_clear(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker):
    mock_feed(aioclient_mock, [])
    await setup_entry(hass)
    assert hass.states.get(MAIN).state == "0"
    assert hass.states.get(HIGHEST).state == "None"
    assert hass.states.get(FEED).state == "on"


async def test_what_the_live_feed_does(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker):
    """The shapes that broke the first version: the TEST level with status Actual, a siren block first, double escaping,
    the same recall published again under a new number."""
    ends = now() + timedelta(days=4)
    mock_feed(aioclient_mock, [
        alert("t", level="TEST", status="Actual", headline="Monthly test"),
        alert("siren", level="ALERT_LVL_2", languages=("en",), channels=("Siren", "Mobile-App"), headline="Real text"),
        cap_xml("e", **times(infos=[info_xml(description="The &amp;quot;end&amp;quot; date", level="ALERT_LVL_4",
                                             headline="Escaped")])),
        cap_xml("r1", **times(sent=now() - timedelta(days=3), expires=ends, level="ALERT_LVL_3", headline="Recall: cabbage")),
        cap_xml("r2", **times(sent=now() - timedelta(hours=2), expires=ends, level="ALERT_LVL_3", headline="Recall: cabbage")),
    ])
    await setup_entry(hass)
    headlines = [a["headline"] for a in hass.states.get(MAIN).attributes["alerts"]]
    assert sorted(headlines) == ["Escaped", "Real text", "Recall: cabbage"]          # no test, no siren stub, one recall
    escaped = next(a for a in hass.states.get(MAIN).attributes["alerts"] if a["headline"] == "Escaped")
    assert escaped["description"] == 'The "end" date'
    assert hass.states.get(HIGHEST).state == "Severe"
    assert hass.states.get(FEED).attributes["ignored_tests"] == 1


async def test_cancel_and_update(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker):
    long_ago = now() - timedelta(hours=3)
    mock_feed(aioclient_mock, [
        alert("a", sent=long_ago, headline="old"),
        alert("b", sent=now() - timedelta(hours=1), msg_type="Update", headline="new", references=reference("a", long_ago)),
        alert("c", sent=now() - timedelta(hours=4), headline="cancelled"),
        alert("x", sent=now() - timedelta(minutes=2), msg_type="Cancel", references=reference("c", now() - timedelta(hours=4))),
    ])
    await setup_entry(hass)
    assert [a["headline"] for a in hass.states.get(MAIN).attributes["alerts"]] == ["new"]


async def test_files_are_downloaded_once(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker):
    mock_feed(aioclient_mock, [alert(f"LU.{i}", headline=f"h{i}") for i in range(20)])
    entry = await setup_entry(hass)
    assert aioclient_mock.call_count == 21                                          # the dataset and 20 files
    await entry.runtime_data.async_refresh()
    assert aioclient_mock.call_count == 22                                          # only the dataset again
    assert hass.states.get(MAIN).state == "20"


async def test_an_outage_keeps_the_last_known_alerts(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, caplog):
    mock_feed(aioclient_mock, [alert("LU.1")])
    entry = await setup_entry(hass)
    coordinator = entry.runtime_data
    assert hass.states.get(MAIN).state == "1"

    mock_feed(aioclient_mock, [], dataset_status=500)
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(MAIN).state == "1"                                       # not "all clear"
    assert hass.states.get("binary_sensor.lu_alert_critical_alert_active").state == "on"
    assert hass.states.get(FEED).state == "off"
    assert "HTTP 500" in hass.states.get(FEED).attributes["last_error"]
    assert coordinator.update_interval == timedelta(seconds=300)                    # the first retry: the normal interval
    await coordinator.async_refresh()                                               # a second failure: logged once only
    assert coordinator.update_interval == timedelta(seconds=600)                    # backoff
    assert sum("feed poll failed" in r.message for r in caplog.records if r.levelname == "WARNING") == 1

    mock_feed(aioclient_mock, [alert("LU.1")])
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(FEED).state == "on"
    assert coordinator.update_interval == timedelta(seconds=300)
    assert "answers again" in caplog.text


async def test_a_first_poll_that_fails_is_retried_by_home_assistant(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker):
    mock_feed(aioclient_mock, [], dataset_status=500)
    entry = await setup_entry(hass)
    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert "HTTP 500" in (entry.reason or "")                                       # not a bug that only looks like one
    assert hass.states.get(MAIN) is None


async def test_a_file_that_cannot_be_read_does_not_stop_the_others(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker):
    mock_feed(aioclient_mock, [alert("LU.1"), "this is not CAP"])
    entry = await setup_entry(hass)
    assert entry.state is ConfigEntryState.LOADED
    assert hass.states.get(MAIN).state == "1"
    assert hass.states.get(FEED).attributes["files_unreadable"] == 1


async def test_an_alert_ends_on_time_without_a_poll(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, freezer):
    mock_feed(aioclient_mock, [alert("short", expires=now() + timedelta(seconds=120), headline="short"),
                               alert("long", headline="long")])
    await setup_entry(hass)
    assert hass.states.get(MAIN).state == "2"
    calls = aioclient_mock.call_count

    freezer.tick(timedelta(seconds=200))                                            # before the next poll at 300 s
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(MAIN).state == "1"
    assert hass.states.get("sensor.lu_alert_1").state == "long"
    assert aioclient_mock.call_count == calls


async def test_minimum_severity(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker):
    mock_feed(aioclient_mock, [alert("minor", level="N3", headline="minor"), alert("severe", level="N2", headline="severe")])
    await setup_entry(hass, options={"min_severity": "Severe"})
    assert [a["headline"] for a in hass.states.get(MAIN).attributes["alerts"]] == ["severe"]


async def test_test_alerts_are_left_out_unless_asked_for(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker):
    mock_feed(aioclient_mock, [alert("minor", level="N3", headline="minor"), alert("t", level="T", headline="test")])
    await setup_entry(hass, options={"show_test_alerts": True})
    assert [a["severity"] for a in hass.states.get(MAIN).attributes["alerts"]] == ["Minor", "Test"]


async def test_changing_the_options_applies_them_at_once(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker):
    mock_feed(aioclient_mock, [alert("minor", level="N3", headline="minor"), alert("severe", level="N2", headline="severe")])
    entry = await setup_entry(hass)
    assert hass.states.get(MAIN).state == "2"
    hass.config_entries.async_update_entry(entry, options={"min_severity": "Severe"})
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert [a["headline"] for a in hass.states.get(MAIN).attributes["alerts"]] == ["severe"]


HERE = {"latitude": HOME[0], "longitude": HOME[1]}
LOCATION_DOCUMENTS = [alert("in", polygon=CITY, headline="in"), alert("out", polygon=ESCH, headline="out"),
                      alert("anywhere", headline="anywhere")]


async def test_the_location_filter_can_flag(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker):
    mock_feed(aioclient_mock, LOCATION_DOCUMENTS)
    await setup_entry(hass, options={"location_mode": "flag", **HERE})
    by_name = {a["headline"]: a["is_local"] for a in hass.states.get(MAIN).attributes["alerts"]}
    assert by_name == {"in": True, "out": False, "anywhere": None}                   # nothing dropped, only flagged
    assert hass.states.get("binary_sensor.lu_alert_local_alert_active").state == "on"


async def test_the_location_filter_can_hide_what_is_elsewhere(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker):
    mock_feed(aioclient_mock, LOCATION_DOCUMENTS)
    await setup_entry(hass, options={"location_mode": "only", **HERE})
    assert sorted(a["headline"] for a in hass.states.get(MAIN).attributes["alerts"]) == ["anywhere", "in"]


async def test_without_a_custom_location_the_home_of_home_assistant_is_used(hass: HomeAssistant,
                                                                          aioclient_mock: AiohttpClientMocker):
    await hass.config.async_update(latitude=ESCH_HOME[0], longitude=ESCH_HOME[1])
    mock_feed(aioclient_mock, LOCATION_DOCUMENTS)
    await setup_entry(hass, options={"location_mode": "only"})
    assert sorted(a["headline"] for a in hass.states.get(MAIN).attributes["alerts"]) == ["anywhere", "out"]


async def test_watchlist_and_allergens(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker):
    mock_feed(aioclient_mock, [alert("a", description="Product recall: contains PEANUTS, not declared.", headline="Recall")])
    await setup_entry(hass, options={"watchlist_keywords": "flood, peanuts", "allergens": ["Peanuts"]})
    assert hass.states.get("binary_sensor.lu_alert_watchlist_match").state == "on"
    assert hass.states.get("binary_sensor.lu_alert_allergen_match").state == "on"


async def test_without_options_watchlist_and_allergens_are_off(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker):
    mock_feed(aioclient_mock, [alert("a", description="peanuts")])
    await setup_entry(hass)
    assert hass.states.get("binary_sensor.lu_alert_watchlist_match").state == "off"
    assert hass.states.get("binary_sensor.lu_alert_allergen_match").state == "off"


async def test_a_long_headline_fits_a_state(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker):
    mock_feed(aioclient_mock, [alert("a", headline="H" * 400)])
    await setup_entry(hass)
    state = hass.states.get("sensor.lu_alert_1")
    assert len(state.state) == 255 and state.state.endswith("...")
    assert state.attributes["headline"] == "H" * 400


async def test_unload_and_reload(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker):
    mock_feed(aioclient_mock, [alert("a")])
    entry = await setup_entry(hass)
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(MAIN).state == "1"



async def test_the_set_up_works_with_lovelace_loaded(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker):
    """The first version read hass.data["lovelace"] like a dict and failed to set up on every real installation."""
    assert await async_setup_component(hass, "lovelace", {})
    mock_feed(aioclient_mock, [alert("a")])
    entry = await setup_entry(hass)
    assert entry.state is ConfigEntryState.LOADED
    assert hass.states.get(MAIN).state == "1"
