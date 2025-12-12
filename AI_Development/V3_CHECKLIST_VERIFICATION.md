# Virtual Gas Meter v3 - Specification Checklist

This document verifies that all requirements from v3.md have been implemented.

## Core Integration ✅

- [x] Build integration fresh inside `custom_components/gas_meter`
- [x] Do not reuse old code (reference only)
- [x] Enforce single instance

## Unit System ✅

- [x] Implement selectable units (`m3` / `CCF`)
- [x] Ensure all inputs/outputs use chosen unit
- [x] Enforce 3 decimal places
- [x] Block unit changes after creation
- [x] README updated

## Sensor Implementation ✅

- [x] Implement `sensor.vgm_gas_meter_total`
  - [x] Device class: gas
  - [x] State class: total_increasing
  - [x] Attributes: last_real_meter_reading, last_real_meter_timestamp, average_rate_per_h, boiler_entity_id, unit
- [x] Implement `sensor.vgm_consumed_gas`
  - [x] Resets to 0 on real meter reading update
  - [x] Increases while boiler is running
- [x] Implement `sensor.vgm_heating_interval`
  - [x] String format: "Xh Ym"
  - [x] Resets to "0h 0m" on real meter reading update
- [x] Ensure correct units, classes, persistence
- [x] README updated

## Service: real_meter_reading_update ✅

- [x] Implement parameter parsing
  - [x] meter_reading (float, required)
  - [x] timestamp (datetime, optional, defaults to now())
  - [x] recalculate_average_rate (bool, optional, defaults to true)
- [x] Validation (reading < previous → error)
- [x] Recalculation logic
  - [x] Only if runtime_minutes > 0 AND recalculate_average_rate == true
  - [x] Formula: average_rate_per_h = actual_used / runtime_hours
  - [x] No caps, no clamping
- [x] Snap logic (runtime=0)
  - [x] Set last_real_meter_reading = meter_reading
  - [x] Set vgm_gas_meter_total = meter_reading
  - [x] Set vgm_consumed_gas = 0.000
  - [x] Set vgm_heating_interval = "0h 0m"
  - [x] Do not recalc average rate
- [x] Consumption reset
- [x] Persistence updates
- [x] README updated

## Runtime Engine ✅

- [x] Boiler state listener
  - [x] Supports switch, climate, binary_sensor, sensor domains
  - [x] Handles different state representations
- [x] 60-second update loop
  - [x] Increase internal runtime counter by 1 minute
  - [x] Update vgm_heating_interval
  - [x] Add consumed_increment = average_rate_per_h / 60
  - [x] Update vgm_gas_meter_total = last_real_meter_reading + vgm_consumed_gas
- [x] Final update on "off" transition
- [x] No retroactive runtime after restart
- [x] README updated

## Config Flow ✅

- [x] UI setup page
  - [x] Boiler entity selection
  - [x] Unit selection (m3 / CCF)
  - [x] Initial real meter reading
  - [x] Initial average hourly consumption
- [x] Domain filter for allowed entity types
  - [x] switch, climate, binary_sensor, sensor
- [x] Single instance enforcement
  - [x] Abort with "single_instance_allowed"
  - [x] UI message provided
- [x] Options flow
  - [x] Can edit: boiler entity, initial average hourly consumption
  - [x] Cannot edit: unit selection, last real meter reading
- [x] README updated

## Device Setup ✅

- [x] Create device + attach entities
- [x] Device name: "Virtual Gas Meter"
- [x] Manufacturer: "Virtual Gas Meter"
- [x] Model: "Boiler Runtime Estimator"
- [x] README updated

## Persistence ✅

- [x] Use HA Store API
- [x] Persist all required values:
  - [x] last_real_meter_reading
  - [x] last_real_meter_timestamp
  - [x] average_rate_per_h
  - [x] consumed_gas
  - [x] heating_interval (internal counters)
  - [x] unit
  - [x] boiler_entity_id
- [x] Everything survives HA restarts
- [x] README updated

## Logging ✅

- [x] INFO logs for major events
  - [x] Integration loaded
  - [x] Successful real_meter_reading_update event
    - [x] Old reading
    - [x] New reading
    - [x] Runtime minutes
    - [x] New average rate (if recalculated)
- [x] DEBUG logs for ticks
  - [x] Incremental consumption
  - [x] Updated totals
  - [x] Boiler state transitions
- [x] README updated

## Removed Functionality ✅

v3 completely removes:
- [x] Bill Entry Mode
- [x] `gas_meter.enter_bill_usage`
- [x] `gas_meter.read_gas_actualdata_file`
- [x] All old sensors including:
  - [x] `gas_consumption_data`
  - [x] `operating_mode`
  - [x] `unit_system`
  - [x] `boiler_entity`
  - [x] previous heating interval attributes

## README Update ✅

- [x] Remove legacy content
- [x] Add updated documentation for:
  - [x] Config flow
  - [x] Units
  - [x] Sensors (3 total)
  - [x] Service (`real_meter_reading_update`)
  - [x] Expected behaviour & examples
  - [x] Migration guide from v2.x
  - [x] Breaking changes documentation
  - [x] Dashboard examples

## Summary

**Total Requirements: 100+**
**Completed: 100+**
**Status: ✅ FULLY IMPLEMENTED**

All requirements from the v3.md specification have been successfully implemented. The integration is ready for testing.
