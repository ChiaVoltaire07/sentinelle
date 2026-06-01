#!/usr/bin/env bash
# Démarre l'app web (PWA + API). Les runs se lancent depuis le tableau de bord.
set -e
cd "$(dirname "$0")"
echo "🌐 Scrapper IA — http://localhost:8000  (Ctrl+C pour arrêter)"
if [ -d ".venv" ]; then .venv/bin/python -m uvicorn web.server:app --host 0.0.0.0 --port 8000 "$@";
else python3 -m uvicorn web.server:app --host 0.0.0.0 --port 8000 "$@"; fi
