#!/usr/bin/env bash
# Lance le bot v2 (scraping multi-agents + crédibilité) en CLI.
set -e
cd "$(dirname "$0")"
if [ -d ".venv" ]; then .venv/bin/python -m bot "$@"; else python3 -m bot "$@"; fi
