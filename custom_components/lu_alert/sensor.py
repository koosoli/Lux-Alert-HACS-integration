"""Sensor platform for LU-Alert (Luxembourg)."""
from __future__ import annotations

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
    """Set up the LU-Alert sensors from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    sensors_to_add = [
        LuAlertHeadlineSensor(coordinator),
        LuAlertStatusSensor(coordinator),
        LuAlertMessageTypeSensor(coordinator),
        LuAlertDescriptionSensor(coordinator),
        LuAlertSenderSensor(coordinator),
        LuAlertSeveritySensor(coordinator),
        LuAlertCertaintySensor(coordinator),
        LuAlertUrgencySensor(coordinator),
        LuAlertEventSensor(coordinator),
        LuAlertInstructionSensor(coordinator),
        LuAlertSentTimeSensor(coordinator),
        LuAlertExpiresTimeSensor(coordinator),
        LuAlertWebSensor(coordinator),
    ]

    async_add_entities(sensors_to_add)


class LuAlertSensor(CoordinatorEntity[LuAlertDataUpdateCoordinator], SensorEntity):
    """Base class for a LU-Alert sensor."""

    def __init__(self, coordinator: LuAlertDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self.coordinator.config_entry.entry_id)},
            "name": DEFAULT_NAME,
            "manufacturer": "Luxembourg Government",
            "model": "LU-Alert",
            "entry_type": "service",
        }
        self._attr_attribution = "Data provided by data.public.lu"

    @property
    def available(self) -> bool:
        """Return if the sensor is available."""
        return super().available and self.coordinator.data is not None

# --- Individual Sensor Classes ---

class LuAlertHeadlineSensor(LuAlertSensor):
    """Sensor for the alert headline."""
    _attr_name = f"{DEFAULT_NAME} Headline"
    _attr_unique_id = f"{DOMAIN}_headline"
    _attr_icon = "mdi:alert-outline"

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        return self.coordinator.data.get("headline")

class LuAlertStatusSensor(LuAlertSensor):
    """Sensor for the alert status."""
    _attr_name = f"{DEFAULT_NAME} Status"
    _attr_unique_id = f"{DOMAIN}_status"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.get("status")

class LuAlertMessageTypeSensor(LuAlertSensor):
    """Sensor for the alert message type."""
    _attr_name = f"{DEFAULT_NAME} Message Type"
    _attr_unique_id = f"{DOMAIN}_msgType"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.get("msgType")

class LuAlertDescriptionSensor(LuAlertSensor):
    """Sensor for the alert description."""
    _attr_name = f"{DEFAULT_NAME} Description"
    _attr_unique_id = f"{DOMAIN}_description"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.get("description")

class LuAlertSenderSensor(LuAlertSensor):
    """Sensor for the alert sender name."""
    _attr_name = f"{DEFAULT_NAME} Sender"
    _attr_unique_id = f"{DOMAIN}_senderName"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.get("senderName")

class LuAlertSeveritySensor(LuAlertSensor):
    """Sensor for the alert severity."""
    _attr_name = f"{DEFAULT_NAME} Severity"
    _attr_unique_id = f"{DOMAIN}_severity"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.get("severity")

class LuAlertCertaintySensor(LuAlertSensor):
    """Sensor for the alert certainty."""
    _attr_name = f"{DEFAULT_NAME} Certainty"
    _attr_unique_id = f"{DOMAIN}_certainty"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.get("certainty")

class LuAlertUrgencySensor(LuAlertSensor):
    """Sensor for the alert urgency."""
    _attr_name = f"{DEFAULT_NAME} Urgency"
    _attr_unique_id = f"{DOMAIN}_urgency"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.get("urgency")

class LuAlertEventSensor(LuAlertSensor):
    """Sensor for the alert event."""
    _attr_name = f"{DEFAULT_NAME} Event"
    _attr_unique_id = f"{DOMAIN}_event"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.get("event")

class LuAlertInstructionSensor(LuAlertSensor):
    """Sensor for the alert instruction."""
    _attr_name = f"{DEFAULT_NAME} Instruction"
    _attr_unique_id = f"{DOMAIN}_instruction"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.get("instruction")

class LuAlertSentTimeSensor(LuAlertSensor):
    """Sensor for the alert sent time."""
    _attr_name = f"{DEFAULT_NAME} Sent Time"
    _attr_unique_id = f"{DOMAIN}_sent"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.get("sent")

class LuAlertExpiresTimeSensor(LuAlertSensor):
    """Sensor for the alert expires time."""
    _attr_name = f"{DEFAULT_NAME} Expires Time"
    _attr_unique_id = f"{DOMAIN}_expires"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.get("expires")

class LuAlertWebSensor(LuAlertSensor):
    """Sensor for the alert web URL."""
    _attr_name = f"{DEFAULT_NAME} Web"
    _attr_unique_id = f"{DOMAIN}_web"
    _attr_icon = "mdi:web"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.get("web")
