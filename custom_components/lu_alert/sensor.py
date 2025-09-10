"""Sensor platform for LU-Alert (Luxembourg)."""
from __future__ import annotations
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, DEFAULT_NAME
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
    async_add_entities(sensors_to_add)


class LuAlertMainSensor(CoordinatorEntity[LuAlertDataUpdateCoordinator], SensorEntity):
    """The main LU-Alert sensor, showing the number of active alerts."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:alert-decagram"

    def __init__(
        self, coordinator: LuAlertDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the main sensor."""
        super().__init__(coordinator)
        self.entry = entry
        self._attr_attribution = "Data provided by data.public.lu"
        self._attr_unique_id = f"{self.entry.entry_id}_main"
        self._attr_name = DEFAULT_NAME

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            name=DEFAULT_NAME,
            manufacturer="Luxembourg Government",
            model="LU-Alert",
            entry_type="service",
        )

    @property
    def native_value(self) -> int:
        """Return the number of active alerts."""
        if self.coordinator.data:
            return self.coordinator.data.get("count", 0)
        return 0

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the state attributes, including the list of all alerts."""
        if not self.coordinator.data:
            return None

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

        # Add the full list of alerts
        attrs["alerts"] = self.coordinator.data.get("alerts", [])

        return attrs

    @property
    def available(self) -> bool:
        """Return if the sensor is available."""
        return super().available and self.coordinator.data is not None


class LuAlertHighestSeveritySensor(
    CoordinatorEntity[LuAlertDataUpdateCoordinator], SensorEntity
):
    """A sensor that shows the highest severity level currently active."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: LuAlertDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the highest severity sensor."""
        super().__init__(coordinator)
        self.entry = entry
        self._attr_attribution = "Data provided by data.public.lu"
        self._attr_unique_id = f"{self.entry.entry_id}_highest_severity"
        self._attr_name = f"{DEFAULT_NAME} Highest Severity"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            name=DEFAULT_NAME,
            manufacturer="Luxembourg Government",
            model="LU-Alert",
            entry_type="service",
        )

    @property
    def native_value(self) -> str:
        """Return the highest severity level of active alerts."""
        if self.coordinator.data and self.coordinator.data.get("highest_severity_alert"):
            return self.coordinator.data["highest_severity_alert"].get("severity", "None")
        return "None"

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return attributes of the highest severity alert."""
        if self.coordinator.data and self.coordinator.data.get("highest_severity_alert"):
            alert = self.coordinator.data["highest_severity_alert"]
            return {
                "headline": alert.get("headline"),
                "event": alert.get("event"),
                "sent": alert.get("sent"),
                "expires": alert.get("expires"),
            }
        return None

    @property
    def available(self) -> bool:
        """Return if the sensor is available."""
        return super().available and self.coordinator.data is not None