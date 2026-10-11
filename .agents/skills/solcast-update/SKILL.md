---
name: solcast-update
description: Fast, token-efficient Solcast synchronization and intelligent damp factor calculation. Reads solcast_data_logger.csv from Home Assistant via SSH, appends data to Google Sheets ('Import'), expands formulas in 'Auswertung', extracts 'Pivot-Tabelle 1' damp factor stats, analyzes the curve with AI-assisted solar domain logic (shading, weather weighting, curve smoothing), updates the automation directly in Home Assistant via ha_mcp, and synchronizes the local Git repository.
---

# Solcast Data Sync & Intelligent Damp Factor Optimization

This skill synchronizes actual PV generation with Solcast forecasts and intelligently optimizes the hourly dampening curve using physical solar reasoning and historical data.

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
5. Clears `/config/solcast_data_logger.csv` on Home Assistant (`sudo truncate -s 0 ...`).
6. Fetches and outputs the latest damp factors for the active month from `Pivot-Tabelle 1`.

#### Step 2: Intelligent AI Evaluation of Damp Factors
Do NOT just blindly copy raw numbers. Apply intelligent solar forecasting logic:
1. **Weather Weighting:** Prioritize `sunny` and `partlycloudy` columns over `cloudy`/`rainy`, because on clear days forecast errors have the largest absolute kWh impact on battery and EMS planning.
2. **Shading & Solar Geometry:** Check for morning and late afternoon shading (steep drops in `sunny` dampening ratio due to trees, roofs, or horizon).
3. **Curve Smoothing:** Ensure a physically plausible diurnal curve without erratic hour-to-hour jumps.
4. **Outlier Protection:** Avoid overreacting to single cloudy or foggy days with low sample counts.
5. Determine the optimized hourly damp factors for the current month.

#### Step 3: Update Automation in Home Assistant (via MCP Server)
If damp factors for the current month changed:
1. Read current automation config using `ha_mcp`:
   Call `ha_config_get_automation(identifier="automation.pv_forecast_damp_factor_solcast")` to retrieve the config and `config_hash`.
2. Update the `damp_factor_string` overrides dictionary for the current month with the optimized hourly factors.
3. Apply changes via `ha_mcp`:
   Call `ha_config_set_automation(identifier="automation.pv_forecast_damp_factor_solcast", config_hash=..., config=...)`.
   *(No Home Assistant restart or reload required; the HA API applies config changes immediately).*

#### Step 4: Synchronize Local YAML & Commit to Git
1. Update the local file to keep the repository in sync:
   `examples/automation/pv_forecast_damp_factor_solcast.yaml`
2. Commit the changes:
```powershell
git add examples/automation/pv_forecast_damp_factor_solcast.yaml
git commit -m "automation: optimize solcast damp factors for $(Get-Date -Format 'yyyy-MM')"
```
3. Present a clear before/after comparison table and explain the physical/statistical reasoning to the user.
