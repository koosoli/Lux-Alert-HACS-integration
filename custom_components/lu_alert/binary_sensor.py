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

from .const import (
    DOMAIN,
    DEFAULT_NAME,
    CONF_WATCHLIST_KEYWORDS,
    DEFAULT_WATCHLIST_KEYWORDS,
    CONF_ALLERGENS,
    DEFAULT_ALLERGENS,
)
from .coordinator import LuAlertDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the LU-Alert binary sensors from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    sensors_to_add = [
        LuAlertSeverityBinarySensor(coordinator, entry, "extreme"),
        LuAlertSeverityBinarySensor(coordinator, entry, "severe"),
        LuAlertCriticalActiveBinarySensor(coordinator, entry),
        LuAlertLocalAlertActiveBinarySensor(coordinator, entry),
        LuAlertWatchlistMatchBinarySensor(coordinator, entry),
        LuAlertAllergenMatchBinarySensor(coordinator, entry),
    ]
    async_add_entities(sensors_to_add)


class LuAlertBaseBinarySensor(
    CoordinatorEntity[LuAlertDataUpdateCoordinator], BinarySensorEntity
):
    """Base class for LU-Alert binary sensors."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.SAFETY

    def __init__(
        self, coordinator: LuAlertDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the base binary sensor."""
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


class LuAlertSeverityBinarySensor(LuAlertBaseBinarySensor):
    """A binary sensor that is 'on' if there are active alerts of a specific severity."""

    def __init__(
        self, coordinator: LuAlertDataUpdateCoordinator, entry: ConfigEntry, severity: str
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, entry)
        self.severity = severity
        self._attr_unique_id = f"{self.entry.entry_id}_{self.severity}_alert_active"
        self._attr_name = f"{self.severity.capitalize()} Alert Active"

    @property
    def is_on(self) -> bool:
        """Return true if there are active alerts of the specified severity."""
        if self.coordinator.data and self.coordinator.data.get("severity_counts"):
            return self.coordinator.data["severity_counts"].get(self.severity, 0) > 0
        return False


class LuAlertCriticalActiveBinarySensor(LuAlertBaseBinarySensor):
    """A binary sensor that is 'on' if there are any Severe or Extreme alerts."""

    def __init__(
        self, coordinator: LuAlertDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{self.entry.entry_id}_critical_active"
        self._attr_name = "Critical Alert Active"

    @property
    def is_on(self) -> bool:
        """Return true if there are active severe or extreme alerts."""
        if self.coordinator.data and self.coordinator.data.get("severity_counts"):
            counts = self.coordinator.data["severity_counts"]
            return counts.get("severe", 0) > 0 or counts.get("extreme", 0) > 0
        return False


class LuAlertLocalAlertActiveBinarySensor(LuAlertBaseBinarySensor):
    """A binary sensor that is 'on' if any active alert is local to the user."""

    def __init__(
        self, coordinator: LuAlertDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{self.entry.entry_id}_local_alert_active"
        self._attr_name = "Local Alert Active"
        self._attr_icon = "mdi:map-marker-alert"

    @property
    def is_on(self) -> bool:
        """Return true if any alert has the 'is_local' flag set to True."""
        if not self.coordinator.data or not self.coordinator.data.get("alerts"):
            return False

        return any(alert.get("is_local") for alert in self.coordinator.data["alerts"])


class LuAlertWatchlistMatchBinarySensor(LuAlertBaseBinarySensor):
    """A binary sensor that is 'on' if any alert matches the user's watchlist."""

    def __init__(
        self, coordinator: LuAlertDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{self.entry.entry_id}_watchlist_match"
        self._attr_name = "Watchlist Match"
        self._attr_icon = "mdi:format-list-checks"

    @property
    def is_on(self) -> bool:
        """Return true if any alert matches the watchlist."""
        keywords_str = self.entry.options.get(
            CONF_WATCHLIST_KEYWORDS, DEFAULT_WATCHLIST_KEYWORDS
        )
        if not keywords_str or not self.coordinator.data or not self.coordinator.data.get("alerts"):
            return False

        keywords = {k.strip().lower() for k in keywords_str.split(",") if k.strip()}
        if not keywords:
            return False

        for alert in self.coordinator.data["alerts"]:
            # Build a string of all text to search through
            search_text = (
                (alert.get("headline", "") or "")
                + " "
                + (alert.get("description", "") or "")
                + " "
                + " ".join((alert.get("structured_description", {}) or {}).values())
            ).lower()

            if any(keyword in search_text for keyword in keywords):
                return True

        return False


class LuAlertAllergenMatchBinarySensor(LuAlertBaseBinarySensor):
    """A binary sensor that is 'on' if any alert matches the user's allergens."""

    def __init__(
        self, coordinator: LuAlertDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{self.entry.entry_id}_allergen_match"
        self._attr_name = "Allergen Match"
        self._attr_icon = "mdi:food-off-outline"

    @property
    def is_on(self) -> bool:
        """Return true if any alert has the 'allergen_match' flag set to True."""
        if not self.coordinator.data or not self.coordinator.data.get("alerts"):
            return False

        return any(alert.get("allergen_match") for alert in self.coordinator.data["alerts"])