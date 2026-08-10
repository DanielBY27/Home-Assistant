---
name: solcast-update
description: Fast, token-efficient Solcast synchronization. Reads solcast_data_logger.csv from Home Assistant via SSH, appends data to Google Sheets ('Import'), expands formulas in 'Auswertung', extracts damp factors from 'Pivot-Tabelle 1', updates the automation directly in Home Assistant via ha_mcp (no restart/reload needed), and synchronizes the local Git repository.
---

# Solcast Data Sync & Damp Factor Update

This skill runs a fast, headless workflow without browser interaction to minimize token consumption and execution time.

### Workflow Steps:

#### Step 1: Synchronize Data & Read Pivot Table
Run the automated PowerShell sync script:
```powershell
powershell -File tools/sync_solcast_from_ha.ps1
```
This script automatically:
1. Reads `/config/solcast_data_logger.csv` from Home Assistant via SSH (`homeassistant`).
2. If empty, exits immediately.
3. Appends new rows to Google Sheet `1Iq5dkjayb4yvALm_uNDdIcQKYLmsaXzeTYg05pACqgQ` (tab `Import`) via Docker Google API.
4. Expands formulas in tab `Auswertung` to match the new row count.
5. Clears `/config/solcast_data_logger.csv` on Home Assistant (`echo '' > ...`).
6. Fetches and outputs the latest damp factors for the current month from `Pivot-Tabelle 1`.

#### Step 2: Update Automation in Home Assistant (via MCP Server)
If damp factors for the current month need updating:
1. Read current automation config using `ha_mcp`:
   Call `ha_config_get_automation(identifier="automation.pv_forecast_damp_factor_solcast")` to retrieve the current config and `config_hash`.
2. Update the `damp_factor_string` overrides dictionary for the current month with the new factors.
3. Apply changes via `ha_mcp`:
   Call `ha_config_set_automation(identifier="automation.pv_forecast_damp_factor_solcast", config_hash=..., config=...)`.
   *(Note: No Home Assistant restart or reload is required; the HA API applies config changes immediately).*

#### Step 3: Synchronize Local YAML & Commit to Git
1. Update the local file to keep the repository in sync:
   `examples/automation/pv_forecast_damp_factor_solcast.yaml`
2. Commit the changes:
```powershell
git add examples/automation/pv_forecast_damp_factor_solcast.yaml
git commit -m "automation: update solcast damp factors"
```
3. Present a concise summary table of the updated damp factors and completed actions to the user.
