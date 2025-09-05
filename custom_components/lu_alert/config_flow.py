"""Config flow for LU-Alert (Luxembourg) integration."""
import logging

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
import voluptuous as vol

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class LuAlertConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for LU-Alert."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        # This integration has only one instance possible, so if one is already
        # configured, we will abort.
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            # No data is actually collected from the user, so we just create the entry.
            return self.async_create_entry(title="LU-Alert", data={})

        # Show the form to the user. Since there are no fields, it will just be
        # a confirmation dialog.
        return self.async_show_form(step_id="user")

async def _async_has_devices(hass: HomeAssistant) -> bool:
    """Return if there are devices that can be discovered."""
    # This integration does not discover devices, it's a cloud service.
    # Returning True allows the user to initiate the flow from the UI.
    return True
