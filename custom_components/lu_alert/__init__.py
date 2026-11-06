
"""The LU-Alert (Luxembourg) integration."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.frontend import (
    DATA_EXTRA_MODULE_URL,
    add_extra_js_url,
    remove_extra_js_url,
)
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CARD_FILE, DOMAIN, STATIC_URL
from .coordinator import LuAlertCoordinator, filters_from_entry

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
]

WWW_PATH = Path(__file__).parent / "www"
CARD_MODULE_URL = f"{STATIC_URL}/{CARD_FILE}?v=0.1.0"
STATIC_PATH_REGISTERED = f"{DOMAIN}_static_path_registered"


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

    # The static path survives a config-entry unload, so register it only once per HA run.
    if hass.http is not None and not hass.data.get(STATIC_PATH_REGISTERED):
        await hass.http.async_register_static_paths(
            [StaticPathConfig(STATIC_URL, str(WWW_PATH), cache_headers=False)]
        )
        hass.data[STATIC_PATH_REGISTERED] = True
    elif hass.http is None:
        _LOGGER.warning("HTTP is not loaded; the LU-Alert dashboard card cannot be served yet")

    # The frontend component may not be loaded in headless installations or tests.
    if DATA_EXTRA_MODULE_URL in hass.data:
        add_extra_js_url(hass, CARD_MODULE_URL)
        entry.async_on_unload(lambda: remove_extra_js_url(hass, CARD_MODULE_URL))

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

