#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGES_DIR="${SCRIPT_DIR}/images"

if [[ ! -d "${IMAGES_DIR}" ]]; then
  echo "images/ directory not found. Run from offline-bundle root."
  exit 1
fi

echo "[1/3] Loading images"
docker load -i "${IMAGES_DIR}/aiops-backend.tar"
docker load -i "${IMAGES_DIR}/aiops-worker.tar"
docker load -i "${IMAGES_DIR}/aiops-frontend.tar"
docker load -i "${IMAGES_DIR}/redis.tar"

echo "[2/3] Tagging images expected by docker-compose"
docker tag aiops-backend:offline aiops-backend:latest
docker tag aiops-worker:offline aiops-worker:latest
docker tag aiops-frontend:offline aiops-frontend:latest

echo "[3/3] Starting services"
if [[ ! -f "${SCRIPT_DIR}/.env" ]]; then
  cp "${SCRIPT_DIR}/.env.example" "${SCRIPT_DIR}/.env"
  echo "Created .env from template. Please edit secrets and re-run if needed."
fi

docker compose -f "${SCRIPT_DIR}/docker-compose.yml" up -d
docker compose -f "${SCRIPT_DIR}/docker-compose.yml" ps

