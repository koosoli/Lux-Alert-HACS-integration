"""The blueprints load with Home Assistant's own blueprint schema, point at entities that exist, and render."""
from pathlib import Path

import aiohttp
import pytest
from homeassistant.components.blueprint import models
from homeassistant.components.blueprint.schemas import BLUEPRINT_SCHEMA
from homeassistant.core import HomeAssistant
from homeassistant.helpers.template import Template
from homeassistant.util import yaml as yaml_util
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.lu_alert.const import DOMAIN
from helpers import alert, mock_feed, setup_entry

FOLDER = Path(__file__).parent.parent / "custom_components" / DOMAIN / "blueprints"
FILES = sorted(FOLDER.glob("*.yaml"))


@pytest.fixture
async def integration_http_session(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, monkeypatch):
    """Keep blueprint setup tests independent of the optional pycares resolver thread."""
    connector = aiohttp.TCPConnector(resolver=aiohttp.ThreadedResolver())
    session = aiohttp.ClientSession(connector=connector)
    # Use the same request interceptor as the HA test mocker, but with a
    # test-owned session whose resolver has no background pycares thread.
    object.__setattr__(session, "_request", aioclient_mock.match_request)
    monkeypatch.setattr(
        "custom_components.lu_alert.coordinator.async_get_clientsession",
        lambda _hass: session,
    )
    try:
        yield session
    finally:
        await session.close()


def test_there_are_three_blueprints():
    assert [f.name for f in FILES] == ["allergen_alert_notification.yaml", "critical_alert_notification.yaml",
                                        "local_alert_notification.yaml"]


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_the_blueprint_is_valid(path):
    blueprint = models.Blueprint(yaml_util.load_yaml(path), expected_domain="automation", path=path.name,
                                 schema=BLUEPRINT_SCHEMA)
    assert set(blueprint.inputs) == {"notification_device", "notification_channel"}
    assert blueprint.metadata["homeassistant"]["min_version"] == "2024.10.0"


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
async def test_the_blueprint_uses_entities_the_integration_creates(
        hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, integration_http_session, path):
    mock_feed(aioclient_mock, [alert("a", description="peanuts", headline="Recall")])
    await setup_entry(hass, options={"allergens": ["peanuts"], "location_mode": "flag", "latitude": 49.6,
                                     "longitude": 6.1})
    data = yaml_util.load_yaml(path)
    trigger = data["triggers"][0]
    assert hass.states.get(trigger["entity_id"]) is not None, trigger["entity_id"]
    assert trigger["trigger"] == "state" and trigger["to"] == "on"


async def test_the_critical_blueprint_text_and_data_render(
        hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, integration_http_session):
    mock_feed(aioclient_mock, [alert("a", headline="Storm", event="Wind")])
    await setup_entry(hass)
    action = yaml_util.load_yaml(FOLDER / "critical_alert_notification.yaml")["actions"][1]
    variables = {"alert": hass.states.get("sensor.lu_alert_highest_severity").attributes}

    assert Template(action["title"], hass).async_render(variables) == "🚨 CRITICAL ALERT: Severe - Wind"
    assert Template(action["message"], hass).async_render(variables) == "Storm"
    assert Template(action["data"], hass).async_render({"notification_channel": ""}) == {"priority": "high"}
    assert Template(action["data"], hass).async_render({"notification_channel": "Alerts"}) == {
        "channel": "Alerts", "priority": "high"}


async def test_the_list_blueprints_pick_the_right_alerts(
        hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, integration_http_session):
    mock_feed(aioclient_mock, [alert("a", description="contains peanuts", headline="Recall"),
                               alert("b", description="storm", headline="Storm")])
    await setup_entry(hass, options={"allergens": ["peanuts"]})
    allergen = yaml_util.load_yaml(FOLDER / "allergen_alert_notification.yaml")["actions"][0]["variables"]
    picked = Template(allergen["allergen_alerts"], hass).async_render()
    assert [a["headline"] for a in picked] == ["Recall"]

    local = yaml_util.load_yaml(FOLDER / "local_alert_notification.yaml")["actions"][0]["variables"]
    assert Template(local["local_alerts"], hass).async_render() == []               # no location filter: no local alert
