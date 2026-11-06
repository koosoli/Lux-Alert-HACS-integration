"""Sensor platform for LU-Alert (Luxembourg)."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .attributes import UNRECORDED, alert_attributes, snapshot_attributes
from .const import DEFAULT_NAME, MAX_ALERTS, MAX_STATE_LENGTH, SEVERITIES
from .coordinator import LuAlertCoordinator
from .entity import LuAlertEntity
from .util import shorten

NO_ALERT = "None"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the LU-Alert sensors from a config entry."""
    coordinator: LuAlertCoordinator = entry.runtime_data
    sensors: list[LuAlertEntity] = [LuAlertMainSensor(coordinator), LuAlertHighestSeveritySensor(coordinator)]
    sensors.extend(LuAlertIndexedSensor(coordinator, index) for index in range(MAX_ALERTS))
    async_add_entities(sensors)


class LuAlertMainSensor(LuAlertEntity, SensorEntity):
    """The main LU-Alert sensor: the number of active alerts, with all of them in its attributes."""

    _attr_icon = "mdi:alert-decagram"
    _attr_name = None                       # the main entity of the device: entity id sensor.lu_alert
    _unrecorded_attributes = UNRECORDED

    def __init__(self, coordinator: LuAlertCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._entry_id}_main"

    @property
    def native_value(self) -> int:
        return self.feed.snapshot.total if self.feed else 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if not self.feed:
            return {}
        snapshot = self.feed.snapshot
        counts = snapshot.counts
        top = snapshot.alerts[0] if snapshot.alerts else None
        return {
            "extreme_alerts": counts.get("Extreme", 0),
            "severe_alerts": counts.get("Severe", 0),
            "moderate_alerts": counts.get("Moderate", 0),
            "minor_alerts": counts.get("Minor", 0),
            "information_alerts": counts.get("Information", 0),
            "highest_severity_level": top.severity if top else NO_ALERT,
            "highest_severity_headline": top.headline if top else NO_ALERT,
            "next_expiry": snapshot.next_expiry.isoformat() if snapshot.next_expiry else None,
            "alerts": snapshot_attributes(snapshot),
        }


class LuAlertHighestSeveritySensor(LuAlertEntity, SensorEntity):
    """The highest severity among the active alerts, with the details of that alert in its attributes."""

    _attr_name = "Highest severity"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [NO_ALERT, *SEVERITIES]
    _unrecorded_attributes = UNRECORDED

    def __init__(self, coordinator: LuAlertCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._entry_id}_highest_severity"

    @property
    def native_value(self) -> str:
        if self.feed and self.feed.snapshot.alerts:
            return self.feed.snapshot.alerts[0].severity
        return NO_ALERT

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if self.feed and self.feed.snapshot.alerts:
            return alert_attributes(self.feed.snapshot.alerts[0])
        return {}


class LuAlertIndexedSensor(LuAlertEntity, SensorEntity):
    """One alert, by position: the state is the headline, the attributes are the rest."""

    _attr_has_entity_name = False           # the name is the whole name: entity id sensor.lu_alert_1
    _attr_icon = "mdi:alert-outline"
    _unrecorded_attributes = UNRECORDED

    def __init__(self, coordinator: LuAlertCoordinator, index: int) -> None:
        super().__init__(coordinator)
        self.index = index
        self._attr_unique_id = f"{self._entry_id}_{index + 1}"
        self._attr_name = f"{DEFAULT_NAME} {index + 1}"

    @property
    def _alert(self):
        alerts = self.feed.snapshot.alerts if self.feed else ()
        return alerts[self.index] if len(alerts) > self.index else None

    @property
    def native_value(self) -> str:
        alert = self._alert
        # a state is at most 255 characters; the full headline is in the attributes
        return shorten(alert.headline, MAX_STATE_LENGTH) if alert else "No Alert"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        alert = self._alert
        return alert_attributes(alert) if alert else {}
