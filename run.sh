#!/usr/bin/env bash
# Lance le bot. Utilise le venv s'il existe, sinon le Python système.
set -e
cd "$(dirname "$0")"
if [ -d ".venv" ]; then
  .venv/bin/python main.py "$@"
else
  python3 main.py "$@"
fi
