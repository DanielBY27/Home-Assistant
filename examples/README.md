# Module: System Configuration Templates & Examples

This directory contains concrete configuration examples, virtual sensors, and helper automations that connect physical devices to our Blueprint logic.

## Folder Contents

* **[examples/blueprints/](./blueprints)**: Instantiations of the YAML blueprints for our active appliances (e.g. Dishwasher, Tumble Dryer, Wallbox, and Room Controls).
* **[examples/sensors/](./sensors)**: Template sensors configured as HA helpers (e.g. battery grid import, EV charger triggers).
* **[examples/automation/](./automation)**: Independent automations, such as the Kostal min SoC controller and Solcast dampening adjustments.

---

## Blueprint Configurations

The files in [examples/blueprints/](./blueprints) instantiate the core templates defined in [blueprints/automation/](../blueprints/automation):

1. **EMHASS Basic**:
   - [emhass_basic_blueprint.yaml](./blueprints/emhass_basic_blueprint.yaml) links directly to [emhass_basic.yaml](../blueprints/automation/emhass_basic.yaml).
2. **Deferrable Loads**:
   - [emhass_basic_trigger_dishwasher.yaml](./blueprints/emhass_basic_trigger_dishwasher.yaml), [washing_machine](./blueprints/emhass_basic_trigger_washing_machine.yaml), [tumble_dryer](./blueprints/emhass_basic_trigger_tumble_dryer.yaml), [water_boiler](./blueprints/emhass_basic_trigger_water_boiler.yaml), and [pv_battery](./blueprints/emhass_basic_trigger_pv_battery.yaml) instantiate [emhass_basic_trigger.yaml](../blueprints/automation/emhass_basic_trigger.yaml).
3. **EV Wallbox**:
   - [emhass_basic_trigger_go_echarger_blueprint.yaml](./blueprints/emhass_basic_trigger_go_echarger_blueprint.yaml) instantiates [emhass_basic_trigger_go_echarger.yaml](../blueprints/automation/emhass_basic_trigger_go_echarger.yaml).
4. **Modbus Write**:
   - [emhass_modbuss_writer_pv_battery.yaml](./blueprints/emhass_modbuss_writer_pv_battery.yaml) instantiates [emhass_modbus_writer.yaml](../blueprints/automation/emhass_modbus_writer.yaml).
5. **Room Control**:
   - Room-specific control files (e.g. [parents](./blueprints/room_control_parents.yaml), [simon](./blueprints/room_control_simon.yaml)) instantiate [room_control.yaml](../blueprints/automation/room_control.yaml).

---

## Virtual Template Sensors (`examples/sensors/`)

To support EMHASS optimization, the system utilizes virtual sensors configured as template helpers:
* **[emhass_battery_grid_import.yaml](./sensors/emhass_battery_grid_import.yaml)**:
  - Dynamically calculates the deficit energy in Watt-hours (Wh) for the next 24 hours based on load forecasts and Solcast PV predictions.
  - Controls grid charging amounts based on seasonal minimum and maximum State of Charge limits.
* **[emhass_go-echarger_trigger.yaml](./sensors/emhass_go-echarger_trigger.yaml)**:
  - Template sensor acting as the trigger indicator for the EV Wallbox.

---

## Maintenance Guidelines

When modifying a device's physical hardware or changing its integration platform:
1. Update its helper sensors in `examples/sensors/` to match the new hardware state/attributes.
2. Update the corresponding blueprint configuration inside `examples/blueprints/` with the new entity IDs.
3. Test changes using the Python testing scripts located in the `tests/` directory.
