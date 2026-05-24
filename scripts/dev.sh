#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ ! -d "frontend/node_modules" ]; then
  echo "Installing frontend dependencies..."
  npm --prefix frontend install
fi

if [ ! -d "node_modules" ]; then
  echo "Installing root dev dependencies..."
  npm install
fi

if [ ! -d "backend/.venv" ]; then
  echo "Setting up backend (first run)..."
  bash scripts/setup-backend.sh
fi

npm run dev
