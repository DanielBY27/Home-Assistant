# Module: Blueprints & Core Automations

This module contains the reusable Home Assistant Blueprint templates that define the automation logic for energy management (EMHASS) and room climate control.

## Module Overview

The Blueprints are divided into two main categories:
1. **EMHASS Energy Optimization Suite**: Dynamically schedules energy-intensive home appliances (deferrable loads) based on solar forecasts and grid tariff costs.
2. **Room Control**: Automates shutters and heating/cooling based on window states, presence, and solar position.

---

## File Structure & Dependencies

All files in this module are located in [blueprints/automation/](./).

### Core Blueprints
* **[emhass_basic.yaml](./emhass_basic.yaml)**:
  - The central manager ("brain") that communicates with the EMHASS add-on.
  - *Dependencies*: Requires a REST command in your Home Assistant configuration (see [Step 1 of Setup](../../README.md#step-1-configure-home-assistant-rest-command)).
  - *Examples*: Instantiated config at [emhass_basic_blueprint.yaml](../../examples/blueprints/emhass_basic_blueprint.yaml).
* **[emhass_basic_trigger.yaml](./emhass_basic_trigger.yaml)**:
  - The satellite controller for a generic deferrable load (e.g. dishwasher).
  - *Dependencies*: Requires one `input_text` JSON helper and one `input_select` status helper per device.
  - *Examples*:
    - [emhass_basic_trigger_dishwasher.yaml](../../examples/blueprints/emhass_basic_trigger_dishwasher.yaml)
    - [emhass_basic_trigger_washing_machine.yaml](../../examples/blueprints/emhass_basic_trigger_washing_machine.yaml)
    - [emhass_basic_trigger_tumble_dryer.yaml](../../examples/blueprints/emhass_basic_trigger_tumble_dryer.yaml)
    - [emhass_basic_trigger_water_boiler.yaml](../../examples/blueprints/emhass_basic_trigger_water_boiler.yaml)
    - [emhass_basic_trigger_pv_battery.yaml](../../examples/blueprints/emhass_basic_trigger_pv_battery.yaml)
* **[emhass_basic_trigger_go_echarger.yaml](./emhass_basic_trigger_go_echarger.yaml)**:
  - Custom deferrable load controller specifically built for the **go-e Wallbox**.
  - *Dependencies*: Leverages `go-e APIv2 Connect` entities for current adjustment.
  - *Examples*: Instantiated config at [emhass_basic_trigger_go_echarger_blueprint.yaml](../../examples/blueprints/emhass_basic_trigger_go_echarger_blueprint.yaml).
* **[emhass_modbus_writer.yaml](./emhass_modbus_writer.yaml)**:
  - Writes data values to Modbus TCP registers (e.g. Kostal Plenticore minimum SOC control).
  - *Examples*: Instantiated config at [emhass_modbuss_writer_pv_battery.yaml](../../examples/blueprints/emhass_modbuss_writer_pv_battery.yaml).
* **[room_control.yaml](./room_control.yaml)**:
  - Thermostat and shutter controller mapping rooms to presence sensors and window state.
  - *Examples*:
    - Parents: [room_control_parents.yaml](../../examples/blueprints/room_control_parents.yaml)
    - Kitchen: [room_control_kitchen.yaml](../../examples/blueprints/room_control_kitchen.yaml)
    - Kids rooms: [Simon](../../examples/blueprints/room_control_simon.yaml), [Stefan](../../examples/blueprints/room_control_stefan.yaml), [Lukas](../../examples/blueprints/room_control_lukas.yaml)

---

## Configuration & Specific Rules

### 1. The State Machine (`emhass_basic_trigger.yaml`)
Each load controller enforces state transitions using the `input_select` entity:
* **`done`**: Device is off and idle. The scheduler parameters are reset to 0 in EMHASS v0.17 payload to prevent phantom power scheduling.
* **`wait`**: Arming phase. Active power is requested from EMHASS.
* **`running`**: Started by EMHASS when optimization schedule assigns power (`sensor.p_deferrableX > 0`).
* **`force`**: Manual override to start the device immediately.

### 2. Jinja2 State Caching (The Snapshot Pattern)
To ensure atomic evaluations during the automation trigger phase, the blueprints declare a complex read-only local variable named `snapshot` in JSON format. All subsequent actions must read from this JSON rather than querying live states:
```yaml
snapshot: >
  {% set status_json = states(input_emhass_sensor | string) | from_json(default={}) %}
  ...
```

---

## Maintenance & Expansion

### Adding a New Deferrable Load
1. Create a helper pair: `input_text.[device_name]_emhass_json` and `input_select.[device_name]_emhass_status`.
2. Instantiate the blueprint: Create a new automation referencing `emhass_basic_trigger.yaml` (follow the dishwasher configuration as a template).
3. Link to the brain: Open the `emhass_basic` automation and add the new `input_text` JSON helper to the `list_emhass_deferrable_loads` parameter.

### Modifying Room Controls
Ensure that any new room configuration added to `examples/blueprints/` maps to a physical climate thermostat, presence sensor, and window sensor using the matching room control blueprint properties.
