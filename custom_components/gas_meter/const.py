"""Constants for the Virtual Gas Meter integration."""

DOMAIN = "gas_meter"

# Configuration keys
CONF_BOILER_ENTITY = "boiler_entity"
CONF_BOILER_AVERAGE = "boiler_average"
CONF_LATEST_GAS_DATA = "latest_gas_data"
CONF_UNIT_SYSTEM = "unit_system"
CONF_OPERATING_MODE = "operating_mode"

# Unit system options
UNIT_SYSTEM_METRIC = "metric"
UNIT_SYSTEM_IMPERIAL = "imperial"

# Unit labels for display
UNIT_CUBIC_METERS = "m³"
UNIT_CCF = "CCF"
UNIT_CF = "ft³"
UNIT_THERMS = "therms"

# Operating modes
MODE_BOILER_TRACKING = "boiler_tracking"
MODE_BILL_ENTRY = "bill_entry"

# Conversion factors (to/from canonical m³)
# 1 CCF = 100 cubic feet = 2.83168 cubic meters
CCF_TO_M3 = 2.83168
M3_TO_CCF = 1 / CCF_TO_M3
# 1 cubic foot = 0.0283168 cubic meters
CF_TO_M3 = 0.0283168
M3_TO_CF = 1 / CF_TO_M3
# 1 therm ≈ 100 cubic feet of natural gas (approximate)
THERM_TO_M3 = 2.83168
M3_TO_THERM = 1 / THERM_TO_M3

# Default values
DEFAULT_BOILER_AV_H = 0.64153071524727  # m³ per hour
DEFAULT_BOILER_AV_M = DEFAULT_BOILER_AV_H / 60  # m³ per minute
DEFAULT_LATEST_GAS_DATA = 0
DEFAULT_BOILER_ENTITY = None  # No default - user must select
DEFAULT_UNIT_SYSTEM = UNIT_SYSTEM_METRIC
DEFAULT_OPERATING_MODE = MODE_BOILER_TRACKING
