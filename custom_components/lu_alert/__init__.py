"""The LU-Alert (Luxembourg) integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.frontend import async_register_lovelace_module, async_remove_lovelace_module

from .const import DOMAIN
from .coordinator import LuAlertDataUpdateCoordinator

# List of platforms that this integration will create.
PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up LU-Alert from a config entry."""

    # Create the DataUpdateCoordinator.
    coordinator = LuAlertDataUpdateCoordinator(hass, entry)

    # Fetch initial data so we have it when the sensors are set up.
    await coordinator.async_config_entry_first_refresh()

    # Store the coordinator so the sensors can access it.
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Forward the setup to the sensor platform.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register the Lovelace card
    await async_register_lovelace_module(
        hass, f"/hacsfiles/{DOMAIN}/lu-alert-card.js", "module"
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unregister the Lovelace card
    await async_remove_lovelace_module(hass, f"/hacsfiles/{DOMAIN}/lu-alert-card.js")

    # This is called when the user removes the integration.
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
