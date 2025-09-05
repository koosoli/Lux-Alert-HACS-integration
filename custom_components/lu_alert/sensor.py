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

    sensors_to_add = []
    for i in range(MAX_ALERTS):
        sensors_to_add.extend(
            [
                LuAlertHeadlineSensor(coordinator, entry, i),
                LuAlertStatusSensor(coordinator, entry, i),
                LuAlertSeveritySensor(coordinator, entry, i),
                LuAlertDescriptionSensor(coordinator, entry, i),
            ]
        )
    async_add_entities(sensors_to_add)


class LuAlertIndexedSensor(CoordinatorEntity[LuAlertDataUpdateCoordinator], SensorEntity):
    """Base class for an indexed LU-Alert sensor."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: LuAlertDataUpdateCoordinator, entry: ConfigEntry, index: int
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entry = entry
        self.index = index
        self._attr_attribution = "Data provided by data.public.lu"

        # All sensors will be part of a single device for the integration
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            name=DEFAULT_NAME,
            manufacturer="Luxembourg Government",
            model="LU-Alert",
            entry_type="service",
        )

    @property
    def alert_data(self) -> dict[str, Any] | None:
        """Return the alert data for this sensor's index, or None if not available."""
        if self.coordinator.data and len(self.coordinator.data["alerts"]) > self.index:
            return self.coordinator.data["alerts"][self.index]
        return None

    @property
    def available(self) -> bool:
        """Return if the sensor is available."""
        return super().available and self.coordinator.data is not None

# --- Individual Sensor Classes ---

class LuAlertHeadlineSensor(LuAlertIndexedSensor):
    """Sensor for the alert headline."""
    _attr_icon = "mdi:alert-outline"

    def __init__(self, coordinator, entry, index):
        super().__init__(coordinator, entry, index)
        self.entity_id = f"sensor.lu_alert_{self.index + 1}_headline"
        self._attr_name = f"Alert {self.index + 1} Headline"
        self._attr_unique_id = f"{self.entry.entry_id}_{self.index}_headline"

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        if self.alert_data:
            return self.alert_data.get("headline")
        return "No Alert"

class LuAlertStatusSensor(LuAlertIndexedSensor):
    """Sensor for the alert status."""
    def __init__(self, coordinator, entry, index):
        super().__init__(coordinator, entry, index)
        self.entity_id = f"sensor.lu_alert_{self.index + 1}_status"
        self._attr_name = f"Alert {self.index + 1} Status"
        self._attr_unique_id = f"{self.entry.entry_id}_{self.index}_status"

    @property
    def native_value(self) -> str | None:
        if self.alert_data:
            return self.alert_data.get("status")
        return "Not Active"

class LuAlertSeveritySensor(LuAlertIndexedSensor):
    """Sensor for the alert severity."""
    def __init__(self, coordinator, entry, index):
        super().__init__(coordinator, entry, index)
        self.entity_id = f"sensor.lu_alert_{self.index + 1}_severity"
        self._attr_name = f"Alert {self.index + 1} Severity"
        self._attr_unique_id = f"{self.entry.entry_id}_{self.index}_severity"

    @property
    def native_value(self) -> str | None:
        if self.alert_data:
            return self.alert_data.get("severity")
        return "Not Active"

class LuAlertDescriptionSensor(LuAlertIndexedSensor):
    """Sensor for the alert description."""
    _attr_icon = "mdi:text-box-outline"

    def __init__(self, coordinator, entry, index):
        super().__init__(coordinator, entry, index)
        self.entity_id = f"sensor.lu_alert_{self.index + 1}_description"
        self._attr_name = f"Alert {self.index + 1} Description"
        self._attr_unique_id = f"{self.entry.entry_id}_{self.index}_description"

    @property
    def native_value(self) -> str | None:
        if self.alert_data:
            return self.alert_data.get("description")
        return "Not Active"
