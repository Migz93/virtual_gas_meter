"""Config flow for Virtual Gas Meter integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import selector

from .const import (
    DOMAIN,
    CONF_BOILER_ENTITY,
    CONF_BOILER_AVERAGE,
    CONF_LATEST_GAS_DATA,
    CONF_UNIT_SYSTEM,
    CONF_OPERATING_MODE,
    DEFAULT_BOILER_AV_H,
    DEFAULT_LATEST_GAS_DATA,
    DEFAULT_UNIT_SYSTEM,
    DEFAULT_OPERATING_MODE,
    UNIT_SYSTEM_METRIC,
    UNIT_SYSTEM_IMPERIAL,
    MODE_BOILER_TRACKING,
    MODE_BILL_ENTRY,
)


class GasMeterConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the Virtual Gas Meter integration."""

    VERSION = 2

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> GasMeterOptionsFlow:
        """Get the options flow for this handler."""
        return GasMeterOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 1: Select unit system and operating mode."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            self._data.update(user_input)
            if user_input[CONF_OPERATING_MODE] == MODE_BOILER_TRACKING:
                return await self.async_step_boiler_config()
            return await self.async_step_bill_entry_config()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_UNIT_SYSTEM, default=DEFAULT_UNIT_SYSTEM): selector({
                    "select": {
                        "options": [
                            {"value": UNIT_SYSTEM_METRIC, "label": "Metric (m³)"},
                            {"value": UNIT_SYSTEM_IMPERIAL, "label": "Imperial (CCF)"},
                        ],
                        "mode": "dropdown",
                    }
                }),
                vol.Required(CONF_OPERATING_MODE, default=DEFAULT_OPERATING_MODE): selector({
                    "select": {
                        "options": [
                            {"value": MODE_BOILER_TRACKING, "label": "Boiler/Furnace Tracking"},
                            {"value": MODE_BILL_ENTRY, "label": "Monthly Bill Entry"},
                        ],
                        "mode": "dropdown",
                    }
                }),
            }),
        )

    async def async_step_boiler_config(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2a: Configure boiler tracking mode."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(
                title="Virtual Gas Meter",
                data=self._data,
            )

        boiler_entities = await self._get_switch_entities()
        if not boiler_entities:
            errors["base"] = "no_switches_found"

        return self.async_show_form(
            step_id="boiler_config",
            data_schema=vol.Schema({
                vol.Required(CONF_BOILER_ENTITY): selector({
                    "entity": {"domain": "switch"}
                }),
                vol.Optional(CONF_BOILER_AVERAGE, default=DEFAULT_BOILER_AV_H): selector({
                    "number": {"min": 0, "max": 100, "step": 0.001, "mode": "box"}
                }),
                vol.Optional(CONF_LATEST_GAS_DATA, default=DEFAULT_LATEST_GAS_DATA): selector({
                    "number": {"min": 0, "max": 1000000, "step": 0.001, "mode": "box"}
                }),
            }),
            errors=errors,
        )

    async def async_step_bill_entry_config(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2b: Configure bill entry mode."""
        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(
                title="Virtual Gas Meter",
                data=self._data,
            )

        return self.async_show_form(
            step_id="bill_entry_config",
            data_schema=vol.Schema({
                vol.Optional(CONF_LATEST_GAS_DATA, default=DEFAULT_LATEST_GAS_DATA): selector({
                    "number": {"min": 0, "max": 1000000, "step": 0.001, "mode": "box"}
                }),
            }),
        )

    async def _get_switch_entities(self) -> list[str]:
        """Retrieve switch entities from the entity registry."""
        entity_registry = er.async_get(self.hass)
        return [
            entity.entity_id
            for entity in entity_registry.entities.values()
            if entity.entity_id.startswith("switch.")
        ]


class GasMeterOptionsFlow(OptionsFlow):
    """Handle options flow for Virtual Gas Meter."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        # Check if we're in boiler tracking mode
        operating_mode = self.config_entry.data.get(
            CONF_OPERATING_MODE, DEFAULT_OPERATING_MODE
        )

        if operating_mode != MODE_BOILER_TRACKING:
            return self.async_abort(reason="no_options_available")

        if user_input is not None:
            # Update hass.data if available
            if (
                DOMAIN in self.hass.data
                and self.config_entry.entry_id in self.hass.data[DOMAIN]
            ):
                new_avg_min = user_input[CONF_BOILER_AVERAGE] / 60
                self.hass.data[DOMAIN][self.config_entry.entry_id]["boiler_entity"] = user_input[CONF_BOILER_ENTITY]
                self.hass.data[DOMAIN][self.config_entry.entry_id]["average_m3_per_min"] = new_avg_min

            # Update the config entry data
            new_data = {**self.config_entry.data}
            new_data[CONF_BOILER_ENTITY] = user_input[CONF_BOILER_ENTITY]
            new_data[CONF_BOILER_AVERAGE] = user_input[CONF_BOILER_AVERAGE]
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=new_data
            )

            return self.async_create_entry(title="", data={})

        # Get current values
        current_boiler_entity = self.config_entry.data.get(CONF_BOILER_ENTITY, "")
        current_average_h = self.config_entry.data.get(
            CONF_BOILER_AVERAGE, DEFAULT_BOILER_AV_H
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(
                    CONF_BOILER_ENTITY, default=current_boiler_entity
                ): selector({"entity": {"domain": "switch"}}),
                vol.Required(
                    CONF_BOILER_AVERAGE, default=current_average_h
                ): selector({
                    "number": {"min": 0, "max": 100, "step": 0.000001, "mode": "box"}
                }),
            }),
        )
