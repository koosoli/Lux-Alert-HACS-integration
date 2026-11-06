"""Config flow for the LU-Alert (Luxembourg) integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    BooleanSelector, SelectOptionDict, SelectSelector, SelectSelectorConfig, SelectSelectorMode, TextSelector,
)

from .const import (
    ALLERGEN_LIST, CONF_ALLERGENS, CONF_LANGUAGE, CONF_LOCATION_MODE, CONF_MIN_SEVERITY, CONF_SHOW_TEST,
    CONF_WATCHLIST_KEYWORDS, DEFAULT_ALLERGENS, DEFAULT_LANGUAGE, DEFAULT_LOCATION_MODE, DEFAULT_MIN_SEVERITY,
    DEFAULT_SHOW_TEST, DEFAULT_WATCHLIST_KEYWORDS, DEFAULT_NAME, DOMAIN, LOCATION_MODES, MIN_SEVERITY_CHOICES,
)

LANGUAGE_OPTIONS = [
    SelectOptionDict(value="en", label="English"),
    SelectOptionDict(value="de", label="Deutsch"),
    SelectOptionDict(value="fr", label="Français"),
    SelectOptionDict(value="lb", label="Lëtzebuergesch"),
]

SEVERITY_SELECTOR = SelectSelector(SelectSelectorConfig(
    options=list(MIN_SEVERITY_CHOICES), mode=SelectSelectorMode.DROPDOWN, translation_key="severity"))


class LuAlertConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for LU-Alert."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """The first and only step: the minimum severity."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(title=DEFAULT_NAME, data=user_input)

        schema = vol.Schema({vol.Required(CONF_MIN_SEVERITY, default=DEFAULT_MIN_SEVERITY): SEVERITY_SELECTOR})
        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> LuAlertOptionsFlow:
        """Get the options flow for this handler."""
        return LuAlertOptionsFlow()


class LuAlertOptionsFlow(OptionsFlow):
    """The options: what is shown, in which language, and what is local."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            # a clear field is left out of the answer: only one of latitude and longitude is not a location
            if (CONF_LATITUDE in user_input) != (CONF_LONGITUDE in user_input):
                errors["base"] = "location_incomplete"
            else:
                return self.async_create_entry(title="", data=user_input)

        current = {**self.config_entry.data, **self.config_entry.options} if user_input is None else user_input
        # Older entries stored title-case values; selectors use the lower-case option keys.
        severity_default = str(current.get(CONF_MIN_SEVERITY, DEFAULT_MIN_SEVERITY)).lower()
        schema = vol.Schema({
            vol.Required(CONF_MIN_SEVERITY, default=severity_default):
                SEVERITY_SELECTOR,
            vol.Required(CONF_LANGUAGE, default=current.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)): SelectSelector(
                SelectSelectorConfig(options=LANGUAGE_OPTIONS, mode=SelectSelectorMode.DROPDOWN)),
            vol.Required(CONF_LOCATION_MODE, default=current.get(CONF_LOCATION_MODE, DEFAULT_LOCATION_MODE)):
                SelectSelector(SelectSelectorConfig(options=list(LOCATION_MODES), mode=SelectSelectorMode.DROPDOWN,
                                                    translation_key="location_mode")),
            vol.Optional(CONF_LATITUDE, description={"suggested_value": current.get(CONF_LATITUDE)}):
                vol.All(vol.Coerce(float), vol.Range(min=-90, max=90)),
            vol.Optional(CONF_LONGITUDE, description={"suggested_value": current.get(CONF_LONGITUDE)}):
                vol.All(vol.Coerce(float), vol.Range(min=-180, max=180)),
            vol.Optional(CONF_WATCHLIST_KEYWORDS, description={"suggested_value": current.get(
                CONF_WATCHLIST_KEYWORDS, DEFAULT_WATCHLIST_KEYWORDS)}): TextSelector(),
            vol.Optional(CONF_ALLERGENS, default=current.get(CONF_ALLERGENS, DEFAULT_ALLERGENS)): SelectSelector(
                SelectSelectorConfig(options=ALLERGEN_LIST, multiple=True, custom_value=True,
                                     mode=SelectSelectorMode.DROPDOWN)),
            vol.Required(CONF_SHOW_TEST, default=current.get(CONF_SHOW_TEST, DEFAULT_SHOW_TEST)): BooleanSelector(),
        })
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
