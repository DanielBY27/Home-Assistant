---
name: emhass-develop
description: Architectural and development guide for EMHASS energy management in Home Assistant, covering optimization modes, deferrable load scheduling, go-eCharger surplus vs grid charging logic, Kostal min SoC control, and battery automation synchronization.
---

# EMHASS Development & Architecture Guide

This skill documents the complete EMHASS setup, blueprint architectures, deferrable load state machines, go-eCharger EV charging logic, and battery optimization controllers in Home Assistant.

---

## 1. EMHASS Core Architecture & Optimization Config

- **Add-on Service:** Docker container managed by Supervisor (`slug: 5b918bf2_emhass`, REST port 5000).
- **Optimization Strategy:**
  - `costfun`: Set to `cost` (minimizes total monetary cost).
  - Feed-in Tariff (`production_price`): `0.082` €/kWh (fixed German EEG feed-in remuneration).
  - Dynamic Import Tariff: Tibber electricity price (`sensor.tibber_electricity_price`).
  - Solcast Solar Forecast: Real-time 48h irradiance forecast passed to EMHASS via `sensor.solcast_pv_forecast_prognose_aktuelle_stunde` and future timesteps.

---

## 2. Blueprint System & JSON Protocol

The system utilizes three core blueprints to decouple scheduling from physical hardware:

```mermaid
flowchart TD
    A[Appliance Trigger / EV Plugged] --> B["input_select.[device]_emhass_status: wait"]
    B --> C["input_text.[device]_emhass_json: needs_optim = true"]
    C --> D["emhass_basic.yaml (Master Controller)"]
    D -->|REST POST /action/dayahead-optim| E[EMHASS Add-on]
    E -->|Optimized Power Schedule| F["sensor.p_deferrable0..N"]
    F -->|Power > 0 on start timestep| G["input_select.[device]_emhass_status: running"]
    G --> H[Physical Device / Wallbox Starts]
    H -->|Cycle Complete / Stop Sensor| I["input_select.[device]_emhass_status: done"]
```

### JSON Helper Payload Schema (`input_text.[device]_emhass_json`)
```json
{
  "po": 11000,    // Nominal power in Watts (W)
  "ho": 2.5,      // Operating hours required (h)
  "st": 0,        // Earliest start timestep index (0 = now)
  "et": 96,       // Latest finish timestep index (96 = 24h at 15m steps)
  "se": false,    // Semi-continuous load (bool)
  "si": true,     // Single constant power block (bool)
  "mp": 4200,     // Minimum power in Watts (W)
  "pe": 2,        // Startup penalty score
  "us": "wait",   // Automation status (done, wait, running, force)
  "ss": 0         // Actual planned start timestamp (0 = no plan yet)
}
```

---

## 3. go-eCharger Wallbox: PV Surplus vs. EMHASS Grid Scheduling

The go-eCharger controller (`examples/blueprints/emhass_basic_trigger_go_echarger_blueprint.yaml` / `automation.emhass_deferrable_load_controller_for_go_echarger`) dynamically determines whether to use pure PV surplus charging or EMHASS cost-optimized grid charging:

### Logic Distinction by Season (`goe_pv_surplus_enabled`):
- **Summer (May to September):**
  - When sun is above horizon (`sun.sun == 'above_horizon'`), surplus charging is enabled (`true`).
  - Sets go-eCharger to Mode 4 (eco/surplus), charging dynamically with available solar power.
- **Transition & Winter (October to April):**
  - Surplus charging is enabled **only** if the remaining Solcast daily forecast covers the entire EV charge demand:
    ```jinja2
    {% set is_day = is_state('sun.sun', 'above_horizon') %}
    {% set current_month = now().month %}
    {% if not is_day %}
      {{ false }}
    {% elif current_month in [5, 6, 7, 8, 9] %}
      {{ true }}
    {% else %}
      {% set remaining_pv_kwh = states('sensor.solcast_pv_forecast_prognose_verbleibende_leistung_heute') | float(0.0) %}
      {% set needed_kwh = (states('sensor.emhass_go_echarger_trigger') | float(0.0)) / 1000.0 %}
      {{ needed_kwh > 0 and remaining_pv_kwh >= needed_kwh }}
    {% endif %}
    ```
  - **Deficit Situation (e.g. 40.5 kWh needed vs 14.5 kWh forecast):**
    Surplus mode evaluates to `false`. Status stays `wait`. EMHASS optimizes charging during cheap night hours via `p_deferrable4`.

### Key Wallbox Sensors:
- `binary_sensor.goe_297534_car_0`: Car connected to wallbox (`on` / `off`).
- `sensor.vr3ezzkxzpj688123_batterie`: EV battery SoC (%).
- `sensor.emhass_go_echarger_trigger`: Calculated gross energy needed in Wh (95% target SoC, 92.5% charging efficiency).

---

## 4. Battery Storage & SoC Management

### Kostal Plenticore Sensor Quirk: Real PV vs. Total Inverter DC Power
- **Hardware Quirk:** On Kostal Plenticore inverters with a high-voltage battery connected to DC3, `sensor.scb_solar_power` reports total inverter DC power:
  $$\text{Power} = \text{DC1} + \text{DC2} + \text{Battery Discharge (DC3)}$$
- **Critical Rule:** Never use `sensor.scb_solar_power` to determine available solar generation during battery discharge. It causes a runaway positive feedback loop where battery discharge into the car is misidentified as solar surplus.
- **Actual Solar Generation Calculation:**
  ```jinja2
  {{ (states('sensor.scb_dc1_power') | float(0.0)) + (states('sensor.scb_dc2_power') | float(0.0)) }}
  ```

### Kostal Min SoC Controller (`examples/automation/kostal_min_soc_controller.yaml`)
Dynamically controls `number.scb_battery_min_soc` and coordinates with EMHASS and Wallbox modes:
- **Case 1: Battery Grid Charging (`input_select.pv_battery_emhass_status` in `running`, `force`)**:
  - Sets `scb_battery_min_soc` to `emhass_calc_soc` (rounded up to 5% increments from `sensor.soc_batt_forecast`).
- **Case 2: EV Charging at Wallbox (`input_select.wallbox_emhass_status` active)**:
  - **Subcase 2a: PV Surplus Mode (`select.goe_297534_lmo == '4'`)**:
    - If real PV ($DC1+DC2 \ge 1500\text{ W}$) **and** Solcast remaining forecast $\ge 3.0\text{ kWh}$: Allows battery buffering down to 10% (`wallbox_allowed_min_soc`).
    - Otherwise (cloudy/evening): Protects home battery by locking `scb_battery_min_soc` to `current_soc`.
  - **Subcase 2b: EMHASS Scheduled Charging / Grid Mode (`select.goe_297534_lmo != '4'`)**:
    - Aligns directly with EMHASS's global cost-optimal schedule.
    - Sets `scb_battery_min_soc` to `emhass_calc_soc` (`sensor.soc_batt_forecast`). Kostal will cover any minor planned battery assistance, but will never drain the battery below the forecast level, reserving home battery capacity for expensive peak hours.
- **Default (Idle)**:
  - When neither grid charging nor Wallbox is active, resets `scb_battery_min_soc` to 10% and ensures `select.battery_charging_usage_mode` is `None`.

### EMHASS PV Battery Status Controller (`examples/automation/emhass_pv_battery_status_controller.yaml`)
- Interprets EMHASS `sensor.p_batt_forecast` to manage home battery charging and discharging.
- **Strict Grid Charging Safety Condition:**
  Grid charging is strictly restricted to prevent false triggers during daytime PV surplus:
  ```jinja2
  {{ (p_batt < -500) and (p_grid > (p_load + 500)) }}
  ```
  Only when EMHASS plans active battery charging from grid during cheap tariff windows does the controller switch the battery into grid-charge mode.
