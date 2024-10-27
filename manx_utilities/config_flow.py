"""Config flow for Manx Utilities integration."""
import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, CONF_COST_RESOURCE_ID, CONF_ENERGY_RESOURCE_ID
from .api import ManxUtilitiesAPI

_LOGGER = logging.getLogger(__name__)

class ManxUtilitiesConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Manx Utilities."""

    VERSION = 1

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                # Test the credentials and resource IDs
                api = ManxUtilitiesAPI(
                    user_input[CONF_USERNAME],
                    user_input[CONF_PASSWORD],
                    user_input[CONF_COST_RESOURCE_ID],
                    user_input[CONF_ENERGY_RESOURCE_ID]
                )
                # Test authentication
                await api.authenticate()

                return self.async_create_entry(
                    title=f"Manx Utilities ({user_input[CONF_USERNAME]})",
                    data=user_input,
                )
            except Exception:  # pylint: disable=broad-except
                errors["base"] = "auth"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Required(CONF_COST_RESOURCE_ID): str,
                    vol.Required(CONF_ENERGY_RESOURCE_ID): str,
                }
            ),
            errors=errors,
        )