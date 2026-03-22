#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# dev.sh — Start backend + frontend locally with hot-reload
# Usage: ./dev.sh
# ─────────────────────────────────────────────────────────────────────────────
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
VENV="$BACKEND/.venv"

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'

log()  { echo -e "${CYAN}[dev]${NC} $*"; }
ok()   { echo -e "${GREEN}[dev]${NC} $*"; }
warn() { echo -e "${YELLOW}[dev]${NC} $*"; }
err()  { echo -e "${RED}[dev]${NC} $*" >&2; }

# ── Cleanup on exit ────────────────────────────────────────────────────────────
BACKEND_PID=""
cleanup() {
  echo ""
  log "Shutting down..."
  [[ -n "$BACKEND_PID" ]] && kill "$BACKEND_PID" 2>/dev/null && ok "Backend stopped"
  ok "Done. Bye!"
}
trap cleanup EXIT INT TERM

# ── 1. Check .env ─────────────────────────────────────────────────────────────
if [[ ! -f "$BACKEND/.env" ]]; then
  err "Missing backend/.env — copy from backend/.env and add your GEMINI_API_KEY"
  exit 1
fi

if grep -q "your_gemini_api_key_here" "$BACKEND/.env"; then
  err "Please set your GEMINI_API_KEY in backend/.env first"
  exit 1
fi

# ── 2. Python venv ────────────────────────────────────────────────────────────
if [[ ! -d "$VENV" ]]; then
  log "Creating Python virtual environment..."
  python3 -m venv "$VENV"
  ok "venv created at backend/.venv"
fi

PY="$VENV/bin/python"
PIP="$VENV/bin/pip"

# ── 3. Install / sync Python deps ─────────────────────────────────────────────
STAMP="$VENV/.installed_stamp"
REQ="$BACKEND/requirements.txt"

if [[ ! -f "$STAMP" ]] || [[ "$REQ" -nt "$STAMP" ]]; then
  log "Installing Python dependencies (this only runs when requirements.txt changes)..."
  "$PIP" install --quiet --upgrade pip
  "$PIP" install --quiet -r "$REQ"
  touch "$STAMP"
  ok "Python deps installed"
else
  ok "Python deps up to date (skipping install)"
fi

# ── 4. Install Node deps ───────────────────────────────────────────────────────
if [[ ! -d "$FRONTEND/node_modules" ]]; then
  log "Installing Node dependencies..."
  cd "$FRONTEND" && npm install --silent
  cd "$ROOT"
  ok "Node deps installed"
else
  ok "Node deps already present (skipping install)"
fi

# ── 5. Start backend with hot-reload ──────────────────────────────────────────
log "Starting backend on http://localhost:10000 (hot-reload on)"
cd "$BACKEND"
"$VENV/bin/uvicorn" main:app \
  --host 0.0.0.0 \
  --port 10000 \
  --reload \
  --reload-dir "$BACKEND" \
  --log-level info &
BACKEND_PID=$!
cd "$ROOT"

# Give uvicorn a moment to start
sleep 2
if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
  err "Backend failed to start — check logs above"
  exit 1
fi
ok "Backend running (PID $BACKEND_PID)"

# ── 6. Start frontend ─────────────────────────────────────────────────────────
log "Starting frontend on http://localhost:3000"
echo ""
echo -e "  ${GREEN}●${NC} Backend : ${BLUE}http://localhost:10000${NC}"
echo -e "  ${GREEN}●${NC} Frontend: ${BLUE}http://localhost:3000${NC}"
echo -e "  ${GREEN}●${NC} API docs: ${BLUE}http://localhost:10000/docs${NC}"
echo -e "  Press ${YELLOW}Ctrl+C${NC} to stop both"
echo ""

cd "$FRONTEND"
npm run dev
