# Lance la PWA / tableau de bord (FastAPI + uvicorn) sur Windows.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# Prefer a real Windows Python. Ignore Linux-style .venv\bin\python (WSL venv).
$python = $null
if (Test-Path ".venv\Scripts\python.exe") {
    $python = (Resolve-Path ".venv\Scripts\python.exe").Path
} else {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { $python = $cmd.Source }
}

if (-not $python) {
    Write-Error "Python introuvable. Installez Python ou creez un venv Windows: python -m venv .venv"
    exit 1
}

Write-Host "Python: $python" -ForegroundColor DarkGray
Write-Host "PWA + API -> http://localhost:8000  (Ctrl+C pour arreter)" -ForegroundColor Cyan

& $python -c "import uvicorn, fastapi" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installation des dependances minimales..." -ForegroundColor Yellow
    & $python -m pip install "fastapi" "uvicorn[standard]" "requests" "python-multipart" "httpx" "psycopg2-binary" "pgvector" "beautifulsoup4"
}

& $python -m uvicorn web.server:app --host 127.0.0.1 --port 8000 @args
