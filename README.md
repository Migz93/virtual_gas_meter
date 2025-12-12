# Virtual Gas Meter for Home Assistant
[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]][license]

[![hacs][hacsbadge]][hacs]
[![Maintainer][maintenance-shield]][user_profile]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

## Overview

> **Note:** This integration was built from the ground up using AI (Claude Sonnet 4.5), based on the original code from the repositories listed in the [Credits](#credits) section. As always, exercise caution with AI-generated code.

Virtual Gas Meter is a Home Assistant integration designed to estimate gas consumption based on boiler runtime. It provides a virtual gas meter that tracks consumption in real-time and allows periodic calibration with real meter readings to maintain accuracy.

The integration supports both **metric (m³)** and **imperial (CCF)** unit systems.

**Note:** Imperial (CCF) units are currently untested.

## Features

- **Real-time Gas Consumption Tracking**: Estimates gas usage based on boiler runtime
- **Unit System Support**: Works with metric (m³) or imperial (CCF) units
- **Calibration System**: Enter real meter readings to recalculate and improve accuracy
- **Energy Dashboard Integration**: Primary sensor designed for Home Assistant's Energy Dashboard
- **UI-based Configuration**: Easy setup through Home Assistant's integration flow

## Installation

### Install via HACS (Recommended)
1. **Ensure HACS is installed** in your Home Assistant instance.
2. **Add the Custom Repository:**
   - Open HACS in Home Assistant.
   - Navigate to `Integrations` and click the three-dot menu.
   - Select `Custom Repositories`.
   - Add the repository URL: `https://github.com/Migz93/virtual_gas_meter`.
   - Choose `Integration` as the category and click `Add`.
3. **Download the Integration:**
   - Search for `Virtual Gas Meter` in HACS and download it.
   - Restart Home Assistant to apply changes.

### Manual Installation
1. Download the repository as a ZIP file and extract it.
2. Copy the `custom_components/gas_meter` folder into your Home Assistant `config/custom_components/` directory.
3. Restart Home Assistant.

## Configuration

### Adding the Integration
1. Navigate to **Settings** > **Devices & Services**
2. Click **"Add Integration"** and search for `Virtual Gas Meter`
3. Configure the following settings:
   - **Boiler Entity**: Select the entity that represents your boiler (switch, climate, binary_sensor, or sensor)
   - **Unit System**: Choose Metric (m³) or Imperial (CCF)
   - **Initial Meter Reading**: Enter your current gas meter reading
   - **Initial Average Hourly Consumption**: Enter the estimated average gas consumption per hour when the boiler is running
4. Click **"Submit"**

**Important Notes:**
- Only one instance of Virtual Gas Meter can exist
- Reconfiguration is not currently supported - to change settings, you must delete the integration and set it up again

### Sensors Created

The integration creates **three sensors** under a single device:

#### sensor.vgm_gas_meter_total
**Primary Energy Dashboard Source**
- Displays the total virtual gas meter reading which can be fed into your Home Assistant Energy Dashboard.
- Device class: `gas`
- State class: `total_increasing`
- Unit: m³ or CCF (based on your configuration)
- **Attributes:**
  - `last_real_meter_reading`: Last calibrated meter reading
  - `last_real_meter_timestamp`: When the last calibration occurred
  - `average_rate_per_h`: Current average hourly consumption rate
  - `boiler_entity_id`: The boiler entity being monitored
  - `unit`: Your chosen unit system

#### sensor.vgm_consumed_gas
**Estimated Gas Consumed Since Last Calibration**
- Shows gas consumed since the last real meter reading update
- Resets to 0 when you enter a new real meter reading
- Increases while the boiler is running based on the average rate

#### sensor.vgm_heating_interval
**Boiler Runtime Since Last Calibration**
- Displays boiler runtime in human-readable format (e.g., "2h 37m")
- Resets to "0h 0m" when you enter a new real meter reading
- Tracks cumulative runtime between calibrations

### Energy Dashboard Integration

The **Gas Meter Total** sensor (`sensor.vgm_gas_meter_total`) is designed to work with Home Assistant's [Energy Dashboard](https://www.home-assistant.io/docs/energy/). It provides:
- `device_class: gas`
- `state_class: total_increasing`
- Numeric meter reading in your configured unit (m³ or CCF)

**To add to Energy Dashboard:**
1. Go to **Settings → Dashboards → Energy**
2. Click **Add Gas Source**
3. Select `sensor.vgm_gas_meter_total`
4. Configure your gas cost if desired

## Services

### `gas_meter.real_meter_reading_update`
Update the virtual gas meter with a real meter reading to calibrate and improve accuracy.

**Why use this service?**
- The virtual gas meter **estimates** consumption based on boiler runtime
- By entering real meter readings periodically, the system **recalculates** the average hourly consumption rate
- This keeps the virtual meter accurate over time as usage patterns change

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `meter_reading` | float | Yes | - | Your current real gas meter reading (in your configured unit) |
| `timestamp` | datetime | No | now() | Optional timestamp for the reading |
| `recalculate_average_rate` | boolean | No | true | If true, recalculates the average hourly rate based on actual usage |

**Service Call Examples:**

Basic usage (recalculates average rate):
```yaml
service: gas_meter.real_meter_reading_update
data:
  meter_reading: 4447.816
```

With custom timestamp:
```yaml
service: gas_meter.real_meter_reading_update
data:
  meter_reading: 4447.816
  timestamp: "2025-02-12 15:51:00"
```

Snap meter total without recalculating rate:
```yaml
service: gas_meter.real_meter_reading_update
data:
  meter_reading: 4447.816
  recalculate_average_rate: false
```

**Behavior:**
1. **Validation**: The new reading must be greater than or equal to the previous reading
2. **If runtime is zero**: Simply snaps the meter total to the new reading
3. **If runtime > 0 and recalculate is true**: Calculates actual consumption and updates the average hourly rate
4. **Resets**: Consumed gas and heating interval reset to zero after update

## Usage

### Daily Operation
The integration automatically tracks boiler runtime and estimates gas consumption based on the configured average hourly rate. No manual intervention is required for day-to-day operation.

### Calibration for Accuracy
Periodically enter real meter readings using the `gas_meter.real_meter_reading_update` service to maintain accuracy:

1. Check your physical gas meter reading
2. Call the service with your current meter reading
3. The system automatically recalculates the average hourly consumption rate based on actual usage
4. The virtual meter stays synchronized with your real meter

### Best Practices
- **Calibrate monthly**: Enter real meter readings at least once per month for best accuracy
- **Calibrate after runtime**: Take readings when the boiler has been running for a while (provides more accurate rate calculations)
- **Monitor trends**: Use the Energy Dashboard to track long-term consumption patterns

## Code Overview

The integration consists of the following files:

| File | Description |
|------|-------------|
| `__init__.py` | Integration setup, runtime engine, service registration, and persistence |
| `sensor.py` | Three sensor entities (gas meter total, consumed gas, heating interval) |
| `config_flow.py` | UI-based configuration flow with single-instance enforcement |
| `const.py` | Constants and configuration keys |
| `manifest.json` | Integration metadata |
| `services.yaml` | Service definitions |
| `strings.json` | Base UI strings |
| `translations/en.json` | English translations |

## Upgrading from v1.x or v2.x

**Version 3.0 is a complete rewrite** with breaking changes:

### What's Changed
- **Removed**: Bill Entry Mode (only boiler tracking mode remains)
- **Removed**: Services `enter_bill_usage`, `trigger_gas_update`, `read_gas_actualdata_file`
- **New**: Single service `real_meter_reading_update` with improved calibration logic
- **New**: Simplified sensor set (3 sensors instead of 6+)
- **New**: Single-instance enforcement
- **Changed**: Sensor entity IDs now use `vgm_` prefix

### Migration Steps
1. **Backup your data** - Note your current meter reading and average rate
2. **Remove the old integration** from Settings → Devices & Services
3. **Restart Home Assistant**
4. **Add the new v3 integration** with your backed-up values
5. **Update automations** to use the new service name
6. **Update dashboards** to use new sensor entity IDs
7. **Reconfigure Energy Dashboard** with the new `sensor.vgm_gas_meter_total`

## Support

For issues or feature requests, please visit the [GitHub Issue Tracker](https://github.com/Migz93/virtual_gas_meter/issues).

## Credits

This project is a fork of [Virtual Gas Meter](https://github.com/lukepatrick/virtual_gas_meter) by [@lukepatrick](https://github.com/lukepatrick)

Which in turn is a fork of the original [Virtual Gas Meter](https://github.com/Elbereth7/virtual_gas_meter) by [@Elbereth7](https://github.com/Elbereth7).

## Contributing

Contributions are welcome! Feel free to submit pull requests or report issues in the GitHub repository.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

[buymecoffee]: https://www.buymeacoffee.com/Migz93
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
[commits-shield]: https://img.shields.io/github/commit-activity/y/migz93/virtual_gas_meter.svg?style=for-the-badge
[commits]: https://github.com/migz93/virtual_gas_meter/commits/main
[hacs]: https://hacs.xyz
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[exampleimg]: https://raw.githubusercontent.com/migz93/virtual_gas_meter/main/example.png
[license]: https://github.com/migz93/virtual_gas_meter/blob/main/LICENSE
[license-shield]: https://img.shields.io/github/license/custom-components/integration_blueprint.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Migz93-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/migz93/virtual_gas_meter.svg?style=for-the-badge
[releases]: https://github.com/migz93/virtual_gas_meter/releases
[user_profile]: https://github.com/migz93
