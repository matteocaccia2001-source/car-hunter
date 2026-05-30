#!/bin/bash
# Setup one-shot per Car Hunter su Mac.
# Installa venv Python, dependencies, Playwright Chrome, e configura launchd.

set -e
cd "$(dirname "$0")/.."
PROJECT_DIR="$(pwd)"
echo "📂 Project: $PROJECT_DIR"

# ─── Check prerequisiti ───────────────────────────────────────────────────
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 non trovato. Installalo da https://www.python.org/downloads/"
    exit 1
fi
echo "✅ Python: $(python3 --version)"

# ─── Crea Python venv ─────────────────────────────────────────────────────
if [ ! -d ".venv" ]; then
    echo "📦 Creo Python virtual environment..."
    python3 -m venv .venv
fi
source .venv/bin/activate

# ─── Installa dependencies ────────────────────────────────────────────────
echo "📥 Installo dipendenze Python..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
pip install playwright --quiet

# ─── Installa Chrome headless (Playwright) ────────────────────────────────
echo "🌐 Installo Chrome headless (~150 MB, una volta sola)..."
playwright install chromium

# ─── Verifica .env ────────────────────────────────────────────────────────
if [ ! -f ".env" ]; then
    echo ""
    echo "❌ MANCA il file .env"
    echo ""
    echo "Crealo con questi 2 valori (gli stessi che hai messo nei Secrets GitHub):"
    echo ""
    echo "  GOOGLE_CREDENTIALS_JSON='{\"type\":\"service_account\",...}'"
    echo "  SPREADSHEET_ID=il_tuo_id"
    echo ""
    echo "Poi rilancia: bash local/setup.sh"
    exit 1
fi
echo "✅ .env trovato"

# ─── Test run ─────────────────────────────────────────────────────────────
echo ""
echo "🧪 Eseguo un test run..."
set -a; source .env; set +a
python execution/main.py

# ─── Installa launchd ─────────────────────────────────────────────────────
PLIST_SRC="$PROJECT_DIR/local/com.carhunter.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.carhunter.plist"

# Genera plist dinamico col path corretto
sed "s|__PROJECT_DIR__|$PROJECT_DIR|g" "$PROJECT_DIR/local/com.carhunter.plist.tpl" > "$PLIST_DST"

# Scarica eventuale agente già caricato e ricarica
launchctl unload "$PLIST_DST" 2>/dev/null || true
launchctl load "$PLIST_DST"

echo ""
echo "✅ SETUP COMPLETO"
echo ""
echo "Il sistema gira ora ogni 6 ore: 00:00, 06:00, 12:00, 18:00"
echo "Log: $PROJECT_DIR/.tmp/run.log"
echo ""
echo "Comandi utili:"
echo "  Disabilitare:  launchctl unload $PLIST_DST"
echo "  Riabilitare:   launchctl load $PLIST_DST"
echo "  Esegui ora:    bash local/run.sh"
echo "  Log in tempo reale: tail -f $PROJECT_DIR/.tmp/run.log"
