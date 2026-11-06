
"""The LU-Alert (Luxembourg) integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import LuAlertCoordinator, filters_from_entry

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[LuAlertCoordinator],
) -> bool:
    """Set up LU-Alert from a config entry."""

    coordinator = LuAlertCoordinator(hass, entry)
    entry.runtime_data = coordinator

    entry.async_on_unload(coordinator.async_shutdown)
    entry.async_on_unload(
        entry.add_update_listener(options_update_listener)
    )

    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(
        entry, PLATFORMS
    )

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[LuAlertCoordinator],
) -> bool:
    """Unload LU-Alert."""

    return await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS
    )


async def options_update_listener(
    hass: HomeAssistant,
    entry: ConfigEntry[LuAlertCoordinator],
) -> None:
    """Handle options update."""

    coordinator = entry.runtime_data
    coordinator.filters = filters_from_entry(hass, entry)
    await coordinator.async_request_refresh()

