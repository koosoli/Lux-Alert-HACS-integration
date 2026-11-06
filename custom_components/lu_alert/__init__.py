
"""The LU-Alert (Luxembourg) integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import LuAlertDataUpdateCoordinator

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Set up LU-Alert from a config entry."""

    coordinator = LuAlertDataUpdateCoordinator(hass, entry)

    entry.async_on_unload(
        entry.add_update_listener(options_update_listener)
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(
        entry, PLATFORMS
    )

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Unload a config entry."""

    if unload_ok := await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS
    ):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def options_update_listener(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Handle options update."""

    await hass.data[DOMAIN][entry.entry_id].async_request_refresh()

