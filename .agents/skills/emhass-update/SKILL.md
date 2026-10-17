---
name: emhass-update
description: Safe, token-efficient, and verified update procedure for the EMHASS add-on in Home Assistant with automated backup, blueprint validation, and trace analysis.
---

# EMHASS Add-on Update

Update procedure for the Home Assistant EMHASS add-on (`5b918bf2_emhass` / `update.emhass_update`). Ensures local blueprint synchronization, automated snapshot backups, notification suppression during upgrade, and trace validation.

## Architecture Context
- **EMHASS Add-on:** Docker container under Supervisor (`slug: 5b918bf2_emhass`, REST port 5000).
- **Controller Blueprint:** `blueprints/automation/emhass_basic.yaml` (`automation.emhass_basic_automation`).
- **Sync Rule:** Live HA blueprints must stay strictly identical to local Git repository blueprints. Always sync via `ha_manage_blueprints` (SSH `admin` user lacks write permissions on `/config/blueprints/`).
- **Docs & Structure:** See [README.md](../../../README.md).

---

## 13-Step Update Procedure

### 1 & 2. Check Update Availability & Early Exit
```json
// Tool: ha_manage_updates
{ "action": "get", "entity_ids": ["update.emhass_update"] }
```
- If `installed_version == latest_version` or entity state is `"off"`, exit cleanly: *"No update available."*

### 3. Architecture & Dependency Review
Check [README.md](../../../README.md) for configured loads, sensor bindings, and active trigger blueprints (`emhass_basic_trigger.yaml`, `emhass_basic_trigger_go_echarger.yaml`).

### 4. Docker Service & Local Tests
Before touching HA, verify the Docker engine and run local unit tests:
```powershell
docker info --format '{{.ServerVersion}}'
powershell -File tests/run_tests.ps1
```
All tests in `tests/test_emhass_basic.py` and `tests/test_multi_load.py` must pass.

### 5 & 6. Verify Versions
Record installed vs target version from `update.emhass_update` or:
```json
// Tool: ha_get_app
{ "slug": "5b918bf2_emhass", "source": "installed" }
```

### 7. Release Notes & Breaking Changes Analysis
Inspect release notes via `ha_manage_updates(action="get", entity_ids=["update.emhass_update"], include_release_notes=True)` or GitHub tags (`davidusb-geek/emhass`).
- **HTTP Status Codes:** EMHASS ≥v0.18 returns `200` instead of `201`. Ensure `blueprints/automation/emhass_basic.yaml` checks `response.status not in [200, 201]`.
- **Parameter Additions:** Verify `DEF_LOAD_ARRAY_PARAMS` in `emhass/utils.py` and `config_defaults.json`. Pad new deferrable load arrays with `([default] * (trigger_objs | length))` in `result_data.save`.
- **Blueprint Sync:** When editing blueprints locally, update HA immediately:
  ```json
  // Tool: ha_manage_blueprints
  {
    "action": "save",
    "domain": "automation",
    "path": "emhass_basic.yaml",
    "overwrite": true,
    "yaml": "<local file content>"
  }
  ```

### 8. Pre-Update HA Test Run
1. Fetch config to ensure `automation_started_manually == "all"`:
   ```json
   // Tool: ha_config_get_automation
   { "identifier": "automation.emhass_basic_automation" }
   ```
2. Trigger the automation:
   ```json
   // Tool: ha_call_service
   { "domain": "automation", "service": "trigger", "entity_id": "automation.emhass_basic_automation" }
   ```
3. Verify trace via `ha_get_automation_traces(automation_id="automation.emhass_basic_automation", limit=1)`. All actions (`Save`, `Forecast`, `Optimization`, `Publish`) must succeed (`execution: finished`).

### 9. Temporarily Disable Failure Notifications
Suppress failure notifications before the update:
1. Obtain current `config_hash` via `ha_config_get_automation(identifier="automation.emhass_basic_automation")`.
2. Disable failure notification:
   ```json
   // Tool: ha_config_set_automation
   {
     "identifier": "automation.emhass_basic_automation",
     "config_hash": "<config_hash>",
     "python_transform": "config['use_blueprint']['input']['enable_optim_failure_notification'] = False",
     "BestPracticeKey": "<key-from-ha_get_skill_guide>",
     "MandatoryBPS": false
   }
   ```
   *(If BestPracticeKey is needed, read `ha_get_skill_guide(file='references/triggers-and-conditions.md')` to obtain the hourly acknowledgment key).*

### 10. Perform EMHASS Update with Backup
1. Install update with mandatory backup:
   ```json
   // Tool: ha_manage_updates
   { "action": "install", "entity_ids": ["update.emhass_update"], "backup": true }
   ```
   *(Note: Service call may time out on client side while HA packages the backup archive. This is expected).*
2. Verify backup existence:
   ```json
   // Tool: ha_manage_backup
   { "scope": "snapshot", "action": "list" }
   ```
   Confirm a snapshot named `EMHASS <old_version>` exists.
3. Poll update status until `in_progress == false` and state is `"off"`:
   ```json
   // Tool: ha_get_state
   { "entity_id": "update.emhass_update" }
   ```
4. Verify add-on running status:
   ```json
   // Tool: ha_get_app
   { "slug": "5b918bf2_emhass", "source": "installed" }
   ```
   Confirm `state: "started"` and `version` matches target.

### 11. Post-Update Test Run & Trace Verification
1. Trigger automation:
   ```json
   // Tool: ha_call_service
   { "domain": "automation", "service": "trigger", "entity_id": "automation.emhass_basic_automation" }
   ```
2. Verify latest run in `ha_get_automation_traces(automation_id="automation.emhass_basic_automation", limit=1)`. Retrieve detailed trace by `run_id` to confirm all REST commands returned `200` (or `201`) and `script_execution == "finished"`.
3. Check add-on logs:
   ```json
   // Tool: ha_get_logs
   { "source": "supervisor", "slug": "5b918bf2_emhass" }
   ```
   Verify solver status is `Optimal` and entities posted successfully.

### 12. Error Diagnostics & Remediation (If Needed)
- View container logs directly: `ssh homeassistant "docker logs addon_5b918bf2_emhass --tail 100"`
- Check stored JSON: `ssh homeassistant "cat /share/config.json"`
- Rollback if critical failure cannot be solved:
  ```json
  // Tool: ha_manage_backup
  { "scope": "snapshot", "action": "restore", "backup_id": "<backup_id>" }
  ```

### 13. Re-enable Failure Notifications
Restore the production notification setting:
```json
// Tool: ha_config_set_automation
{
  "identifier": "automation.emhass_basic_automation",
  "config_hash": "<config_hash>",
  "python_transform": "config['use_blueprint']['input']['enable_optim_failure_notification'] = True",
  "BestPracticeKey": "<key>",
  "MandatoryBPS": false
}
```
If `automation_started_manually` was modified in Step 8, restore its initial value.
Ensure local Git workspace is clean and committed.
