#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="${ROOT_DIR}/apps/backend"
FRONTEND_DIR="${ROOT_DIR}/apps/frontend"

export PATH="${HOME}/.local/bin:${PATH}"

echo "[verify] Backend: ruff + pytest"
(
  cd "${BACKEND_DIR}"
  python3 -m ruff check app
  python3 -m pytest -q
)

echo "[verify] Frontend: lint + build"
(
  cd "${FRONTEND_DIR}"
  npm run lint
  npm run build
)

echo "[verify] All checks passed"

