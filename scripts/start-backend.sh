#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$ROOT/backend"
VENV="$BACKEND_DIR/.venv"
PORT="${FOCUS_GUARD_PORT:-8787}"

if [ ! -d "$VENV" ]; then
  echo "Backend virtualenv not found — running setup ..."
  bash "$ROOT/scripts/setup-backend.sh"
fi

cd "$BACKEND_DIR"
# shellcheck disable=SC1091
source "$VENV/bin/activate"

echo "Starting Focus Guard backend on http://127.0.0.1:${PORT}"
exec uvicorn main:app --reload --host 127.0.0.1 --port "$PORT"
