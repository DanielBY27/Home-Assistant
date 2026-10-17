<#
.SYNOPSIS
    Runs the Home Assistant System Health, Ghost Entity, and Database Bloat Inspector over SSH.
.DESCRIPTION
    Pipes tools/ha_system_health.py into python3 on Home Assistant to perform
    a deep audit of automations, scripts, dashboards, custom sensors, and database bloaters.
    Passes local examples/automation/ha_database_purge.yaml as base64 to verify synchronization.
#>

$ErrorActionPreference = "Stop"
$scriptPath = Join-Path $PSScriptRoot "ha_system_health.py"

if (-not (Test-Path $scriptPath)) {
    Write-Error "Script not found at $scriptPath"
    exit 1
}

$purgeYamlPath = Join-Path $PSScriptRoot "..\examples\automation\ha_database_purge.yaml"
$b64 = ""
if (Test-Path $purgeYamlPath) {
    $rawContent = [System.IO.File]::ReadAllText($purgeYamlPath, [System.Text.Encoding]::UTF8)
    $b64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($rawContent))
}

$pyScript = Get-Content $scriptPath -Raw
$pyScript | ssh homeassistant "LOCAL_PURGE_B64='$b64' python3"
