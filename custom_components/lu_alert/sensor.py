"""Sensor platform for LU-Alert (Luxembourg)."""
from __future__ import annotations
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, DEFAULT_NAME, MAX_ALERTS
from .coordinator import LuAlertDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the LU-Alert sensors from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    sensors_to_add = [
        LuAlertMainSensor(coordinator, entry),
        LuAlertHighestSeveritySensor(coordinator, entry),
    ]

    for i in range(MAX_ALERTS):
        sensors_to_add.append(LuAlertIndexedSensor(coordinator, entry, i))

    async_add_entities(sensors_to_add)


class LuAlertBaseSensor(CoordinatorEntity[LuAlertDataUpdateCoordinator], SensorEntity):
    """Base class for LU-Alert sensors."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: LuAlertDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the base sensor."""
        super().__init__(coordinator)
        self.entry = entry
        self._attr_attribution = "Data provided by data.public.lu"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            name=DEFAULT_NAME,
            manufacturer="Luxembourg Government",
            model="LU-Alert",
            entry_type="service",
        )

    @property
    def available(self) -> bool:
        """Return if the coordinator is available."""
        return self.coordinator.last_update_success


class LuAlertMainSensor(LuAlertBaseSensor):
    """The main LU-Alert sensor, showing the number of active alerts."""

    _attr_icon = "mdi:alert-decagram"

    def __init__(
        self, coordinator: LuAlertDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the main sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{self.entry.entry_id}_main"
        self._attr_name = DEFAULT_NAME

    @property
    def native_value(self) -> int:
        """Return the number of active alerts."""
        return self.coordinator.data.get("count", 0) if self.coordinator.data else 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes, including the list of all alerts."""
        if not self.coordinator.data:
            return {}

        attrs = {}
        counts = self.coordinator.data.get("severity_counts", {})
        attrs["extreme_alerts"] = counts.get("extreme", 0)
        attrs["severe_alerts"] = counts.get("severe", 0)
        attrs["moderate_alerts"] = counts.get("moderate", 0)
        attrs["minor_alerts"] = counts.get("minor", 0)
        attrs["information_alerts"] = counts.get("information", 0)

        highest_alert = self.coordinator.data.get("highest_severity_alert")
        if highest_alert:
            attrs["highest_severity_level"] = highest_alert.get("severity")
            attrs["highest_severity_headline"] = highest_alert.get("headline")
        else:
            attrs["highest_severity_level"] = "None"
            attrs["highest_severity_headline"] = "None"

        attrs["alerts"] = self.coordinator.data.get("alerts", [])
        return attrs


class LuAlertHighestSeveritySensor(LuAlertBaseSensor):
    """A sensor that shows the highest severity level currently active."""

    def __init__(
        self, coordinator: LuAlertDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the highest severity sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{self.entry.entry_id}_highest_severity"
        self._attr_name = f"{DEFAULT_NAME} Highest Severity"

    @property
    def native_value(self) -> str:
        """Return the highest severity level of active alerts."""
        if self.coordinator.data and self.coordinator.data.get("highest_severity_alert"):
            return self.coordinator.data["highest_severity_alert"].get("severity", "None")
        return "None"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return attributes of the highest severity alert."""
        if self.coordinator.data and self.coordinator.data.get("highest_severity_alert"):
            return self.coordinator.data["highest_severity_alert"]
        return {}


class LuAlertIndexedSensor(LuAlertBaseSensor):
    """A sensor for a single alert, identified by its index."""

    _attr_has_entity_name = False  # Override base class
    _attr_icon = "mdi:alert-outline"

    def __init__(
        self, coordinator: LuAlertDataUpdateCoordinator, entry: ConfigEntry, index: int
    ) -> None:
        """Initialize the indexed sensor."""
        super().__init__(coordinator, entry)
        self.index = index
        # The unique ID needs to be stable and unique
        self._attr_unique_id = f"{self.entry.entry_id}_{index + 1}"
        # Set the full friendly name. The entity ID will be derived from this.
        self._attr_name = f"{DEFAULT_NAME} {index + 1}"

    @property
    def alert_data(self) -> dict[str, Any] | None:
        """Return the alert data for this sensor's index."""
        if self.coordinator.data and len(self.coordinator.data.get("alerts", [])) > self.index:
            return self.coordinator.data["alerts"][self.index]
        return None

    @property
    def native_value(self) -> str:
        """Return the formatted alert message."""
        if self.alert_data:
            severity = self.alert_data.get("severity", "No Severity")
            headline = self.alert_data.get("headline", "No Headline")
            structured_description = self.alert_data.get("structured_description", {})
            reason = structured_description.get("reason", "No Description")
            return f"severity level: {severity} - {headline} - Description of the alert Reason: {reason}"
        return "No Alert"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the rest of the alert data as attributes."""
        if self.alert_data:
            attrs = self.alert_data.copy()
            attrs.pop("headline", None)
            return attrs
        return {}