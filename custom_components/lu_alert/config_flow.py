"""Config flow for LU-Alert (Luxembourg) integration."""
from __future__ import annotations
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)


from .const import (
    DOMAIN,
    CONF_MIN_SEVERITY,
    DEFAULT_MIN_SEVERITY,
    CONF_ENABLE_LOCATION_FILTER,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    DEFAULT_ENABLE_LOCATION_FILTER,
    CONF_WATCHLIST_KEYWORDS,
    DEFAULT_WATCHLIST_KEYWORDS,
    CONF_ALLERGENS,
    DEFAULT_ALLERGENS,
    ALLERGEN_LIST,
)
from .enums import Severity

_LOGGER = logging.getLogger(__name__)

# Define the list of severity levels for the dropdown, including a "None" option
SEVERITY_LEVELS = [s.value for s in Severity]


class LuAlertConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for LU-Alert."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(title="LU-Alert", data=user_input)

        # Define the form for the user to fill out
        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_MIN_SEVERITY, default=DEFAULT_MIN_SEVERITY
                ): vol.In(SEVERITY_LEVELS),
                vol.Optional(
                    CONF_ENABLE_LOCATION_FILTER,
                    default=DEFAULT_ENABLE_LOCATION_FILTER,
                ): bool,
                vol.Optional(
                    CONF_LATITUDE, default=self.hass.config.latitude
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=-90, max=90, step=0.000001, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(
                    CONF_LONGITUDE, default=self.hass.config.longitude
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=-180, max=180, step=0.000001, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(
                    CONF_WATCHLIST_KEYWORDS, default=DEFAULT_WATCHLIST_KEYWORDS
                ): str,
                vol.Optional(
                    CONF_ALLERGENS
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=ALLERGEN_LIST,
                        multiple=True,
                        mode=SelectSelectorMode.LIST,
                        custom_value=True,
                    )
                ),
            }
        )

        return self.async_show_form(step_id="user", data_schema=data_schema)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> LuAlertOptionsFlowHandler:
        """Get the options flow for this handler."""
        return LuAlertOptionsFlowHandler(config_entry)


class LuAlertOptionsFlowHandler(config_entries.OptionsFlowWithReload):
    """Handle an options flow for LU-Alert."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            # Update the config entry with new options
            return self.async_create_entry(title="", data=user_input)

        # Define the form, pre-filling with existing options
        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_MIN_SEVERITY,
                    default=self.config_entry.options.get(
                        CONF_MIN_SEVERITY, DEFAULT_MIN_SEVERITY
                    ),
                ): vol.In(SEVERITY_LEVELS),
                vol.Optional(
                    CONF_ENABLE_LOCATION_FILTER,
                    default=self.config_entry.options.get(
                        CONF_ENABLE_LOCATION_FILTER, DEFAULT_ENABLE_LOCATION_FILTER
                    ),
                ): bool,
                vol.Optional(
                    CONF_LATITUDE,
                    default=self.config_entry.options.get(
                        CONF_LATITUDE, self.hass.config.latitude
                    ),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=-90, max=90, step=0.000001, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(
                    CONF_LONGITUDE,
                    default=self.config_entry.options.get(
                        CONF_LONGITUDE, self.hass.config.longitude
                    ),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=-180, max=180, step=0.000001, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(
                    CONF_WATCHLIST_KEYWORDS,
                    default=self.config_entry.options.get(
                        CONF_WATCHLIST_KEYWORDS, DEFAULT_WATCHLIST_KEYWORDS
                    ),
                ): str,
                vol.Optional(
                    CONF_ALLERGENS,
                    default=self.config_entry.options.get(
                        CONF_ALLERGENS, DEFAULT_ALLERGENS
                    ),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=ALLERGEN_LIST,
                        multiple=True,
                        mode=SelectSelectorMode.LIST,
                        custom_value=True,
                    )
                ),
            }
        )

        return self.async_show_form(step_id="init", data_schema=data_schema)
