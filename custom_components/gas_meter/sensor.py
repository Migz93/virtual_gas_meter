"""Sensor platform for the Virtual Gas Meter integration."""
import logging
import asyncio

from datetime import datetime
from homeassistant.const import STATE_UNKNOWN
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.core import HomeAssistant, callback, ServiceCall
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.helpers.entity import EntityCategory
from homeassistant.components.history_stats.sensor import HistoryStatsSensor
from homeassistant.components.history_stats.coordinator import HistoryStatsUpdateCoordinator, HistoryStats
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers import entity_registry as er
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
    UNIT_SYSTEM_IMPERIAL,
    M3_TO_CCF,
)
from .unit_converter import get_unit_label, format_gas_value, to_display_unit
import custom_components.gas_meter.file_handler as fh

_LOGGER = logging.getLogger(__name__)

class CustomTemplateSensor(SensorEntity):
    def __init__(self, hass, friendly_name, unique_id, state_template, device_info, unit_of_measurement=None, device_class=None, icon=None, state_class=None):
        self.hass = hass
        self._attr_name = friendly_name
        self._attr_unique_id = unique_id
        self._desired_entity_id = f"sensor.{unique_id}"
        self._state_template = state_template
        self._attr_unit_of_measurement = unit_of_measurement if unit_of_measurement else UNIT_CUBIC_METERS
        self._attr_device_class = device_class
        self._attr_icon = icon
        self._attr_state_class = state_class
        self._attr_device_info = device_info
        self._state = None

    async def async_added_to_hass(self):
        """Set the entity ID when added to hass."""
        if self.entity_id != self._desired_entity_id:
            entity_registry = er.async_get(self.hass)
            entity_registry.async_update_entity(self.entity_id, new_entity_id=self._desired_entity_id)

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
    """Sensor that displays gas usage history with unit conversion."""

    _attr_name = "Gas Usage History"
    _attr_unique_id = "vgm_gas_consumption_data"

    def __init__(self, hass: HomeAssistant, unit_system: str, device_info: DeviceInfo):
        self.hass = hass
        self._unit_system = unit_system
        self._attr_device_info = device_info
        self._desired_entity_id = "sensor.vgm_gas_consumption_data"
        self._state = STATE_UNKNOWN
        self._gas_data = []

    async def async_added_to_hass(self):
        """Set the entity ID when added to hass."""
        if self.entity_id != self._desired_entity_id:
            entity_registry = er.async_get(self.hass)
            entity_registry.async_update_entity(self.entity_id, new_entity_id=self._desired_entity_id)

    async def async_update(self):
        try:
            self._gas_data = await fh.load_gas_actualdata(self.hass)
            if self._gas_data:
                # Format the last record (most recent)
                latest_record = self._gas_data[-1]
                formatted_datetime = latest_record["datetime"].strftime('%Y-%m-%d')
                formatted_usage = format_gas_value(
                    latest_record['consumed_gas'],
                    self._unit_system,
                    precision=2
                )
                formatted_total = format_gas_value(
                    latest_record.get('consumed_gas_cumulated', latest_record['consumed_gas']),
                    self._unit_system,
                    precision=2
                )
                self._state = f"{formatted_datetime}: {formatted_usage} (Total: {formatted_total})"
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
            # Format all records for dashboard display
            formatted_records = []
            for record in self._gas_data:
                formatted_datetime = record["datetime"].strftime('%Y-%m-%d')
                formatted_usage = format_gas_value(
                    record['consumed_gas'],
                    self._unit_system,
                    precision=2
                )
                formatted_cumulative = format_gas_value(
                    record.get('consumed_gas_cumulated', record['consumed_gas']),
                    self._unit_system,
                    precision=2
                )
                formatted_record = {
                    "date": formatted_datetime,
                    "usage": formatted_usage,
                    "cumulative_total": formatted_cumulative,
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
    _attr_unique_id = "vgm_gas_meter_total"
    _attr_device_class = SensorDeviceClass.GAS
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:meter-gas"

    def __init__(self, hass: HomeAssistant, unit_system: str, device_info: DeviceInfo):
        self.hass = hass
        self._unit_system = unit_system
        self._attr_device_info = device_info
        self._desired_entity_id = "sensor.vgm_gas_meter_total"
        self._attr_native_unit_of_measurement = get_unit_label(unit_system)
        self._attr_native_value = None

    async def async_added_to_hass(self):
        """Set the entity ID when added to hass."""
        if self.entity_id != self._desired_entity_id:
            entity_registry = er.async_get(self.hass)
            entity_registry.async_update_entity(self.entity_id, new_entity_id=self._desired_entity_id)

    async def async_update(self):
        try:
            gas_data = await fh.load_gas_actualdata(self.hass)
            if gas_data:
                # Get the cumulative total and convert to display unit
                latest_record = gas_data[-1]
                # Use cumulative total, fallback to consumed_gas for first record
                canonical_value = latest_record.get(
                    'consumed_gas_cumulated',
                    latest_record['consumed_gas']
                )
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
    def __init__(self, sensor_entity_id, device_info, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.entity_id = sensor_entity_id
        self._attr_device_info = device_info

    async def async_update(self):
        await self.coordinator.async_request_refresh()


class InternalStateSensor(SensorEntity):
    """Base class for internal state sensors that read from hass.data."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        name: str,
        unique_id: str,
        data_key: str,
        device_info: DeviceInfo,
        icon: str = None,
        unit_of_measurement: str = None,
        device_class: SensorDeviceClass = None,
        state_class: SensorStateClass = None,
        entity_category: EntityCategory = EntityCategory.DIAGNOSTIC,
    ):
        self.hass = hass
        self._config_entry_id = config_entry_id
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._desired_entity_id = f"sensor.{unique_id}"
        self._data_key = data_key
        self._attr_device_info = device_info
        self._attr_icon = icon
        self._attr_native_unit_of_measurement = unit_of_measurement
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_entity_category = entity_category

    async def async_added_to_hass(self):
        """Set the entity ID when added to hass."""
        if self.entity_id != self._desired_entity_id:
            entity_registry = er.async_get(self.hass)
            entity_registry.async_update_entity(self.entity_id, new_entity_id=self._desired_entity_id)

    @property
    def native_value(self):
        """Return the state from hass.data."""
        data = self.hass.data.get(DOMAIN, {}).get(self._config_entry_id, {})
        return data.get(self._data_key)


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities: AddEntitiesCallback):
    """Set up the sensor platform and add the entities."""
    # Get configuration from stored data
    config_data = hass.data.get(DOMAIN, {}).get(config_entry.entry_id, {})
    unit_system = config_data.get(CONF_UNIT_SYSTEM, DEFAULT_UNIT_SYSTEM)
    operating_mode = config_data.get(CONF_OPERATING_MODE, MODE_BOILER_TRACKING)
    device_info = config_data.get("device_info")

    # Get the appropriate unit label for display
    unit_label = get_unit_label(unit_system)
    
    # Conversion factor: 1.0 for metric (no change), M3_TO_CCF for imperial
    unit_conversion_factor = M3_TO_CCF if unit_system == UNIT_SYSTEM_IMPERIAL else 1.0

    sensors = []
    
    # Create internal state sensors (diagnostic entities)
    internal_sensors = [
        InternalStateSensor(
            hass=hass,
            config_entry_id=config_entry.entry_id,
            name="Unit System",
            unique_id="vgm_unit_system",
            data_key="unit_system",
            device_info=device_info,
            icon="mdi:ruler",
        ),
        InternalStateSensor(
            hass=hass,
            config_entry_id=config_entry.entry_id,
            name="Operating Mode",
            unique_id="vgm_operating_mode",
            data_key="operating_mode",
            device_info=device_info,
            icon="mdi:cog",
        ),
        InternalStateSensor(
            hass=hass,
            config_entry_id=config_entry.entry_id,
            name="Latest Gas Data",
            unique_id="vgm_latest_gas_data",
            data_key="latest_gas_data",
            device_info=device_info,
            icon="mdi:meter-gas",
            unit_of_measurement=UNIT_CUBIC_METERS,
        ),
        InternalStateSensor(
            hass=hass,
            config_entry_id=config_entry.entry_id,
            name="Latest Gas Update",
            unique_id="vgm_latest_gas_update",
            data_key="latest_gas_update",
            device_info=device_info,
            icon="mdi:clock-outline",
            device_class=SensorDeviceClass.TIMESTAMP,
        ),
    ]

    # Only create boiler tracking sensors if in boiler tracking mode
    if operating_mode == MODE_BOILER_TRACKING:
        internal_sensors.extend([
            InternalStateSensor(
                hass=hass,
                config_entry_id=config_entry.entry_id,
                name="Boiler Entity",
                unique_id="vgm_boiler_entity",
                data_key="boiler_entity",
                device_info=device_info,
                icon="mdi:water-boiler",
            ),
            InternalStateSensor(
                hass=hass,
                config_entry_id=config_entry.entry_id,
                name="Average Gas Per Minute",
                unique_id="vgm_average_m3_per_min",
                data_key="average_m3_per_min",
                device_info=device_info,
                icon="mdi:speedometer",
                unit_of_measurement=f"{UNIT_CUBIC_METERS}/min",
            ),
        ])
        
        sensors.extend([
            CustomTemplateSensor(
                hass=hass,
                friendly_name="Consumed gas",
                unique_id="vgm_consumed_gas",
                state_template=f"{{{{ ((states('sensor.vgm_latest_gas_data') | float({DEFAULT_LATEST_GAS_DATA}) + (states('sensor.vgm_heating_interval') | float(0) * states('sensor.vgm_average_m3_per_min') | float({DEFAULT_BOILER_AV_M}))) * {unit_conversion_factor}) | round(3) }}}}",
                device_info=device_info,
                unit_of_measurement=unit_label,
                device_class="gas",
                icon="mdi:gas-cylinder",
                state_class="total",
            ),
        ])

    # Add all internal state sensors
    async_add_entities(internal_sensors, True)
    
    # Add the data display sensor and Energy Dashboard compatible sensor
    async_add_entities([
        GasDataSensor(hass, unit_system, device_info),
        GasMeterTotalSensor(hass, unit_system, device_info),
    ], True)
    async_add_entities(sensors, update_before_add=True)

    async def create_history_stats_sensor(hass: HomeAssistant, config_entry, device_info):
        try:
            start_template = Template("{{ states('sensor.vgm_latest_gas_update') }}", hass)
            end_template = Template("{{ now() }}", hass)

            # Get boiler entity from hass.data instead of raw state
            config_data = hass.data.get(DOMAIN, {}).get(config_entry.entry_id, {})
            boiler_entity_id = config_data.get("boiler_entity")

            if not boiler_entity_id or boiler_entity_id in [None, "None", "unknown", "unavailable"]:
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
                sensor_entity_id="sensor.vgm_heating_interval",
                device_info=device_info,
                hass=hass,
                name="Heating Interval",
                source_entity_id=boiler_entity_id,
                sensor_type="time",
                unique_id="vgm_heating_interval",
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
        except Exception as e:
            _LOGGER.error("Failed to create history stats sensor: %s", str(e))

    # Only create history stats sensor in boiler tracking mode
    if operating_mode == MODE_BOILER_TRACKING:
        hass.async_create_task(create_history_stats_sensor(hass, config_entry, device_info))
