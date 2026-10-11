<#
.SYNOPSIS
    Liest solcast_data_logger.csv von Home Assistant, synchronisiert nach Google Sheets (Import + Auswertung),
    leert die Datei auf Home Assistant und gibt die aktuellen Pivot-Werte aus.
#>

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

Write-Host "1. Lese /config/solcast_data_logger.csv von Home Assistant via SSH..." -ForegroundColor Cyan
$csvData = ssh -o BatchMode=yes homeassistant "cat /config/solcast_data_logger.csv"

if (-not $csvData -or $csvData.Trim() -eq "") {
    Write-Host "Keine neuen Solcast-Daten in Home Assistant vorhanden." -ForegroundColor Yellow
    exit 0
}

$nonEmptyLines = ($csvData.Trim() -split "`r?`n") | Where-Object { $_.Trim() -ne "" }
$lineCount = $nonEmptyLines.Count
Write-Host "Gefundene Datenzeilen: $lineCount" -ForegroundColor Green

$tempCsv = "credentials/temp_solcast_import.csv"
$csvData | Out-File -FilePath $tempCsv -Encoding utf8

try {
    Write-Host "2. Synchronisiere Daten nach Google Sheets ('Import' & 'Auswertung')..." -ForegroundColor Cyan
    docker run --rm -v "${PWD}:/app" -e PYTHONPATH=/app -w /app home-assistant-tests python -m tools.google.cli sync-solcast --csv-file $tempCsv
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Fehler bei der Google Sheets Synchronisation."
        exit $LASTEXITCODE
    }

    Write-Host "3. Leere /config/solcast_data_logger.csv auf Home Assistant..." -ForegroundColor Cyan
    ssh -o BatchMode=yes homeassistant "sudo truncate -s 0 /config/solcast_data_logger.csv"
    Write-Host "Datei auf Home Assistant erfolgreich geleert." -ForegroundColor Green

    Write-Host "`n4. Lese aktuelle Dämpfungsfaktoren aus 'Pivot-Tabelle 1'..." -ForegroundColor Cyan
    docker run --rm -v "${PWD}:/app" -e PYTHONPATH=/app -w /app home-assistant-tests python -m tools.google.cli get-pivot
} finally {
    if (Test-Path $tempCsv) {
        Remove-Item -Force $tempCsv -ErrorAction SilentlyContinue
    }
}
