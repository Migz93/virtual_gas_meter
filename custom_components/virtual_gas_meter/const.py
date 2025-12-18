"""Constants for Virtual Gas Meter v3."""

DOMAIN = "gas_meter"

# Unit options
UNIT_M3 = "m3"
UNIT_CCF = "CCF"
UNIT_OPTIONS = [UNIT_M3, UNIT_CCF]

# Config entry keys
CONF_BOILER_ENTITY = "boiler_entity_id"
CONF_UNIT = "unit"
CONF_INITIAL_METER_READING = "initial_meter_reading"
CONF_INITIAL_AVERAGE_RATE = "initial_average_rate"

# Storage keys
STORAGE_VERSION = 1
STORAGE_KEY = "gas_meter_v3"

# Sensor entity IDs
SENSOR_GAS_METER_TOTAL = "vgm_gas_meter_total"
SENSOR_CONSUMED_GAS = "vgm_consumed_gas"
SENSOR_HEATING_INTERVAL = "vgm_heating_interval"

# Service names
SERVICE_REAL_METER_READING_UPDATE = "real_meter_reading_update"

# Service parameters
ATTR_METER_READING = "meter_reading"
ATTR_TIMESTAMP = "timestamp"
ATTR_RECALCULATE_AVERAGE_RATE = "recalculate_average_rate"

# Device info
DEVICE_NAME = "Virtual Gas Meter"
DEVICE_MANUFACTURER = "Virtual Gas Meter"
DEVICE_MODEL = "Boiler Runtime Estimator"

# Allowed boiler entity domains
ALLOWED_BOILER_DOMAINS = ["switch", "climate", "binary_sensor", "sensor"]

# Update interval (seconds)
UPDATE_INTERVAL = 60

# Decimal places
DECIMAL_PLACES = 3

# Time constants
MINUTES_PER_HOUR = 60
