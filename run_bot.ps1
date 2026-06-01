# Lance le bot v2 (scraping multi-agents + credibilite) en CLI sur Windows.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$python = $null
if (Test-Path ".venv\Scripts\python.exe") {
    $python = (Resolve-Path ".venv\Scripts\python.exe").Path
} else {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { $python = $cmd.Source }
}

if (-not $python) {
    Write-Error "Python introuvable."
    exit 1
}

& $python -m bot @args
