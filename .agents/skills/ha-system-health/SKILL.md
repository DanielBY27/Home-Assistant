---
name: ha-system-health
description: Deep health check for Home Assistant. Detects orphaned entities in automations/scripts/blueprints, broken dashboard cards, dead entities in the entity registry, deprecated YAML configurations, unused custom sensors, and SQLite database bloaters while maintaining EMHASS 60-day recorder retention and Git-to-HA purge automation synchronization.
---

# Home Assistant Health & Ghost Entity Inspector

This skill performs a comprehensive, non-destructive audit of Home Assistant runtime states, system logs, configuration files, Lovelace dashboards, and the SQLite recorder database (`home-assistant_v2.db`) to identify dead references, broken automations, template errors, unused custom sensors, and database bloaters.

---

## Architecture & Integration Context

- **MCP Server (`ha_mcp`):** Provides direct access to live core health diagnostics (`ha_get_system_health`), active/dismissed repairs, live system error logs (`ha_get_logs`), helpers (`ha_config_list_helpers`), entity removal (`ha_remove_entity`), and automation management (`ha_config_get_automation` / `ha_config_set_automation`).
- **SSH Access (`ssh homeassistant`):** Access to HA OS filesystem (`/homeassistant`, symlinked as `/config`) and Python 3 runtime for deep static analysis of YAML configs, `.storage` JSON registries, and read-only inspection of `home-assistant_v2.db`.
- **Purge Automation & EMHASS Retention:**
  - Local Git file: `examples/automation/ha_database_purge.yaml`
  - Live HA entity: `automation.ha_datenbank_purge`
  - EMHASS ML Forecaster requirement: Requires recorder history `purge_keep_days >= 60` for key sensors (`sensor.scb_solar_power` and `sensor.emhass_config_home_power_no_var_loads`). All other high-frequency entities are purged aggressively (keep_days: 3 or 10) to keep the database size compact.
- **Helper Script:** `tools/run_system_health.ps1` executes `tools/ha_system_health.py` directly on Home Assistant via SSH, passing the local purge automation Base64-encoded to guarantee synchronization.

---

## 5-Step Health Audit Procedure

### Step 1: Query Live Health, Repairs & Dead Entities (via `ha_mcp`)
Run `ha_get_system_health` with parameters:
```json
// Tool: ha_get_system_health
{
  "include": "repairs,config_check,dead_entities"
}
```
- **Config Check:** Confirms if the active configuration is valid.
- **Repairs:** Checks for open issues or warnings flagged by Home Assistant.
- **Dead Entities:** Identifies `stale_restored` entities (restored from previous boots that integrations no longer claim) and `config_entry_orphans`.

### Step 2: Query Structured System Logs (via `ha_mcp`)
Check for runtime warnings and failed trigger initializations:
```json
// Tool: ha_get_logs
{
  "source": "system"
}
```
Optionally inspect component errors:
```json
// Tool: ha_get_logs
{
  "source": "error_log",
  "structured": true
}
```
- Pinpoints triggers referencing unknown entities (e.g. at boot).
- Detects integrations taking >10s to set up.
- Highlights deprecated YAML platform warnings.

### Step 3: Deep Configuration & Dashboard Scan (via SSH)
Execute the automated analysis script:
```powershell
powershell -ExecutionPolicy Bypass -File tools/run_system_health.ps1
```
This script audits `/homeassistant`:
1. **Automations & Scripts (`automations.yaml`, `scripts.yaml`):** Cross-checks all referenced entities in triggers, conditions, actions, and templates against active registry and restore states.
2. **Lovelace Dashboards (`.storage/lovelace.*`):** Flags cards or views targeting non-existent or deleted entities.
3. **Person Device Trackers (`.storage/person`):** Identifies persons assigned to deleted or disabled trackers.
4. **Unused Custom Sensors (`custom_template.yaml`, `modbus.yaml`):** Identifies custom defined sensors that are never referenced across any automation, script, or dashboard card.
5. **Template & Syntax Verification:** Catches unquoted keywords (e.g. `float(unavailable)`) or deprecated configurations (e.g. platform sensor definitions).

### Step 4: Database Bloat & Purge Automation Audit
The script automatically connects in read-only mode (`?mode=ro`) to `/homeassistant/home-assistant_v2.db`:
1. **Top State Contributors:** Queries the top state-generating entities (`states` joined with `states_meta`).
2. **EMHASS Protection Whitelist:** Asserts that EMHASS mlforecaster sensors (`sensor.scb_solar_power`, `sensor.emhass_config_home_power_no_var_loads`) are marked as `protected_emhass` and NOT purged early.
3. **Uncovered Bloat Detection:** Checks whether high-volume entities are matched by `domains`, `entity_id`, or `entity_globs` in the purge automation. Unmatched high-volume entities are flagged with actionable glob/domain recommendations.
4. **Git vs. Live HA Automation Sync:** Compares the local `examples/automation/ha_database_purge.yaml` with the live `automation.ha_datenbank_purge` in `automations.yaml` to ensure they are 100% in sync (`"status": "in_sync"`).

### Step 5: Generate Diagnostic Summary Report
Present findings cleanly categorized:

1. 🚨 **Broken Automations & Dashboards:** Automations or dashboard cards pointing to non-existent or missing entities.
2. 👻 **Ghost / Dead Registry Entities:** `stale_restored` entries that can be safely removed via `ha_remove_entity`.
3. 🧹 **Unused Custom Sensors:** Custom sensors or helpers with 0 active references.
4. ⚠️ **Configuration Warnings & Deprecations:** Deprecated YAML structures or template issues.
5. 💾 **Database Bloat & Purge Sync:**
   - Git vs. Live synchronization status (`in_sync` or diffs).
   - High-volume state generators not yet covered by purge rules.
   - Confirmation of protected EMHASS long-term sensors.
6. 🛠️ **Recommended Actions:** Clear, actionable step-by-step remediation without making destructive deletions automatically.
