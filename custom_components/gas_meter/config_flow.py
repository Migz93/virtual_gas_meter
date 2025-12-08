from homeassistant import config_entries
import voluptuous as vol
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


class GasMeterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the Virtual Gas Meter integration."""

    VERSION = 2

    def __init__(self):
        """Initialize the config flow."""
        self._data = {}

    async def async_step_user(self, user_input=None):
        """Step 1: Select unit system and operating mode."""
        # Prevent duplicate entries - only one instance allowed
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        
        errors = {}

        if user_input is not None:
            self._data.update(user_input)
            # Route to appropriate next step based on mode
            if user_input[CONF_OPERATING_MODE] == MODE_BOILER_TRACKING:
                return await self.async_step_boiler_config()
            else:
                return await self.async_step_bill_entry_config()

        schema = vol.Schema({
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
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_boiler_config(self, user_input=None):
        """Step 2a: Configure boiler tracking mode."""
        errors = {}

        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(
                title="Virtual Gas Meter",
                data=self._data,
            )

        # Get list of switch entities
        boiler_entities = await self._get_switch_entities()

        if not boiler_entities:
            errors["base"] = "no_switches_found"

        schema = vol.Schema({
            vol.Required(CONF_BOILER_ENTITY): selector({
                "entity": {
                    "domain": "switch",
                }
            }),
            vol.Optional(CONF_BOILER_AVERAGE, default=DEFAULT_BOILER_AV_H): selector({
                "number": {
                    "min": 0,
                    "max": 100,
                    "step": 0.001,
                    "mode": "box",
                }
            }),
            vol.Optional(CONF_LATEST_GAS_DATA, default=DEFAULT_LATEST_GAS_DATA): selector({
                "number": {
                    "min": 0,
                    "max": 1000000,
                    "step": 0.001,
                    "mode": "box",
                }
            }),
        })

        return self.async_show_form(
            step_id="boiler_config",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_bill_entry_config(self, user_input=None):
        """Step 2b: Configure bill entry mode."""
        errors = {}

        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(
                title="Virtual Gas Meter",
                data=self._data,
            )

        schema = vol.Schema({
            vol.Optional(CONF_LATEST_GAS_DATA, default=DEFAULT_LATEST_GAS_DATA): selector({
                "number": {
                    "min": 0,
                    "max": 1000000,
                    "step": 0.001,
                    "mode": "box",
                }
            }),
        })

        return self.async_show_form(
            step_id="bill_entry_config",
            data_schema=schema,
            errors=errors,
        )

    async def _get_switch_entities(self):
        """Retrieve switch entities from the entity registry."""
        entity_registry = er.async_get(self.hass)

        return [
            entity.entity_id for entity in entity_registry.entities.values()
            if entity.entity_id.startswith("switch.")
        ]

    @staticmethod
    @config_entries.HANDLERS.register(DOMAIN)
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return GasMeterOptionsFlow(config_entry)


class GasMeterOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Virtual Gas Meter."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        # Check if we're in boiler tracking mode
        operating_mode = self.config_entry.data.get(CONF_OPERATING_MODE, DEFAULT_OPERATING_MODE)
        
        if operating_mode != MODE_BOILER_TRACKING:
            # No options available for bill entry mode
            return self.async_abort(reason="no_options_available")

        errors = {}

        # Get config data from hass.data
        config_data = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id, {})

        if user_input is not None:
            # Get the new values
            new_boiler_entity = user_input.get(CONF_BOILER_ENTITY)
            new_boiler_average_h = user_input.get(CONF_BOILER_AVERAGE)
            new_boiler_average_min = new_boiler_average_h / 60

            # Update hass.data
            self.hass.data[DOMAIN][self.config_entry.entry_id]["boiler_entity"] = new_boiler_entity
            self.hass.data[DOMAIN][self.config_entry.entry_id]["average_m3_per_min"] = new_boiler_average_min

            # Update the config entry data
            new_data = {**self.config_entry.data}
            new_data[CONF_BOILER_ENTITY] = new_boiler_entity
            new_data[CONF_BOILER_AVERAGE] = new_boiler_average_h
            self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)

            return self.async_create_entry(title="", data={})

        # Get current values from hass.data (these may have been updated by the integration)
        current_boiler_entity = config_data.get("boiler_entity", self.config_entry.data.get(CONF_BOILER_ENTITY))

        current_average_min = config_data.get("average_m3_per_min")
        if current_average_min is not None and current_average_min not in [None, "None", "unknown", "unavailable"]:
            try:
                current_average_h = float(current_average_min) * 60
            except (ValueError, TypeError):
                current_average_h = self.config_entry.data.get(CONF_BOILER_AVERAGE, DEFAULT_BOILER_AV_H)
        else:
            current_average_h = self.config_entry.data.get(CONF_BOILER_AVERAGE, DEFAULT_BOILER_AV_H)

        schema = vol.Schema({
            vol.Required(CONF_BOILER_ENTITY, default=current_boiler_entity): selector({
                "entity": {
                    "domain": "switch",
                }
            }),
            vol.Required(CONF_BOILER_AVERAGE, default=current_average_h): selector({
                "number": {
                    "min": 0,
                    "max": 100,
                    "step": 0.000001,
                    "mode": "box",
                }
            }),
        })

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
        )
