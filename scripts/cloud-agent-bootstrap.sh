#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="${ROOT_DIR}/apps/backend"
FRONTEND_DIR="${ROOT_DIR}/apps/frontend"

echo "[bootstrap] Root: ${ROOT_DIR}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "[bootstrap] ERROR: python3 not found"
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "[bootstrap] ERROR: npm not found"
  exit 1
fi

export PATH="${HOME}/.local/bin:${PATH}"

echo "[bootstrap] Upgrading pip/setuptools/wheel"
python3 -m pip install --upgrade pip setuptools wheel

echo "[bootstrap] Installing backend editable deps (including dev extras)"
python3 -m pip install -e "${BACKEND_DIR}[dev]"

echo "[bootstrap] Installing frontend npm deps"
npm ci --prefix "${FRONTEND_DIR}"

echo "[bootstrap] Pre-compiling backend python modules"
python3 -m compileall "${BACKEND_DIR}/app"

echo "[bootstrap] Completed successfully"

