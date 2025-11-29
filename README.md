# Virtual Gas Meter for Home Assistant

## Overview

The **Virtual Gas Meter** is a Home Assistant integration designed to track gas consumption. It supports two operating modes:

1. **Boiler/Furnace Tracking Mode**: Estimates gas consumption based on boiler runtime and average gas usage rate. Users can periodically enter real meter readings to improve accuracy.

2. **Monthly Bill Entry Mode**: Simple tracking by entering gas meter readings from your utility bills. Ideal for users who want to track usage without a smart boiler sensor.

The integration supports both **metric (m³)** and **imperial (CCF)** unit systems.

## Features

- **Dual Operating Modes**: Choose between boiler tracking or simple bill entry
- **Unit System Support**: Works with metric (m³) or imperial (CCF) units
- **Virtual Gas Meter Calculation**: Estimates gas consumption using time-based calculations (boiler mode)
- **Sensor Integration**: Creates Home Assistant sensors to track gas usage
- **Manual Data Entry**: Enter real gas meter readings from utility bills
- **Historical Data Tracking**: Stores consumption history with cumulative totals
- **JSON-based Storage**: Uses Home Assistant's native storage system
- **UI-based Configuration**: Easy setup through Home Assistant's integration flow

## Installation

### Install via HACS (Recommended)
1. **Ensure HACS is installed** in your Home Assistant instance.
2. **Add the Custom Repository:**
   - Open HACS in Home Assistant.
   - Navigate to `Integrations` and click the three-dot menu.
   - Select `Custom Repositories`.
   - Add the repository URL: `https://github.com/lukepatrick/virtual_gas_meter`.
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
1. Navigate to **Settings** > **Devices & Services**.
2. Click **"Add Integration"** and search for `Virtual Gas Meter`.
3. **Step 1 - Basic Setup:**
   - Select your **Unit System**: Metric (m³) or Imperial (CCF)
   - Select your **Operating Mode**: Boiler/Furnace Tracking or Monthly Bill Entry
4. **Step 2 - Mode-specific Setup:**
   - **Boiler Tracking**: Select your boiler switch entity, enter average gas consumption per hour, and optionally enter current meter reading
   - **Bill Entry**: Optionally enter your current meter reading
5. Click **"Submit"**.

### Sensors Created

#### Both Modes
- **Gas Consumption Data**: Displays your gas readings and tracks cumulative usage (text-based)
- **Gas Meter Total**: Numeric meter reading for Energy Dashboard integration

#### Boiler Tracking Mode (additional sensors)
- **Consumed Gas**: Real-time estimated gas consumption based on boiler runtime
- **Gas Meter Latest Update**: Timestamp of last meter reading
- **Heating Interval**: Tracks boiler "on" time since last update

### Energy Dashboard Integration

The **Gas Meter Total** sensor (`sensor.gas_meter_total`) is designed to work with Home Assistant's [Energy Dashboard](https://www.home-assistant.io/docs/energy/). It provides:
- `device_class: gas`
- `state_class: total_increasing`
- Numeric meter reading in your configured unit (m³ or CCF)

**To add to Energy Dashboard:**
1. Go to **Settings → Dashboards → Energy**
2. Click **Add Gas Source**
3. Select `sensor.gas_meter_total`
4. Configure your gas cost if desired

## Services

### `gas_meter.enter_bill_reading`
**For Bill Entry Mode** - Enter a gas meter reading from your utility bill.

- **Fields:**
  - `billing_date`: The billing date or meter reading date
  - `meter_reading`: The meter reading value in your configured unit (m³ or CCF)

- **Service Call Example:**
  ```yaml
  service: gas_meter.enter_bill_reading
  data:
    billing_date: "2025-11-01"
    meter_reading: 1234.56
  ```

### `gas_meter.trigger_gas_update`
**For Boiler Tracking Mode** - Update the virtual gas meter with a real meter reading to improve accuracy.

- **Why use this?**
  - The virtual gas meter **estimates** gas consumption using the average rate
  - By entering real readings, the system **adjusts** the average gas consumption for better accuracy
  - If no real readings are provided, the virtual gas meter relies on the initial average entered during setup

- **Fields:**
  - `datetime`: Timestamp for the gas reading (format: `YYYY-MM-DD HH:MM`)
  - `consumed_gas`: Gas meter reading in your configured unit (m³ or CCF)

- **Service Call Example:**
  ```yaml
  service: gas_meter.trigger_gas_update
  data:
    datetime: "2025-02-12 15:51"
    consumed_gas: 4447.816
  ```

### `gas_meter.read_gas_actualdata_file`
Reads and refreshes the stored gas meter data.

- **Service Call Example:**
  ```yaml
  service: gas_meter.read_gas_actualdata_file
  ```

## Data Storage

Gas consumption data is stored in Home Assistant's `.storage` directory as `gas_meter_data` (JSON format). Data is always stored internally in cubic meters (m³) for consistency, and converted to your display unit automatically.

## Code Overview

The integration consists of the following files:

| File | Description |
|------|-------------|
| `__init__.py` | Integration setup, service registration, and data persistence |
| `sensor.py` | Sensor entities for gas tracking |
| `config_flow.py` | UI-based configuration flow |
| `unit_converter.py` | Unit conversion utilities (m³ ↔ CCF) |
| `datetime_handler.py` | Date/time parsing and conversion |
| `file_handler.py` | JSON-based storage using Home Assistant Store |
| `gas_consume.py` | Gas consumption record management |
| `const.py` | Constants and default values |
| `manifest.json` | Integration metadata |
| `services.yaml` | Service definitions |
| `translations/en.json` | UI translations |

## Dashboard Examples

### Bill Entry Mode

#### Option 1: Built-in HA Cards with Input Helpers

This approach uses standard Home Assistant cards and input helpers for a user-friendly bill entry experience.

**Step 1: Create Input Helpers**

Add to `configuration.yaml`:
```yaml
input_datetime:
  gas_billing_date:
    name: Billing Date
    has_date: true
    has_time: false
    icon: mdi:calendar

input_number:
  gas_meter_reading:
    name: Meter Reading
    min: 0
    max: 100000
    step: 0.01
    mode: box
    icon: mdi:meter-gas
    unit_of_measurement: "CCF"  # Change to "m³" for metric

input_button:
  submit_gas_reading:
    name: Submit Reading
    icon: mdi:send
```

**Step 2: Create Automation**

Add to `automations.yaml`:
```yaml
- id: gas_meter_bill_entry
  alias: "Gas Meter - Submit Bill Reading"
  trigger:
    - platform: state
      entity_id: input_button.submit_gas_reading
  condition:
    - condition: numeric_state
      entity_id: input_number.gas_meter_reading
      above: 0
  action:
    - service: gas_meter.enter_bill_reading
      data:
        billing_date: "{{ states('input_datetime.gas_billing_date') }}"
        meter_reading: "{{ states('input_number.gas_meter_reading') | float }}"
    - service: persistent_notification.create
      data:
        title: "Gas Meter Updated"
        message: "Reading of {{ states('input_number.gas_meter_reading') }} submitted for {{ states('input_datetime.gas_billing_date') }}"
```

**Step 3: Dashboard Card**

```yaml
type: vertical-stack
title: Gas Meter
cards:
  # Current Status
  - type: entities
    entities:
      - entity: sensor.gas_consumption_data
        name: Latest Reading

  # Usage Statistics
  - type: markdown
    title: Monthly Usage
    content: >
      {% set records = state_attr('sensor.gas_consumption_data', 'records') %}
      {% if records and records | length > 1 %}
        {% set latest = records[-1] %}
        {% set previous = records[-2] %}
        {% set usage = (latest.consumed_gas | replace(' CCF', '') | replace(' m³', '') | float) - (previous.consumed_gas | replace(' CCF', '') | replace(' m³', '') | float) %}
        **Last Period Usage:** {{ "%.2f" | format(usage) }} {{ latest.consumed_gas.split(' ')[-1] }}

        **Current Reading:** {{ latest.consumed_gas }}

        **Previous Reading:** {{ previous.consumed_gas }}
      {% elif records and records | length == 1 %}
        **Current Reading:** {{ records[0].consumed_gas }}

        _Enter another reading to see usage._
      {% else %}
        _No readings yet._
      {% endif %}

  # Bill Entry Form
  - type: entities
    title: Enter New Reading
    entities:
      - entity: input_datetime.gas_billing_date
      - entity: input_number.gas_meter_reading
  - type: button
    name: Submit Reading
    entity: input_button.submit_gas_reading
    tap_action:
      action: toggle
    icon: mdi:send
    icon_height: 40px

  # Reading History
  - type: markdown
    title: Reading History
    content: >
      {% set readings = state_attr('sensor.gas_consumption_data', 'records') %}
      {% if readings %}
        | Date | Reading | Cumulative |
        |------|---------|------------|
        {% for record in readings | reverse %}
        | {{ record.datetime[:10] }} | {{ record.consumed_gas }} | {{ record.consumed_gas_cumulated or 'N/A' }} |
        {% endfor %}
      {% else %}
        No readings recorded yet.
      {% endif %}
```

#### Option 2: Enhanced Dashboard with HACS Custom Cards

For a more polished look, install these HACS frontend integrations:
- [Mushroom Cards](https://github.com/piitaya/lovelace-mushroom)
- [ApexCharts Card](https://github.com/RomRider/apexcharts-card)
- [Mini Graph Card](https://github.com/kalkih/mini-graph-card)

**Dashboard with Custom Cards:**

```yaml
type: vertical-stack
cards:
  # Header with current reading
  - type: custom:mushroom-template-card
    primary: Gas Meter
    secondary: >
      {% set records = state_attr('sensor.gas_consumption_data', 'records') %}
      {{ records[-1].consumed_gas if records else 'No data' }}
    icon: mdi:meter-gas
    icon_color: orange
    card_mod:
      style: |
        ha-card {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          --primary-text-color: white;
          --secondary-text-color: rgba(255,255,255,0.8);
        }

  # Usage comparison (markdown card since sensor is non-numeric)
  - type: markdown
    title: Last Period Usage
    content: >
      {% set records = state_attr('sensor.gas_consumption_data', 'records') %}
      {% if records and records | length > 1 %}
        {% set latest = records[-1].consumed_gas | replace(' CCF', '') | replace(' m³', '') | float %}
        {% set previous = records[-2].consumed_gas | replace(' CCF', '') | replace(' m³', '') | float %}
        {% set usage = (latest - previous) | round(1) %}
        {% set unit = records[-1].consumed_gas.split(' ')[-1] %}
        <h1 style="text-align:center; color: {{ 'green' if usage < 100 else 'orange' if usage < 150 else 'red' }}">{{ usage }} {{ unit }}</h1>
      {% else %}
        <p style="text-align:center">Need 2+ readings</p>
      {% endif %}

  # Bill entry with mushroom chips
  - type: horizontal-stack
    cards:
      - type: custom:mushroom-entity-card
        entity: input_datetime.gas_billing_date
        icon_color: blue
      - type: custom:mushroom-number-card
        entity: input_number.gas_meter_reading
        icon_color: orange

  - type: custom:mushroom-template-card
    primary: Submit Reading
    icon: mdi:send-circle
    icon_color: green
    tap_action:
      action: call-service
      service: input_button.press
      target:
        entity_id: input_button.submit_gas_reading

  # Usage trend chart (requires ApexCharts)
  - type: custom:apexcharts-card
    header:
      show: true
      title: Usage Trend
    graph_span: 12month
    series:
      - entity: sensor.gas_consumption_data
        data_generator: |
          const records = entity.attributes.records || [];
          const data = [];
          for (let i = 1; i < records.length; i++) {
            const curr = parseFloat(records[i].consumed_gas.replace(/[^\d.-]/g, ''));
            const prev = parseFloat(records[i-1].consumed_gas.replace(/[^\d.-]/g, ''));
            const date = new Date(records[i].datetime);
            data.push([date.getTime(), (curr - prev).toFixed(2)]);
          }
          return data;
        name: Monthly Usage
```

### Boiler Tracking Mode

#### Virtual Gas Meter Data Section
```yaml
type: vertical-stack
title: Virtual Gas Meter
cards:
  - type: entities
    entities:
      - entity: sensor.consumed_gas
        name: Current Consumption
      - entity: sensor.gas_meter_latest_update
        name: Last Update
      - entity: sensor.heating_interval
        name: Heating Time
  - type: history-graph
    entities:
      - entity: sensor.consumed_gas
    hours_to_show: 168
    title: Weekly Consumption
```

#### Enter Meter Reading Section

**Input Helpers** (add to `configuration.yaml`):
```yaml
input_datetime:
  gas_update_datetime:
    name: Reading Date/Time
    has_date: true
    has_time: true
    icon: mdi:calendar-clock

input_number:
  consumed_gas:
    name: Meter Reading
    min: 0
    max: 100000
    step: 0.001
    mode: box
    icon: mdi:meter-gas

input_button:
  trigger_gas_update:
    name: Submit Reading
    icon: mdi:send
```

**Automation** (add to `automations.yaml`):
```yaml
- id: gas_meter_correction
  alias: "Gas Meter - Submit Correction"
  trigger:
    - platform: state
      entity_id: input_button.trigger_gas_update
  condition:
    - condition: numeric_state
      entity_id: input_number.consumed_gas
      above: 0
  action:
    - service: gas_meter.trigger_gas_update
      data:
        datetime: "{{ states('input_datetime.gas_update_datetime') }}"
        consumed_gas: "{{ states('input_number.consumed_gas') | float }}"
    - service: persistent_notification.create
      data:
        title: "Gas Meter Corrected"
        message: "Reading updated to {{ states('input_number.consumed_gas') }}"
```

**Dashboard Card:**
```yaml
type: vertical-stack
title: Enter Meter Reading
cards:
  - type: entities
    entities:
      - entity: input_datetime.gas_update_datetime
      - entity: input_number.consumed_gas
  - type: button
    name: Submit Reading
    entity: input_button.trigger_gas_update
    tap_action:
      action: toggle
    icon: mdi:send
```

## Usage

### Bill Entry Mode
1. Configure the integration with "Monthly Bill Entry" mode
2. When you receive your utility bill, use **Developer Tools → Services → gas_meter.enter_bill_reading**
3. Enter the billing date and meter reading
4. View your consumption history in the Gas Consumption Data sensor

### Boiler Tracking Mode
1. Configure the integration with "Boiler/Furnace Tracking" mode
2. Select your boiler switch entity
3. Monitor real-time estimated consumption via the "Consumed Gas" sensor
4. Periodically enter real meter readings to improve accuracy

## Upgrading from v1.x

Version 2.0 introduces several changes:
- **Data Migration**: Existing pickle-based storage is automatically migrated to JSON
- **New Config Flow**: You may need to reconfigure the integration to access new features
- **Unit Selection**: Imperial (CCF) units are now supported

## Support & Issues

For any issues or feature requests, please visit the [GitHub Issue Tracker](https://github.com/lukepatrick/virtual_gas_meter/issues).

## Credits

This project is a fork of the original [Virtual Gas Meter](https://github.com/Elbereth7/virtual_gas_meter) by [@Elbereth7](https://github.com/Elbereth7).

## Contributing

Contributions are welcome! Feel free to submit pull requests or report issues in the GitHub repository.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
