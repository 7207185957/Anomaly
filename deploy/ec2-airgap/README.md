# Air-Gapped EC2 Deployment

This folder provides an offline deployment flow for environments with no internet access.

## Strategy

1. Build and package everything on a connected machine.
2. Transfer the bundle (`.tar.gz`) to the air-gapped EC2 instance.
3. Load Docker images and run with `docker compose`.

This avoids `pip install` and `npm install` on the air-gapped host.

## 1) On a connected build machine

```bash
./deploy/ec2-airgap/package-online.sh
```

This produces:
- `offline-bundle/images/*.tar` (backend/frontend/worker/redis images)
- `offline-bundle/docker-compose.yml` (offline image-only compose)
- `offline-bundle/.env.example`
- `offline-bundle/install-offline.sh`

## 2) Transfer bundle to EC2 (air-gapped)

Use your approved transfer mechanism (scp via bastion, artifact gateway, removable media, etc.).

## 3) On air-gapped EC2

```bash
tar -xzf offline-bundle.tar.gz
cd offline-bundle
cp .env.example .env
# edit .env with real values
./install-offline.sh
```

`install-offline.sh` auto-detects Compose command and supports both:
- `docker compose`
- `docker-compose`

If Compose is missing or broken (for example `http+docker` Python docker-compose errors),
the installer automatically falls back to plain `docker run` orchestration.

## Optional: offline dependency mirrors

If you must rebuild in air-gap:
- Pre-load Python wheels (`pip download -r requirements`) to internal wheelhouse.
- Pre-load npm tarballs or use an internal npm proxy.
- Prefer immutable prebuilt containers for reliability and faster recovery.

