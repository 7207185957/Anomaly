#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BUNDLE_DIR="${ROOT_DIR}/deploy/ec2-airgap/offline-bundle"
IMAGES_DIR="${BUNDLE_DIR}/images"

mkdir -p "${IMAGES_DIR}"

echo "[1/5] Building docker images"
docker build -t aiops-backend:offline "${ROOT_DIR}/apps/backend" -f "${ROOT_DIR}/apps/backend/Dockerfile"
docker build -t aiops-worker:offline "${ROOT_DIR}/apps/backend" -f "${ROOT_DIR}/apps/backend/Dockerfile.worker"
docker build \
  --build-arg NEXT_PUBLIC_API_BASE_URL="${NEXT_PUBLIC_API_BASE_URL:-http://localhost:9001/api/v1}" \
  --build-arg NEXT_PUBLIC_DEMO_MODE="${NEXT_PUBLIC_DEMO_MODE:-false}" \
  --build-arg NEXT_PUBLIC_DEMO_USERNAME="${NEXT_PUBLIC_DEMO_USERNAME:-demo}" \
  --build-arg NEXT_PUBLIC_DEMO_PASSWORD="${NEXT_PUBLIC_DEMO_PASSWORD:-demo123}" \
  -t aiops-frontend:offline "${ROOT_DIR}/apps/frontend" -f "${ROOT_DIR}/apps/frontend/Dockerfile"
docker pull redis:7-alpine

echo "[2/5] Saving images as tar archives"
docker save aiops-backend:offline > "${IMAGES_DIR}/aiops-backend.tar"
docker save aiops-worker:offline > "${IMAGES_DIR}/aiops-worker.tar"
docker save aiops-frontend:offline > "${IMAGES_DIR}/aiops-frontend.tar"
docker save redis:7-alpine > "${IMAGES_DIR}/redis.tar"

echo "[3/5] Copying runtime files"
cp "${ROOT_DIR}/deploy/ec2-airgap/docker-compose.offline.yml" "${BUNDLE_DIR}/docker-compose.yml"
cp "${ROOT_DIR}/.env.example" "${BUNDLE_DIR}/.env.example"
cp "${ROOT_DIR}/deploy/ec2-airgap/install-offline.sh" "${BUNDLE_DIR}/install-offline.sh"
chmod +x "${BUNDLE_DIR}/install-offline.sh"

echo "[4/5] Creating tar.gz bundle"
(
  cd "${ROOT_DIR}/deploy/ec2-airgap"
  tar -czf offline-bundle.tar.gz offline-bundle
)

echo "[5/5] Done -> ${ROOT_DIR}/deploy/ec2-airgap/offline-bundle.tar.gz"

