#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$ROOT/backend"
VENV="$BACKEND_DIR/.venv"

if ! command -v python3.12 >/dev/null 2>&1; then
  echo "Python 3.12 is required but was not found on PATH."
  echo "Install it with: brew install python@3.12"
  exit 1
fi

if [ ! -d "$VENV" ]; then
  echo "Creating backend virtualenv at backend/.venv ..."
  python3.12 -m venv "$VENV"
fi

# shellcheck disable=SC1091
source "$VENV/bin/activate"

echo "Installing backend Python dependencies ..."
pip install -r "$BACKEND_DIR/requirements.txt"

echo "Backend setup complete."
