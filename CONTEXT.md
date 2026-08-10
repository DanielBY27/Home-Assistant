# Project Context

This document provides a high-level summary of the entire Home Assistant system, integrated devices, and energy optimization control logic, enabling future development sessions to proceed with the correct context.

## Software Environment

* **Home Assistant Environment** (from latest tablet kiosk configuration):
  - **Core Version**: `2026.5.4` (upgraded from `2026.3.1`)
  - **Supervisor Version**: `2026.05.1`
  - **Operating System (HAOS)**: `17.3`
  - **Frontend Version**: `20260429.4`
* **EMHASS Integration**: `v0.17.0` (Energy Management Optimization for Home Assistant)
  - Configured folder path: `/share`
  - Internal API port: `5000`

---

## Integrated Services & Integrations

The system integrates several physical devices and software platforms:

1. **Energy Management (EMHASS)**:
   - Optimizes grid import/export tariffs, home battery charging, and deferrable loads using forecast algorithms.
2. **Solar and Battery System**:
   - Inverter: **Kostal Plenticore** (integrated via Home Assistant Kostal integration).
   - Battery: **BYD Battery Storage** (18 kWh capacity, charging managed dynamically via Modbus TCP).
   - Forecasts: **Solcast PV Forecast** integration.
3. **Electric Vehicle Charging**:
   - Charger: **go-e Charger 11kW** (Wallbox).
   - Connected via: `go-e APIv2 Connect` HACS integration.
4. **Smart Home Devices**:
   - Deferrable Loads: **Dishwasher**, **Tumble Dryer**, **Washing Machine**, **Water Boiler** (PV surplus heating).
   - Managed via Zigbee smart plugs/switches with active power sensors.
5. **Climate and Shutters**:
   - Room Control manages roller shutters and heating/cooling based on window sensors, occupancy trackers, and solar azimuth/elevation.
6. **Frontend**:
   - Main Kiosk: Running on a **T65 Tablet** in kiosk mode utilizing the `kiosk-mode` HACS extension.
   - Designed to be responsive, scaling to mobile phones and desktop computers.

---

## Core Control Logic

### 1. Centralized EMHASS Flow
The `EMHASS Basic Automation Controller` manages all communication with the EMHASS add-on. Every 5 minutes, it sends current battery state of charge (SoC), PV production forecasts, and individual deferrable load configurations (read from `input_text` JSON helpers) to the EMHASS server. EMHASS returns an optimized plan which sets state flags in Home Assistant sensors (`sensor.p_deferrable0` ... `sensor.p_deferrable5`).

### 2. State-Based Deferrable Load Lifecycle
Each load automation follows a strategy-based state machine:
- **`done` (Idle)**: The machine is finished. Power is typically off.
- **`wait` (Scheduled)**: The load is armed (e.g. by starting it physically or hitting a schedule). The controller signals to EMHASS that it wants power.
- **`running` (Active)**: EMHASS assigns power (`sensor.p_deferrableX > 0`). The controller turns on the physical switch.
- **`force` (Override)**: Manual bypass. Bypasses the optimizer to run the device immediately (with variable charging current overrides like `force-6` to `force-16` amps for the EV charger).

### 3. Inverter Modbus SOC Management
To prevent the battery from discharging into the EV or heating systems when charging from the grid during cheap periods, the `Kostal min SoC Controller` dynamically adjusts the minimum battery State of Charge (`number.scb_battery_min_soc`) using Modbus TCP. It dynamically raises the floor to reserve capacity when active imports occur and resets it to `10%` when done.
