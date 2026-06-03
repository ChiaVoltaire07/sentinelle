# Backup local des bases SQLite (médical + scrapper + auth).
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$dest = Join-Path "backups" $stamp
New-Item -ItemType Directory -Force -Path $dest | Out-Null
foreach ($f in @("data\medical.db", "data\scrapper.db", "data\auth.db")) {
    if (Test-Path $f) {
        Copy-Item $f (Join-Path $dest (Split-Path $f -Leaf))
        Write-Host "OK $f"
    }
}
Write-Host "Backup -> $dest"
