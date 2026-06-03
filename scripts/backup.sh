#!/usr/bin/env bash
# Backup SQLite local
set -e
cd "$(dirname "$0")/.."
stamp=$(date +%Y%m%d_%H%M%S)
dest="backups/$stamp"
mkdir -p "$dest"
for f in data/medical.db data/scrapper.db data/auth.db; do
  [ -f "$f" ] && cp "$f" "$dest/" && echo "OK $f"
done
echo "Backup -> $dest"
