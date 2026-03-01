# Enterprise AIOps Platform

This repository is a fresh, enterprise-grade rebuild of the previous Streamlit prototype.

## What changed

- Streamlit UI removed and replaced with a modular web product:
  - **Frontend**: Next.js + TypeScript + MUI + React Query + AG Grid + ECharts
  - **Backend**: FastAPI modular API with LDAP auth and versioned routes
- Hardcoded runtime endpoints removed from app code.
- Added Redis-backed async jobs for expensive RCA generation.
- Added deployment support for:
  - Kubernetes/EKS via Helm
  - Air-gapped EC2 environments

## Repository layout

```text
apps/
  backend/   # FastAPI service
  frontend/  # Next.js application
deploy/
  helm/      # Helm chart
  ec2-airgap/# Offline bundle + install scripts
scripts/     # Utility scripts
```

## Why Redis is used

Redis is used as the queue backend for long-running jobs (for example LLM-based RCA/report generation).

Benefits:
- user requests return immediately with `job_id`
- UI remains responsive and independent per module
- expensive tasks do not block health/log/topology APIs
- scales horizontally by running more workers

## Backend API (v1)

- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `POST /api/v1/summaries/combined`
- `POST /api/v1/cluster/health`
- `POST /api/v1/logs/query`
- `POST /api/v1/topology/graph`
- `POST /api/v1/jobs/rca`
- `GET /api/v1/jobs/{job_id}`

## Local run (docker compose)

```bash
cp .env.example .env
docker compose up --build
```

Services:
- Frontend: http://localhost:3000
- Backend: http://localhost:9001
- Redis is internal-only in Docker network (no host 6379 bind by default)

If host ports are already in use, set in `.env`:

```bash
FRONTEND_HOST_PORT=3001
BACKEND_HOST_PORT=9002
NEXT_PUBLIC_API_BASE_URL=http://localhost:9002/api/v1
```

Important: `NEXT_PUBLIC_*` variables are embedded into the frontend at build-time.
After changing them, rebuild the frontend image:

```bash
docker compose build frontend
docker compose up -d
```

## Cloud agent environment bootstrap

Use these scripts in cloud/onboarding setup so dependencies are preinstalled once:

```bash
./scripts/cloud-agent-bootstrap.sh
./scripts/cloud-agent-verify.sh
```

What this preinstalls:
- backend Python deps from `apps/backend/pyproject.toml` (including `[dev]`)
- frontend npm deps from `apps/frontend/package-lock.json`
- validates lint/build/test readiness for both demo and normal mode

## Demo mode (Option 2)

Set these in `.env`:

```bash
DEMO_MODE=true
DEMO_USERNAME=demo
DEMO_PASSWORD=demo123
NEXT_PUBLIC_DEMO_MODE=true
NEXT_PUBLIC_DEMO_USERNAME=demo
NEXT_PUBLIC_DEMO_PASSWORD=demo123
```

In demo mode:
- login is local (no LDAP dependency)
- health/alerts/incidents/logs/topology use synthetic realistic data
- RCA jobs are simulated and complete quickly

## Air-gapped EC2 deployment

See `deploy/ec2-airgap/README.md` for offline packaging and installation flow.

## Kubernetes/EKS

See `deploy/helm/aiops/` for Helm chart and values.

