"""Sensor platform for LU-Alert (Luxembourg)."""
from __future__ import annotations
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, DEFAULT_NAME
from .coordinator import LuAlertDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the LU-Alert sensor from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([LuAlertSensor(coordinator, entry)])


class LuAlertSensor(CoordinatorEntity[LuAlertDataUpdateCoordinator], SensorEntity):
    """A sensor to display the number of active LU-Alerts."""

    def __init__(
        self, coordinator: LuAlertDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = DEFAULT_NAME
        self._attr_unique_id = f"{entry.entry_id}_alerts"
        self._attr_icon = "mdi:alert"
        self._attr_attribution = "Data provided by data.public.lu"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": DEFAULT_NAME,
            "manufacturer": "Luxembourg Government",
            "model": "LU-Alert",
            "entry_type": "service",
        }

    @property
    def native_value(self) -> int:
        """Return the state of the sensor (the number of active alerts)."""
        if self.coordinator.data:
            return self.coordinator.data.get("count", 0)
        return 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the attributes of the sensor."""
        if self.coordinator.data:
            return {"alerts": self.coordinator.data.get("alerts", [])}
        return {"alerts": []}

    @property
    def available(self) -> bool:
        """Return if the sensor is available."""
        return super().available and self.coordinator.data is not None
