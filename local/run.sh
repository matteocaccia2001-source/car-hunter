#!/bin/bash
# Runner chiamato da launchd ogni 6 ore.
cd "$(dirname "$0")/.."
source .venv/bin/activate
set -a; source .env; set +a
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "▶ Run: $(date '+%Y-%m-%d %H:%M:%S')"
echo "═══════════════════════════════════════════════════════════"
python execution/main.py
