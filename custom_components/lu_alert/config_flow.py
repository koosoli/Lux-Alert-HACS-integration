"""Config flow for LU-Alert (Luxembourg) integration."""
from __future__ import annotations

from homeassistant import config_entries

from .const import DOMAIN


class LuAlertConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for LU-Alert."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        # This integration has only one instance possible, so if one is already
        # configured, we will abort.
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        # For a simple, no-input flow, we just create the entry directly
        # without showing a form.
        return self.async_create_entry(title="LU-Alert", data={})
