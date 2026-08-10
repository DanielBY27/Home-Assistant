<#
.SYNOPSIS
    Führt Google Drive & Google Sheets Befehle im Docker-Container aus.
.EXAMPLE
    .\tools\run_google.ps1 read-sheet --id 1Iq5dkjayb4yvALm_uNDdIcQKYLmsaXzeTYg05pACqgQ --range "Import!A1:E5"
.EXAMPLE
    .\tools\run_google.ps1 list-files
.EXAMPLE
    .\tools\run_google.ps1 auth
#>

[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$CommandArgs
)

# Prüfen, ob das Docker Image existiert, andernfalls bauen
$imageCheck = docker images -q home-assistant-tests
if (-not $imageCheck) {
    Write-Host "Docker-Image 'home-assistant-tests' wird gebaut..." -ForegroundColor Cyan
    docker build -t home-assistant-tests ./tests/
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Docker Build fehlgeschlagen."
        exit $LASTEXITCODE
    }
}

if ($CommandArgs -contains "auth") {
    Write-Host "Starte interaktiven Auth-Modus mit Portweiterleitung 8080..." -ForegroundColor Yellow
    docker run --rm -it -p 8080:8080 -v "${PWD}:/app" -w /app home-assistant-tests python -m tools.google.cli $CommandArgs
} else {
    docker run --rm -v "${PWD}:/app" -w /app home-assistant-tests python -m tools.google.cli $CommandArgs
}

exit $LASTEXITCODE
