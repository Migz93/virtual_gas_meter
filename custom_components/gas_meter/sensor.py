"""Sensor platform for the Virtual Gas Meter integration."""
import logging
import asyncio

from datetime import datetime, timedelta
from homeassistant.const import STATE_UNKNOWN
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.core import HomeAssistant, callback, ServiceCall
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.components.history_stats.sensor import HistoryStatsSensor
from homeassistant.components.history_stats.coordinator import HistoryStatsUpdateCoordinator, HistoryStats
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.dt import now
from homeassistant.helpers.template import Template
from .const import (
    DOMAIN,
    DEFAULT_BOILER_AV_M,
    DEFAULT_LATEST_GAS_DATA,
    DEFAULT_UNIT_SYSTEM,
    CONF_UNIT_SYSTEM,
    CONF_OPERATING_MODE,
    MODE_BOILER_TRACKING,
    UNIT_CUBIC_METERS,
)
from .unit_converter import get_unit_label, format_gas_value, to_display_unit
import custom_components.gas_meter.file_handler as fh

_LOGGER = logging.getLogger(__name__)

class CustomTemplateSensor(SensorEntity):
    def __init__(self, hass, friendly_name, unique_id, state_template, unit_of_measurement=None, device_class=None, icon=None, state_class=None):
        self.hass = hass
        self._attr_name = friendly_name
        self._attr_unique_id = unique_id
        self._state_template = state_template
        self._attr_unit_of_measurement = unit_of_measurement if unit_of_measurement else UNIT_CUBIC_METERS
        self._attr_device_class = device_class
        self._attr_icon = icon
        self._attr_state_class = state_class
        self._state = None

    @property
    def native_value(self):
        return self._state

    async def async_update(self):
        try:
            self._state = await self._async_render_template()
        except Exception as e:
            _LOGGER.error("Template rendering failed for %s: %s", self._attr_unique_id, str(e))
            self._state = "error"

    async def _async_render_template(self):
        template = Template(self._state_template, self.hass)
        return template.async_render()

class GasDataSensor(SensorEntity):
    """Sensor that displays gas consumption data with unit conversion."""

    _attr_name = "Gas Consumption Data"
    _attr_unique_id = "gas_consumption_data"

    def __init__(self, hass: HomeAssistant, unit_system: str):
        self.hass = hass
        self._unit_system = unit_system
        self._state = STATE_UNKNOWN
        self._gas_data = []

    async def async_update(self):
        try:
            self._gas_data = await fh.load_gas_actualdata(self.hass)
            if self._gas_data:
                # Format the last record (most recent)
                latest_record = self._gas_data[-1]
                formatted_datetime = latest_record["datetime"].strftime('%Y-%m-%d %H:%M:%S')
                formatted_gas = format_gas_value(
                    latest_record['consumed_gas'],
                    self._unit_system,
                    precision=2
                )
                self._state = f"Last record: {formatted_datetime}, consumed gas: {formatted_gas}"
            else:
                self._state = STATE_UNKNOWN
        except Exception as e:
            _LOGGER.error("Error updating gas sensor: %s", str(e))
            self._state = STATE_UNKNOWN

    @property
    def native_value(self):
        return self._state

    @property
    def extra_state_attributes(self):
        if self._gas_data:
            # Format all records for more user-friendly display on dashboard
            formatted_records = []
            for record in self._gas_data:
                formatted_datetime = record["datetime"].strftime('%Y-%m-%d %H:%M:%S')
                formatted_gas = format_gas_value(
                    record['consumed_gas'],
                    self._unit_system,
                    precision=3
                )
                formatted_cumulative = format_gas_value(
                    record.get('consumed_gas_cumulated', 0),
                    self._unit_system,
                    precision=3
                )
                formatted_record = {
                    "datetime": formatted_datetime,
                    "consumed_gas": formatted_gas,
                    "consumed_gas_cumulated": formatted_cumulative,
                }
                formatted_records.append(formatted_record)

            return {"records": formatted_records}
        return {}


class GasMeterTotalSensor(SensorEntity):
    """Energy Dashboard compatible sensor for total gas consumption.

    This sensor provides a numeric meter reading that can be used
    in the Home Assistant Energy Dashboard for gas tracking.
    """

    _attr_name = "Gas Meter Total"
    _attr_unique_id = "gas_meter_total"
    _attr_device_class = SensorDeviceClass.GAS
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:meter-gas"

    def __init__(self, hass: HomeAssistant, unit_system: str):
        self.hass = hass
        self._unit_system = unit_system
        self._attr_native_unit_of_measurement = get_unit_label(unit_system)
        self._attr_native_value = None

    async def async_update(self):
        try:
            gas_data = await fh.load_gas_actualdata(self.hass)
            if gas_data:
                # Get the latest meter reading and convert to display unit
                latest_record = gas_data[-1]
                canonical_value = latest_record['consumed_gas']
                self._attr_native_value = round(
                    to_display_unit(canonical_value, self._unit_system),
                    3
                )
            else:
                self._attr_native_value = None
        except Exception as e:
            _LOGGER.error("Error updating gas meter total sensor: %s", str(e))
            self._attr_native_value = None


class CustomHistoryStatsSensor(HistoryStatsSensor):
    def __init__(self, entity_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.entity_id = entity_id

    async def async_update(self):
        await self.coordinator.async_request_refresh()



async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities: AddEntitiesCallback):
    """Set up the sensor platform and add the entities."""
    # Get configuration from stored data
    config_data = hass.data.get(DOMAIN, {}).get(config_entry.entry_id, {})
    unit_system = config_data.get(CONF_UNIT_SYSTEM, DEFAULT_UNIT_SYSTEM)
    operating_mode = config_data.get(CONF_OPERATING_MODE, MODE_BOILER_TRACKING)

    # Get the appropriate unit label for display
    unit_label = get_unit_label(unit_system)

    sensors = []

    # Only create boiler tracking sensors if in boiler tracking mode
    if operating_mode == MODE_BOILER_TRACKING:
        sensors.extend([
            CustomTemplateSensor(
                hass=hass,
                friendly_name="Consumed gas",
                unique_id="consumed_gas",
                state_template=f"{{{{ (states('{DOMAIN}.latest_gas_data') | float({DEFAULT_LATEST_GAS_DATA}) + (states('sensor.heating_interval_2') | float(0) * states('{DOMAIN}.average_m3_per_min') | float({DEFAULT_BOILER_AV_M})) | round(3)) }}}}",
                unit_of_measurement=unit_label,
                device_class="gas",
                icon="mdi:gas-cylinder",
                state_class="total",
            ),
            CustomTemplateSensor(
                hass=hass,
                friendly_name="Gas meter latest update",
                unique_id="gas_meter_latest_update",
                state_template=f"{{{{ states('{DOMAIN}.latest_gas_update') if states('{DOMAIN}.latest_gas_update') not in ['unknown', 'unavailable', None] }}}}",
                icon="mdi:clock",
            ),
        ])

    # Add the data display sensor and Energy Dashboard compatible sensor
    async_add_entities([
        GasDataSensor(hass, unit_system),
        GasMeterTotalSensor(hass, unit_system),
    ], True)
    async_add_entities(sensors, update_before_add=True)

    async def create_history_stats_sensor(hass: HomeAssistant, config_entry):
        start_template = Template("{{ states('sensor.gas_meter_latest_update') }}", hass)
        end_template = Template("{{ now() }}", hass)

        boiler_entity = hass.states.get(f"{DOMAIN}.boiler_entity")
        boiler_entity_id = boiler_entity.state if boiler_entity and boiler_entity.state not in [None, "None", "unknown", "unavailable"] else None

        if not boiler_entity_id:
            _LOGGER.warning("No boiler entity configured. History stats sensor will not be created.")
            return

        history_stats = HistoryStats(
            hass=hass,
            entity_id=boiler_entity_id,
            entity_states=["on"],
            start=start_template,
            end=end_template,
            duration=None,
        )

        coordinator = HistoryStatsUpdateCoordinator(
            hass=hass,
            history_stats=history_stats,
            config_entry=config_entry,
            name="Heating Interval"
        )

        await coordinator.async_refresh()

        history_stats_sensor = CustomHistoryStatsSensor(
            entity_id = "sensor.heating_interval",
            hass=hass,
            name="Heating Interval",
            source_entity_id=boiler_entity_id,
            sensor_type="time",
            unique_id="heating_interval",
            coordinator=coordinator
        )

        @callback
        def _handle_coordinator_update():
            """Handle updated data from the coordinator."""
            if history_stats_sensor.hass is None:
                _LOGGER.warning("Skipping update: hass is not available for %s", history_stats_sensor.name)
                return

            history_stats_sensor._attr_state = coordinator.data
            history_stats_sensor.async_write_ha_state()

        coordinator.async_add_listener(_handle_coordinator_update)
        async_add_entities([history_stats_sensor], update_before_add=True)
        _LOGGER.info("Heating Interval sensor added successfully.")

    # Only create history stats sensor in boiler tracking mode
    if operating_mode == MODE_BOILER_TRACKING:
        asyncio.create_task(create_history_stats_sensor(hass, config_entry))
