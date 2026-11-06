"""Base class of the LU-Alert entities: one device, one coordinator."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DEFAULT_NAME, DOMAIN, PROJECT_URL
from .coordinator import LuAlertCoordinator, LuAlertData


class LuAlertEntity(CoordinatorEntity[LuAlertCoordinator]):
    """Everything an LU-Alert entity shares."""

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION

    def __init__(self, coordinator: LuAlertCoordinator) -> None:
        super().__init__(coordinator)
        self._entry_id = coordinator.config_entry.entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            name=DEFAULT_NAME,
            manufacturer="Luxembourg Government",
            model="LU-Alert",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=PROJECT_URL,
        )

    @property
    def feed(self) -> LuAlertData | None:
        return self.coordinator.data
