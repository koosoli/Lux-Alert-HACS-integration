"""Binary sensor platform for LU-Alert (Luxembourg)."""
from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CRITICAL_SEVERITIES
from .coordinator import LuAlertCoordinator
from .entity import LuAlertEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the LU-Alert binary sensors from a config entry."""
    coordinator: LuAlertCoordinator = entry.runtime_data
    async_add_entities([
        LuAlertSeverityBinarySensor(coordinator, "extreme"),
        LuAlertSeverityBinarySensor(coordinator, "severe"),
        LuAlertCriticalBinarySensor(coordinator),
        LuAlertLocalBinarySensor(coordinator),
        LuAlertWatchlistBinarySensor(coordinator),
        LuAlertAllergenBinarySensor(coordinator),
        LuAlertFeedBinarySensor(coordinator),
    ])


class LuAlertBinarySensor(LuAlertEntity, BinarySensorEntity):
    """Base class: an alert condition. On means "unsafe"."""

    _attr_device_class = BinarySensorDeviceClass.SAFETY

    def _alerts(self):
        return self.feed.snapshot.alerts if self.feed else ()


class LuAlertSeverityBinarySensor(LuAlertBinarySensor):
    """On while there is an alert of one severity."""

    def __init__(self, coordinator: LuAlertCoordinator, severity: str) -> None:
        super().__init__(coordinator)
        self.severity = severity
        self._attr_unique_id = f"{self._entry_id}_{severity}_alert_active"
        self._attr_name = f"{severity.capitalize()} Alert Active"

    @property
    def is_on(self) -> bool:
        return any(a.severity.lower() == self.severity for a in self._alerts())


class LuAlertCriticalBinarySensor(LuAlertBinarySensor):
    """On while there is a Severe or Extreme alert."""

    _attr_name = "Critical Alert Active"

    def __init__(self, coordinator: LuAlertCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._entry_id}_critical_active"

    @property
    def is_on(self) -> bool:
        return any(a.severity in CRITICAL_SEVERITIES for a in self._alerts())


class LuAlertLocalBinarySensor(LuAlertBinarySensor):
    """On while an alert covers the home location (needs the location filter to be on)."""

    _attr_name = "Local Alert Active"
    _attr_icon = "mdi:map-marker-alert"

    def __init__(self, coordinator: LuAlertCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._entry_id}_local_alert_active"

    @property
    def is_on(self) -> bool:
        return any(a.local is True for a in self._alerts())


class LuAlertWatchlistBinarySensor(LuAlertBinarySensor):
    """On while an alert mentions one of the watchlist keywords."""

    _attr_name = "Watchlist Match"
    _attr_icon = "mdi:format-list-checks"

    def __init__(self, coordinator: LuAlertCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._entry_id}_watchlist_match"

    @property
    def is_on(self) -> bool:
        return any(a.watch_match for a in self._alerts())


class LuAlertAllergenBinarySensor(LuAlertBinarySensor):
    """On while an alert mentions one of the chosen allergens."""

    _attr_name = "Allergen Match"
    _attr_icon = "mdi:food-off-outline"

    def __init__(self, coordinator: LuAlertCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._entry_id}_allergen_match"

    @property
    def is_on(self) -> bool:
        return any(a.allergen_match for a in self._alerts())


class LuAlertFeedBinarySensor(LuAlertEntity, BinarySensorEntity):
    """On while the last poll of the feed worked. Off: the other entities show the last known alerts."""

    _attr_name = "Feed connection"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: LuAlertCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._entry_id}_feed_connection"

    @property
    def is_on(self) -> bool:
        return bool(self.feed and self.feed.feed_ok)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if not self.feed:
            return {}
        snapshot = self.feed.snapshot
        return {
            "last_success": self.feed.last_success.isoformat() if self.feed.last_success else None,
            "last_error": self.feed.last_error,
            "files_listed": self.feed.listed,
            "files_fetched": self.feed.fetched,
            "files_failed": self.feed.failed,
            "files_unreadable": self.feed.unreadable,
            "left_out": dict(snapshot.dropped),
            "unknown_levels": list(snapshot.unknown_levels),
            "ignored_tests": len(snapshot.ignored_tests),
        }
