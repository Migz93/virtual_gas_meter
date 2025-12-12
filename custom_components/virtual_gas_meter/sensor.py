"""Sensor platform for Virtual Gas Meter v3."""
from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    DOMAIN,
    CONF_UNIT,
    UNIT_M3,
    UNIT_CCF,
    SENSOR_GAS_METER_TOTAL,
    SENSOR_CONSUMED_GAS,
    SENSOR_HEATING_INTERVAL,
    DECIMAL_PLACES,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Virtual Gas Meter sensors."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    unit = config_entry.data[CONF_UNIT]
    
    sensors = [
        VGMGasMeterTotalSensor(coordinator, config_entry, unit),
        VGMConsumedGasSensor(coordinator, config_entry, unit),
        VGMHeatingIntervalSensor(coordinator, config_entry),
    ]
    
    async_add_entities(sensors)


class VGMGasMeterTotalSensor(RestoreEntity, SensorEntity):
    """Virtual Gas Meter Total sensor - primary energy dashboard source."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.GAS
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_suggested_display_precision = DECIMAL_PLACES

    def __init__(self, coordinator, config_entry: ConfigEntry, unit: str) -> None:
        """Initialize the sensor."""
        self._coordinator = coordinator
        self._config_entry = config_entry
        self._unit = unit
        self._attr_unique_id = f"{config_entry.entry_id}_{SENSOR_GAS_METER_TOTAL}"
        self._attr_name = "Gas Meter Total"
        
        # Set unit of measurement
        if unit == UNIT_M3:
            self._attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS
        else:  # CCF
            self._attr_native_unit_of_measurement = UNIT_CCF

    @property
    def device_info(self):
        """Return device information."""
        return self._coordinator.device_info

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        return self._coordinator.get_gas_meter_total()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        return {
            "last_real_meter_reading": self._coordinator.get_last_real_meter_reading(),
            "last_real_meter_timestamp": self._coordinator.get_last_real_meter_timestamp(),
            "average_rate_per_h": self._coordinator.get_average_rate_per_h(),
            "boiler_entity_id": self._coordinator.get_boiler_entity_id(),
            "unit": self._unit,
        }

    async def async_added_to_hass(self) -> None:
        """Handle entity added to hass."""
        await super().async_added_to_hass()
        self._coordinator.register_sensor(SENSOR_GAS_METER_TOTAL, self)


class VGMConsumedGasSensor(RestoreEntity, SensorEntity):
    """Consumed Gas sensor - gas consumed since last real reading."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.GAS
    _attr_state_class = SensorStateClass.TOTAL
    _attr_suggested_display_precision = DECIMAL_PLACES

    def __init__(self, coordinator, config_entry: ConfigEntry, unit: str) -> None:
        """Initialize the sensor."""
        self._coordinator = coordinator
        self._config_entry = config_entry
        self._unit = unit
        self._attr_unique_id = f"{config_entry.entry_id}_{SENSOR_CONSUMED_GAS}"
        self._attr_name = "Consumed Gas"
        
        # Set unit of measurement
        if unit == UNIT_M3:
            self._attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS
        else:  # CCF
            self._attr_native_unit_of_measurement = UNIT_CCF

    @property
    def device_info(self):
        """Return device information."""
        return self._coordinator.device_info

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        return self._coordinator.get_consumed_gas()

    async def async_added_to_hass(self) -> None:
        """Handle entity added to hass."""
        await super().async_added_to_hass()
        self._coordinator.register_sensor(SENSOR_CONSUMED_GAS, self)


class VGMHeatingIntervalSensor(RestoreEntity, SensorEntity):
    """Heating Interval sensor - boiler runtime since last real reading."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:clock-outline"

    def __init__(self, coordinator, config_entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        self._coordinator = coordinator
        self._config_entry = config_entry
        self._attr_unique_id = f"{config_entry.entry_id}_{SENSOR_HEATING_INTERVAL}"
        self._attr_name = "Heating Interval"
        self._attr_native_unit_of_measurement = None

    @property
    def device_info(self):
        """Return device information."""
        return self._coordinator.device_info

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        return self._coordinator.get_heating_interval_string()

    async def async_added_to_hass(self) -> None:
        """Handle entity added to hass."""
        await super().async_added_to_hass()
        self._coordinator.register_sensor(SENSOR_HEATING_INTERVAL, self)
