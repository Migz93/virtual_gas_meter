"""Virtual Gas Meter integration for Home Assistant."""
import logging
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.components.recorder.history import get_significant_states
from homeassistant.components.recorder import get_instance
from homeassistant.util import dt as dt_util
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import entity_registry as er
import custom_components.gas_meter.file_handler as fh
from .const import (
    DOMAIN,
    CONF_BOILER_ENTITY,
    CONF_BOILER_AVERAGE,
    CONF_LATEST_GAS_DATA,
    CONF_UNIT_SYSTEM,
    CONF_OPERATING_MODE,
    DEFAULT_BOILER_AV_H,
    DEFAULT_BOILER_AV_M,
    DEFAULT_LATEST_GAS_DATA,
    DEFAULT_UNIT_SYSTEM,
    DEFAULT_OPERATING_MODE,
    MODE_BOILER_TRACKING,
    MODE_BILL_ENTRY,
)
from .unit_converter import to_canonical_unit, get_unit_label

_LOGGER = logging.getLogger(__name__)

async def _register_services(hass: HomeAssistant):
    """Register services for gas meter integration."""
    
    async def handle_trigger_service(call: ServiceCall):
        """Handle service call to update gas meter data."""
        try:
            gas_consume = await fh.load_gas_actualdata(hass)
            datetime_received = call.data.get("datetime")
            if datetime_received is None:
                _LOGGER.error("Missing 'datetime' in service call data.")
                return
            _LOGGER.info(f"datetime_received: {datetime_received}")
            if isinstance(datetime_received, str):
                try:
                    gas_new_datetime = fh.string_to_datetime(datetime_received)
                except Exception as e:
                    _LOGGER.error(f"Error parsing datetime string: {e}")
                    return
            else:
                gas_new_datetime = datetime_received

            gas_new_data = call.data.get("consumed_gas")
            if gas_new_data is None:
                _LOGGER.error("Missing 'consumed_gas' in service call data.")
                return
            _LOGGER.info(f"consumed_gas received: {gas_new_data}")
            if isinstance(gas_new_data, str):
                try:
                    gas_new_data = float(gas_new_data)
                except ValueError:
                    _LOGGER.error(f"Invalid 'consumed_gas' value: {gas_new_data}")
                    return

            # Convert input value to canonical unit (m³) if user is using imperial
            unit_system_state = hass.states.get(f"{DOMAIN}.unit_system")
            unit_system = unit_system_state.state if unit_system_state else DEFAULT_UNIT_SYSTEM
            gas_new_data = to_canonical_unit(gas_new_data, unit_system)
            _LOGGER.debug(f"consumed_gas in canonical units (m³): {gas_new_data}")

            gas_consume.add_record(gas_new_datetime, gas_new_data)
            _LOGGER.info("Gas meter data updated successfully.")

            if len(gas_consume) > 1:
                gas_prev_datetime = gas_consume[-2]["datetime"]
                gas_prev_data = gas_consume[-2]["consumed_gas"]

                # Get the state history of the switch between the two timestamps
                start_time = dt_util.as_utc(gas_prev_datetime)
                end_time = dt_util.as_utc(gas_new_datetime)
                entity_id = f"{DOMAIN}.boiler_entity"
                history_list = await get_instance(hass).async_add_executor_job(
                    get_significant_states, hass, start_time, end_time, [entity_id]
                    )

                # Calculate the total time the switch was "on"
                total_on_time = 0
                previous_state = None
                previous_time = start_time
                for state in history_list.get(entity_id, []):
                    current_time = state.last_changed

                    if previous_state == "on":
                        total_on_time += (current_time - previous_time).total_seconds()

                    previous_state = state.state
                    previous_time = current_time

                # Handle the last segment
                if previous_state == "on":
                    total_on_time += (end_time - previous_time).total_seconds()

                total_min = total_on_time / 60  # Total time in minutes

                # Count m3/min for the current interval ("m3/min for interval")
                gas_data_diff = gas_new_data - gas_prev_data
                if total_min:
                    gas_consume[-1]["m3/min for interval"] = gas_data_diff / total_min
                
                # Count how much gas was consumed from the first data till the last data ("consumed_gas_cumulated")
                consumed_gas_cumulated = gas_new_data - gas_consume[0]["consumed_gas"]
                gas_consume[-1]["consumed_gas_cumulated"] = consumed_gas_cumulated

                # Count how many minutes the boiler was working starting from the first data till the last data ("min_cumulated")
                if len(gas_consume) == 2:
                    min_cumulated = total_min
                elif len(gas_consume) > 2:
                    min_cumulated = total_min + gas_consume[-2]["min_cumulated"]
                gas_consume[-1]["min_cumulated"] = min_cumulated

                # Count m3/min for the whole period between the first data till the last data ("average m3/min")
                if min_cumulated:
                    av_min = consumed_gas_cumulated / min_cumulated
                    gas_consume[-1]["average m3/min"] = av_min

                    hass.states.async_set(f"{DOMAIN}.average_m3_per_min", av_min)
                    
            hass.states.async_set(f"{DOMAIN}.latest_gas_update", gas_new_datetime)
            hass.states.async_set(f"{DOMAIN}.latest_gas_data", gas_new_data)

            # Save updated gas consumption
            await fh.save_gas_actualdata(gas_consume, hass)

        except Exception as e:
            _LOGGER.error("Error in handle_trigger_service: %s", str(e))
            raise
            
    async def read_gas_actualdata_file(call: ServiceCall):
        """Read and log gas meter data."""
        try:
            gas_consume = await fh.load_gas_actualdata(hass)
            for record in gas_consume:
                _LOGGER.info("Gas record: %s", record)
            # Get the GasDataSensor entity object
            entity_registry = er.async_get(hass)
            gas_data_sensor_entity_id = entity_registry.async_get_entity_id("sensor", DOMAIN, "gas_consumption_data")

            if gas_data_sensor_entity_id:
                gas_data_sensor_entity = hass.states.get(gas_data_sensor_entity_id)
                if gas_data_sensor_entity:
                    # Trigger the sensor's async_update()
                    entity = hass.data["entity_components"]["sensor"].get_entity(gas_data_sensor_entity_id)
                    _LOGGER.info(f"Entity component for GasDataSensor: {entity}")
                    if entity:
                        await entity.async_update()
                        _LOGGER.info("GasDataSensor updated successfully.")
                    else:
                        _LOGGER.warning(f"Could not get entity from entity component for {gas_data_sensor_entity_id}")
                else:
                    _LOGGER.warning(f"Could not get state for {gas_data_sensor_entity_id}")
            else:
                _LOGGER.warning("GasDataSensor entity not found in registry.")
        except Exception as e:
            _LOGGER.error("Error in read_gas_actualdata_file: %s", str(e))
            raise
            
    async def handle_bill_entry(call: ServiceCall):
        """Handle service call to enter a bill reading (simplified for bill entry mode)."""
        try:
            gas_consume = await fh.load_gas_actualdata(hass)

            # Parse billing date
            billing_date = call.data.get("billing_date")
            if billing_date is None:
                _LOGGER.error("Missing 'billing_date' in service call data.")
                return

            _LOGGER.info(f"billing_date received: {billing_date}")
            if isinstance(billing_date, str):
                try:
                    from .datetime_handler import string_to_datetime
                    gas_datetime = string_to_datetime(billing_date)
                except Exception as e:
                    _LOGGER.error(f"Error parsing billing_date string: {e}")
                    return
            else:
                gas_datetime = billing_date

            # Parse meter reading
            meter_reading = call.data.get("meter_reading")
            if meter_reading is None:
                _LOGGER.error("Missing 'meter_reading' in service call data.")
                return

            _LOGGER.info(f"meter_reading received: {meter_reading}")
            if isinstance(meter_reading, str):
                try:
                    meter_reading = float(meter_reading)
                except ValueError:
                    _LOGGER.error(f"Invalid 'meter_reading' value: {meter_reading}")
                    return

            # Convert input value to canonical unit (m³) if user is using imperial
            unit_system_state = hass.states.get(f"{DOMAIN}.unit_system")
            unit_system = unit_system_state.state if unit_system_state else DEFAULT_UNIT_SYSTEM
            meter_reading_canonical = to_canonical_unit(meter_reading, unit_system)
            _LOGGER.debug(f"meter_reading in canonical units (m³): {meter_reading_canonical}")

            # Add record
            gas_consume.add_record(gas_datetime, meter_reading_canonical)

            # Calculate cumulative consumption if we have previous records
            if len(gas_consume) > 1:
                consumed_gas_cumulated = meter_reading_canonical - gas_consume[0]["consumed_gas"]
                gas_consume[-1]["consumed_gas_cumulated"] = consumed_gas_cumulated

            # Update states
            hass.states.async_set(f"{DOMAIN}.latest_gas_update", gas_datetime)
            hass.states.async_set(f"{DOMAIN}.latest_gas_data", meter_reading_canonical)

            # Save updated gas consumption
            await fh.save_gas_actualdata(gas_consume, hass)
            _LOGGER.info("Bill reading added successfully.")

        except Exception as e:
            _LOGGER.error("Error in handle_bill_entry: %s", str(e))
            raise

    # Register the services
    hass.services.async_register(
        DOMAIN, "trigger_gas_update", handle_trigger_service
    )
    hass.services.async_register(
        DOMAIN, "enter_bill_reading", handle_bill_entry
    )
    hass.services.async_register(
        DOMAIN, "read_gas_actualdata_file", read_gas_actualdata_file
    )

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Set up the integration from a config entry (UI setup)."""
    await _register_services(hass)

    # Retrieve user input values
    unit_system = config_entry.data.get(CONF_UNIT_SYSTEM, DEFAULT_UNIT_SYSTEM)
    operating_mode = config_entry.data.get(CONF_OPERATING_MODE, DEFAULT_OPERATING_MODE)
    latest_gas_data = config_entry.data.get(CONF_LATEST_GAS_DATA, DEFAULT_LATEST_GAS_DATA)
    now = dt_util.now()

    # Store config in hass.data for access by sensors
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = {
        CONF_UNIT_SYSTEM: unit_system,
        CONF_OPERATING_MODE: operating_mode,
    }

    # Set common initial states
    hass.states.async_set(f"{DOMAIN}.unit_system", unit_system)
    hass.states.async_set(f"{DOMAIN}.operating_mode", operating_mode)
    hass.states.async_set(f"{DOMAIN}.latest_gas_data", latest_gas_data)
    hass.states.async_set(f"{DOMAIN}.latest_gas_update", now)

    # Mode-specific setup
    if operating_mode == MODE_BOILER_TRACKING:
        boiler_entity = config_entry.data.get(CONF_BOILER_ENTITY)
        boiler_average = config_entry.data.get(CONF_BOILER_AVERAGE, DEFAULT_BOILER_AV_H)
        boiler_av_min = boiler_average / 60

        hass.states.async_set(f"{DOMAIN}.boiler_entity", boiler_entity)
        hass.states.async_set(f"{DOMAIN}.average_m3_per_min", boiler_av_min)

        _LOGGER.info(f"Virtual Gas Meter configured in Boiler Tracking mode with {unit_system} units")
    else:
        # Bill entry mode - no boiler entity needed
        hass.states.async_set(f"{DOMAIN}.boiler_entity", None)
        hass.states.async_set(f"{DOMAIN}.average_m3_per_min", 0)

        _LOGGER.info(f"Virtual Gas Meter configured in Bill Entry mode with {unit_system} units")

    # Add the first record to the file if latest_gas_data is not 0
    if latest_gas_data != 0:
        # Convert initial value to canonical unit (m³) before storing
        initial_gas_canonical = to_canonical_unit(latest_gas_data, unit_system)
        _LOGGER.debug(f"Initial gas data: {latest_gas_data} ({unit_system}) -> {initial_gas_canonical} m³")

        # Add directly to storage instead of calling service to avoid conversion happening twice
        gas_consume = await fh.load_gas_actualdata(hass)
        gas_consume.add_record(now, initial_gas_canonical)
        await fh.save_gas_actualdata(gas_consume, hass)

        # Update state with canonical value
        hass.states.async_set(f"{DOMAIN}.latest_gas_data", initial_gas_canonical)
        _LOGGER.info("Added initial gas record to storage.")

    await hass.config_entries.async_forward_entry_setups(config_entry, ["sensor"])
    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Unload the integration."""
    # Clean up hass.data
    if DOMAIN in hass.data and config_entry.entry_id in hass.data[DOMAIN]:
        hass.data[DOMAIN].pop(config_entry.entry_id)

    await hass.config_entries.async_forward_entry_unload(config_entry, "sensor")
    return True
