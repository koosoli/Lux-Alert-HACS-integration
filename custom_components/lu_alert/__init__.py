"""The LU-Alert (Luxembourg) integration."""
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from .const import CARD_FILE, DOMAIN, STATIC_URL
from .coordinator import LuAlertCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]

type LuAlertConfigEntry = ConfigEntry[LuAlertCoordinator]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Serve the dashboard card. This runs once, not once per config entry."""
    await _async_register_card(hass)
    return True


async def _async_register_card(hass: HomeAssistant) -> None:
    """Serve the files of the www folder and load the card module in every dashboard.

    HACS only serves files of a "plugin" repository under /hacsfiles/, never those inside an integration, so the
    integration serves its own folder and registers the module as an extra JS module of the frontend. That needs no
    Lovelace resource and works with dashboards in YAML mode as well.
    """
    if getattr(hass, "http", None) is None:
        return
    folder = Path(__file__).parent / "www"
    await hass.http.async_register_static_paths([StaticPathConfig(STATIC_URL, str(folder), cache_headers=False)])
    if "frontend" not in hass.config.components:
        _LOGGER.debug("The frontend is not loaded: the dashboard card is served but not registered")
        return
    from homeassistant.components.frontend import add_extra_js_url  # noqa: PLC0415

    version = (await async_get_integration(hass, DOMAIN)).version
    add_extra_js_url(hass, f"{STATIC_URL}/{CARD_FILE}?v={version}")


async def async_setup_entry(hass: HomeAssistant, entry: LuAlertConfigEntry) -> bool:
    """Set up LU-Alert from a config entry."""
    coordinator = LuAlertCoordinator(hass, entry)
    # Raises ConfigEntryNotReady when the feed cannot be read: Home Assistant retries the setup by itself.
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    entry.async_on_unload(coordinator.async_shutdown)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: LuAlertConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_options_updated(hass: HomeAssistant, entry: LuAlertConfigEntry) -> None:
    """The options changed: set the entry up again, so the new filter rules apply at once."""
    await hass.config_entries.async_reload(entry.entry_id)
