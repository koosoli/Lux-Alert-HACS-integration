"""Binary sensor platform for LU-Alert (Luxembourg)."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
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
    """Set up the LU-Alert binary sensors from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    sensors_to_add = [
        LuAlertCriticalBinarySensor(coordinator, entry, "extreme"),
        LuAlertCriticalBinarySensor(coordinator, entry, "severe"),
    ]
    async_add_entities(sensors_to_add)


class LuAlertCriticalBinarySensor(
    CoordinatorEntity[LuAlertDataUpdateCoordinator], BinarySensorEntity
):
    """A binary sensor that is 'on' if there are active alerts of a certain severity."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.SAFETY

    def __init__(
        self,
        coordinator: LuAlertDataUpdateCoordinator,
        entry: ConfigEntry,
        severity_level: str,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.entry = entry
        self.severity_level = severity_level
        self._attr_attribution = "Data provided by data.public.lu"

        # Define the unique ID and name based on the severity level
        self._attr_unique_id = f"{self.entry.entry_id}_{self.severity_level}_alert_active"
        self._attr_name = f"{self.severity_level.capitalize()} Alert Active"

        # All sensors are part of the same device
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            name=DEFAULT_NAME,
            manufacturer="Luxembourg Government",
            model="LU-Alert",
            entry_type="service",
        )

    @property
    def is_on(self) -> bool:
        """Return true if there are active alerts of the specified severity."""
        if self.coordinator.data:
            return self.coordinator.data["severity_counts"].get(self.severity_level, 0) > 0
        return False

    @property
    def available(self) -> bool:
        """Return if the sensor is available."""
        return super().available and self.coordinator.data is not None
