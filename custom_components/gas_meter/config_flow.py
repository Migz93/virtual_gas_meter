"""Config flow for Virtual Gas Meter integration."""
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
