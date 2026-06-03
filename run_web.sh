#!/usr/bin/env bash
# Lance la PWA / tableau de bord (FastAPI + uvicorn).
set -e
cd "$(dirname "$0")"
if [ -d ".venv" ]; then .venv/bin/python -m uvicorn web.server:app --host 0.0.0.0 --port 8000 "$@";
else python3 -m uvicorn web.server:app --host 0.0.0.0 --port 8000 "$@"; fi
