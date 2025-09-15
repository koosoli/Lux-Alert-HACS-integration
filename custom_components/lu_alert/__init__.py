"""The LU-Alert (Luxembourg) integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import LuAlertDataUpdateCoordinator

# List of platforms that this integration will create.
PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up LU-Alert from a config entry."""

    # Create the DataUpdateCoordinator.
    coordinator = LuAlertDataUpdateCoordinator(hass, entry)

    # Add listener for options updates.
    entry.async_on_unload(entry.add_update_listener(options_update_listener))

    # Fetch initial data so we have it when the sensors are set up.
    await coordinator.async_config_entry_first_refresh()

    # Store the coordinator so the sensors can access it.
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Forward the setup to the sensor platform.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register the Lovelace card if it's not already registered
    if "lovelace" in hass.data:
        resources = hass.data["lovelace"].get("resources")
        if resources:
            card_url = f"/hacsfiles/{DOMAIN}/lu-alert-card.js"
            if not any(res["url"] == card_url for res in resources.async_items()):
                resources.async_create_item(
                    {"res_type": "module", "url": card_url}
                )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # This is called when the user removes the integration.
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def options_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    # This is triggered when the user changes the options.
    # We trigger a refresh of the coordinator to apply the new settings.
    await hass.data[DOMAIN][entry.entry_id].async_request_refresh()