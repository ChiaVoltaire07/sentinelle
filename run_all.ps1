# Demarre l'app web (PWA + API). Les runs se lancent depuis le tableau de bord.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "Portail Clinique - http://localhost:8000  (Ctrl+C pour arreter)" -ForegroundColor Cyan
& (Join-Path $PSScriptRoot "run_web.ps1") @args
