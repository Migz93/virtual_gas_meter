"""Config flow for Virtual Gas Meter v3."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_ENTITY_ID
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    UNIT_M3,
    UNIT_CCF,
    UNIT_OPTIONS,
    CONF_BOILER_ENTITY,
    CONF_UNIT,
    CONF_INITIAL_METER_READING,
    CONF_INITIAL_AVERAGE_RATE,
    ALLOWED_BOILER_DOMAINS,
)

_LOGGER = logging.getLogger(__name__)


class VirtualGasMeterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Virtual Gas Meter."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle the initial step."""
        # Enforce single instance
        if self._async_current_entries():
            return self.async_abort(
                reason="single_instance_allowed",
                description_placeholders={
                    "message": "Virtual Gas Meter only supports one instance. Remove the existing one to reconfigure."
                },
            )

        errors = {}

        if user_input is not None:
            # Validate boiler entity exists and is in allowed domains
            boiler_entity = user_input[CONF_BOILER_ENTITY]
            domain = boiler_entity.split(".")[0] if "." in boiler_entity else ""
            
            if domain not in ALLOWED_BOILER_DOMAINS:
                errors[CONF_BOILER_ENTITY] = "invalid_domain"
            else:
                # Create the config entry
                return self.async_create_entry(
                    title="Virtual Gas Meter",
                    data=user_input,
                )

        # Build the schema
        data_schema = vol.Schema(
            {
                vol.Required(CONF_BOILER_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=ALLOWED_BOILER_DOMAINS,
                    )
                ),
                vol.Required(CONF_UNIT, default=UNIT_M3): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value=UNIT_M3, label="Cubic Meters (m³)"),
                            selector.SelectOptionDict(value=UNIT_CCF, label="Hundred Cubic Feet (CCF)"),
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(CONF_INITIAL_METER_READING, default=0.0): cv.positive_float,
                vol.Required(CONF_INITIAL_AVERAGE_RATE, default=0.0): cv.positive_float,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "unit_note": "Unit selection cannot be changed after setup."
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> VirtualGasMeterOptionsFlow:
        """Get the options flow for this handler."""
        return VirtualGasMeterOptionsFlow(config_entry)


class VirtualGasMeterOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Virtual Gas Meter."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Manage the options."""
        errors = {}

        if user_input is not None:
            # Validate boiler entity
            boiler_entity = user_input[CONF_BOILER_ENTITY]
            domain = boiler_entity.split(".")[0] if "." in boiler_entity else ""
            
            if domain not in ALLOWED_BOILER_DOMAINS:
                errors[CONF_BOILER_ENTITY] = "invalid_domain"
            else:
                # Update config entry data
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data={**self.config_entry.data, **user_input},
                )
                return self.async_create_entry(title="", data={})

        # Get current values
        current_boiler = self.config_entry.data.get(CONF_BOILER_ENTITY)
        current_rate = self.config_entry.data.get(CONF_INITIAL_AVERAGE_RATE, 0.0)
        current_unit = self.config_entry.data.get(CONF_UNIT, UNIT_M3)

        data_schema = vol.Schema(
            {
                vol.Required(CONF_BOILER_ENTITY, default=current_boiler): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=ALLOWED_BOILER_DOMAINS,
                    )
                ),
                vol.Required(CONF_INITIAL_AVERAGE_RATE, default=current_rate): cv.positive_float,
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "current_unit": f"Current unit: {current_unit} (cannot be changed)",
            },
        )
