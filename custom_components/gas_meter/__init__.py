"""Virtual Gas Meter v3 integration."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EVENT_HOMEASSISTANT_STOP,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.helpers.device_registry import DeviceInfo

from .const import (
    DOMAIN,
    CONF_BOILER_ENTITY,
    CONF_UNIT,
    CONF_INITIAL_METER_READING,
    CONF_INITIAL_AVERAGE_RATE,
    STORAGE_VERSION,
    STORAGE_KEY,
    SERVICE_REAL_METER_READING_UPDATE,
    ATTR_METER_READING,
    ATTR_TIMESTAMP,
    ATTR_RECALCULATE_AVERAGE_RATE,
    DEVICE_NAME,
    DEVICE_MANUFACTURER,
    DEVICE_MODEL,
    UPDATE_INTERVAL,
    DECIMAL_PLACES,
    SENSOR_GAS_METER_TOTAL,
    SENSOR_CONSUMED_GAS,
    SENSOR_HEATING_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Virtual Gas Meter from a config entry."""
    coordinator = VirtualGasMeterCoordinator(hass, entry)
    await coordinator.async_setup()
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Register service
    async def handle_real_meter_reading_update(call: ServiceCall) -> None:
        """Handle real meter reading update service."""
        await coordinator.handle_real_meter_reading_update(call)
    
    hass.services.async_register(
        DOMAIN,
        SERVICE_REAL_METER_READING_UPDATE,
        handle_real_meter_reading_update,
        schema=vol.Schema(
            {
                vol.Required(ATTR_METER_READING): cv.positive_float,
                vol.Optional(ATTR_TIMESTAMP): cv.datetime,
                vol.Optional(ATTR_RECALCULATE_AVERAGE_RATE, default=True): cv.boolean,
            }
        ),
    )
    
    _LOGGER.info("Virtual Gas Meter v3 integration loaded")
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    await coordinator.async_unload()
    
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        
        # Remove service if no more instances
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_REAL_METER_READING_UPDATE)
    
    return unload_ok


class VirtualGasMeterCoordinator:
    """Coordinator for Virtual Gas Meter."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.hass = hass
        self.entry = entry
        self._store = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY}_{entry.entry_id}")
        
        # Config data
        self._boiler_entity_id = entry.data[CONF_BOILER_ENTITY]
        self._unit = entry.data[CONF_UNIT]
        self._initial_meter_reading = entry.data[CONF_INITIAL_METER_READING]
        self._initial_average_rate = entry.data[CONF_INITIAL_AVERAGE_RATE]
        
        # Runtime state
        self._last_real_meter_reading: float = self._initial_meter_reading
        self._last_real_meter_timestamp: datetime = datetime.now()
        self._average_rate_per_h: float = self._initial_average_rate
        self._consumed_gas: float = 0.0
        self._heating_interval_minutes: int = 0
        self._boiler_last_state: str | None = None
        self._boiler_state_change_time: datetime | None = None
        
        # Sensor references
        self._sensors: dict[str, Any] = {}
        
        # Listeners
        self._unsub_boiler_listener = None
        self._unsub_interval_listener = None
        
        # Device info
        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=DEVICE_NAME,
            manufacturer=DEVICE_MANUFACTURER,
            model=DEVICE_MODEL,
        )

    async def async_setup(self) -> None:
        """Set up the coordinator."""
        # Load persisted data
        await self._load_data()
        
        # Start boiler state listener
        self._unsub_boiler_listener = async_track_state_change_event(
            self.hass,
            [self._boiler_entity_id],
            self._handle_boiler_state_change,
        )
        
        # Start interval update (60 seconds)
        self._unsub_interval_listener = async_track_time_interval(
            self.hass,
            self._handle_interval_update,
            timedelta(seconds=UPDATE_INTERVAL),
        )
        
        # Initialize boiler state
        state = self.hass.states.get(self._boiler_entity_id)
        if state:
            self._boiler_last_state = self._get_boiler_state(state.state)
            self._boiler_state_change_time = datetime.now()

    async def async_unload(self) -> None:
        """Unload the coordinator."""
        if self._unsub_boiler_listener:
            self._unsub_boiler_listener()
        if self._unsub_interval_listener:
            self._unsub_interval_listener()
        
        await self._save_data()

    def register_sensor(self, sensor_type: str, sensor: Any) -> None:
        """Register a sensor."""
        self._sensors[sensor_type] = sensor

    def get_boiler_entity_id(self) -> str:
        """Get boiler entity ID."""
        return self._boiler_entity_id

    def get_gas_meter_total(self) -> float:
        """Get gas meter total."""
        total = self._last_real_meter_reading + self._consumed_gas
        return round(total, DECIMAL_PLACES)

    def get_consumed_gas(self) -> float:
        """Get consumed gas."""
        return round(self._consumed_gas, DECIMAL_PLACES)

    def get_last_real_meter_reading(self) -> float:
        """Get last real meter reading."""
        return round(self._last_real_meter_reading, DECIMAL_PLACES)

    def get_last_real_meter_timestamp(self) -> str:
        """Get last real meter timestamp."""
        return self._last_real_meter_timestamp.isoformat()

    def get_average_rate_per_h(self) -> float:
        """Get average rate per hour."""
        return round(self._average_rate_per_h, DECIMAL_PLACES)

    def get_heating_interval_string(self) -> str:
        """Get heating interval as string."""
        hours = self._heating_interval_minutes // 60
        minutes = self._heating_interval_minutes % 60
        return f"{hours}h {minutes}m"

    def _get_boiler_state(self, state_str: str) -> str:
        """Determine if boiler is on or off."""
        if state_str in [STATE_UNAVAILABLE, STATE_UNKNOWN]:
            return "off"
        
        # Handle different entity types
        entity_domain = self._boiler_entity_id.split(".")[0]
        
        if entity_domain == "climate":
            # For climate entities, check if hvac_action is heating
            state_obj = self.hass.states.get(self._boiler_entity_id)
            if state_obj and state_obj.attributes.get("hvac_action") == "heating":
                return "on"
            return "off"
        elif entity_domain in ["switch", "binary_sensor"]:
            return "on" if state_str == STATE_ON else "off"
        elif entity_domain == "sensor":
            # For sensor, treat numeric > 0 or "on" as on
            try:
                return "on" if float(state_str) > 0 else "off"
            except (ValueError, TypeError):
                return "on" if state_str.lower() == "on" else "off"
        
        return "off"

    @callback
    def _handle_boiler_state_change(self, event) -> None:
        """Handle boiler state changes."""
        new_state = event.data.get("new_state")
        if not new_state:
            return
        
        current_boiler_state = self._get_boiler_state(new_state.state)
        
        _LOGGER.debug(
            "Boiler state change: %s -> %s",
            self._boiler_last_state,
            current_boiler_state,
        )
        
        # If turning off, perform final tick
        if self._boiler_last_state == "on" and current_boiler_state == "off":
            self._perform_tick()
        
        self._boiler_last_state = current_boiler_state
        self._boiler_state_change_time = datetime.now()

    @callback
    def _handle_interval_update(self, now: datetime) -> None:
        """Handle interval updates (every 60 seconds)."""
        if self._boiler_last_state == "on":
            self._perform_tick()

    def _perform_tick(self) -> None:
        """Perform a runtime tick."""
        # Increment runtime by 1 minute
        self._heating_interval_minutes += 1
        
        # Calculate consumption increment
        consumed_increment = self._average_rate_per_h / 60.0
        self._consumed_gas += consumed_increment
        
        _LOGGER.debug(
            "Runtime tick: interval=%s, consumed_increment=%.3f, total_consumed=%.3f, meter_total=%.3f",
            self.get_heating_interval_string(),
            consumed_increment,
            self._consumed_gas,
            self.get_gas_meter_total(),
        )
        
        # Update sensors
        self._update_sensors()
        
        # Save state
        self.hass.async_create_task(self._save_data())

    def _update_sensors(self) -> None:
        """Update all sensors."""
        for sensor in self._sensors.values():
            sensor.async_schedule_update_ha_state(force_refresh=True)

    async def handle_real_meter_reading_update(self, call: ServiceCall) -> None:
        """Handle real meter reading update service call."""
        meter_reading = call.data[ATTR_METER_READING]
        timestamp = call.data.get(ATTR_TIMESTAMP, datetime.now())
        recalculate = call.data.get(ATTR_RECALCULATE_AVERAGE_RATE, True)
        
        # Validation: meter_reading must be >= last_real
        if meter_reading < self._last_real_meter_reading:
            _LOGGER.error(
                "Real meter reading update failed: New reading (%.3f) is less than previous reading (%.3f)",
                meter_reading,
                self._last_real_meter_reading,
            )
            return
        
        old_reading = self._last_real_meter_reading
        runtime_minutes = self._heating_interval_minutes
        runtime_hours = runtime_minutes / 60.0
        
        # If runtime is zero, just snap the values
        if runtime_minutes == 0:
            self._last_real_meter_reading = meter_reading
            self._last_real_meter_timestamp = timestamp
            self._consumed_gas = 0.0
            self._heating_interval_minutes = 0
            
            _LOGGER.info(
                "Real meter reading update (runtime=0): reading=%.3f -> %.3f",
                old_reading,
                meter_reading,
            )
        else:
            # Recalculate average rate if enabled
            if recalculate:
                actual_used = meter_reading - self._last_real_meter_reading
                new_average_rate = actual_used / runtime_hours
                
                _LOGGER.info(
                    "Real meter reading update: reading=%.3f -> %.3f, runtime=%dm (%.2fh), actual_used=%.3f, new_rate=%.3f %s/h",
                    old_reading,
                    meter_reading,
                    runtime_minutes,
                    runtime_hours,
                    actual_used,
                    new_average_rate,
                    self._unit,
                )
                
                self._average_rate_per_h = new_average_rate
            else:
                _LOGGER.info(
                    "Real meter reading update (no recalc): reading=%.3f -> %.3f, runtime=%dm",
                    old_reading,
                    meter_reading,
                    runtime_minutes,
                )
            
            # Apply result
            self._last_real_meter_reading = meter_reading
            self._last_real_meter_timestamp = timestamp
            self._consumed_gas = 0.0
            self._heating_interval_minutes = 0
        
        # Update sensors
        self._update_sensors()
        
        # Save state
        await self._save_data()

    async def _load_data(self) -> None:
        """Load persisted data."""
        data = await self._store.async_load()
        
        if data:
            self._last_real_meter_reading = data.get(
                "last_real_meter_reading", self._initial_meter_reading
            )
            self._last_real_meter_timestamp = datetime.fromisoformat(
                data.get("last_real_meter_timestamp", datetime.now().isoformat())
            )
            self._average_rate_per_h = data.get(
                "average_rate_per_h", self._initial_average_rate
            )
            self._consumed_gas = data.get("consumed_gas", 0.0)
            self._heating_interval_minutes = data.get("heating_interval_minutes", 0)
            
            _LOGGER.debug(
                "Loaded persisted data: last_reading=%.3f, consumed=%.3f, interval=%dm, rate=%.3f",
                self._last_real_meter_reading,
                self._consumed_gas,
                self._heating_interval_minutes,
                self._average_rate_per_h,
            )

    async def _save_data(self) -> None:
        """Save data to storage."""
        data = {
            "last_real_meter_reading": self._last_real_meter_reading,
            "last_real_meter_timestamp": self._last_real_meter_timestamp.isoformat(),
            "average_rate_per_h": self._average_rate_per_h,
            "consumed_gas": self._consumed_gas,
            "heating_interval_minutes": self._heating_interval_minutes,
            "unit": self._unit,
            "boiler_entity_id": self._boiler_entity_id,
        }
        
        await self._store.async_save(data)
