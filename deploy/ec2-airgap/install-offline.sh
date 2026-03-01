#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGES_DIR="${SCRIPT_DIR}/images"

start_with_docker_cli() {
  echo "[fallback] Starting services with plain docker CLI (no Compose dependency)"

  # shellcheck disable=SC1090
  set -a
  source "${SCRIPT_DIR}/.env"
  set +a

  BACKEND_HOST_PORT="${BACKEND_HOST_PORT:-9001}"
  FRONTEND_HOST_PORT="${FRONTEND_HOST_PORT:-3000}"
  RCA_QUEUE_NAME="${RCA_QUEUE_NAME:-rca-jobs}"
  NEXT_PUBLIC_API_BASE_URL="${NEXT_PUBLIC_API_BASE_URL:-http://localhost:9001/api/v1}"
  NEXT_PUBLIC_DEMO_MODE="${NEXT_PUBLIC_DEMO_MODE:-false}"
  NEXT_PUBLIC_DEMO_USERNAME="${NEXT_PUBLIC_DEMO_USERNAME:-demo}"
  NEXT_PUBLIC_DEMO_PASSWORD="${NEXT_PUBLIC_DEMO_PASSWORD:-demo123}"

  docker network inspect aiops-net >/dev/null 2>&1 || docker network create aiops-net

  for c in aiops-frontend aiops-worker aiops-backend aiops-redis; do
    docker rm -f "${c}" >/dev/null 2>&1 || true
  done

  docker run -d --name aiops-redis --network aiops-net redis:7-alpine

  docker run -d \
    --name aiops-backend \
    --network aiops-net \
    --env-file "${SCRIPT_DIR}/.env" \
    -e REDIS_URL="redis://aiops-redis:6379/0" \
    -p "${BACKEND_HOST_PORT}:9001" \
    aiops-backend:latest

  docker run -d \
    --name aiops-worker \
    --network aiops-net \
    --env-file "${SCRIPT_DIR}/.env" \
    -e REDIS_URL="redis://aiops-redis:6379/0" \
    -e RCA_QUEUE_NAME="${RCA_QUEUE_NAME}" \
    aiops-worker:latest

  docker run -d \
    --name aiops-frontend \
    --network aiops-net \
    -e NEXT_PUBLIC_API_BASE_URL="${NEXT_PUBLIC_API_BASE_URL}" \
    -e NEXT_PUBLIC_DEMO_MODE="${NEXT_PUBLIC_DEMO_MODE}" \
    -e NEXT_PUBLIC_DEMO_USERNAME="${NEXT_PUBLIC_DEMO_USERNAME}" \
    -e NEXT_PUBLIC_DEMO_PASSWORD="${NEXT_PUBLIC_DEMO_PASSWORD}" \
    -p "${FRONTEND_HOST_PORT}:3000" \
    aiops-frontend:latest

  docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "aiops-|NAMES" || true
}

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

if docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD=(docker compose)
  if "${COMPOSE_CMD[@]}" -f "${SCRIPT_DIR}/docker-compose.yml" up -d; then
    "${COMPOSE_CMD[@]}" -f "${SCRIPT_DIR}/docker-compose.yml" ps
    exit 0
  fi
  echo "[warn] 'docker compose' failed. Falling back to plain docker CLI."
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD=(docker-compose)
  if "${COMPOSE_CMD[@]}" -f "${SCRIPT_DIR}/docker-compose.yml" up -d; then
    "${COMPOSE_CMD[@]}" -f "${SCRIPT_DIR}/docker-compose.yml" ps
    exit 0
  fi
  echo "[warn] 'docker-compose' failed. Falling back to plain docker CLI."
else
  echo "[warn] No Compose command found. Falling back to plain docker CLI."
fi

start_with_docker_cli

