# AIOps Backend

Enterprise FastAPI backend for incidents, health analytics, logs, topology, and RCA jobs.

## Run locally

```bash
cd apps/backend
pip install -e ".[dev]"
uvicorn app.main:app --host 0.0.0.0 --port 9001 --reload
```

## Environment

Copy `.env.example` at repository root and populate secrets through environment variables.

### Demo mode

You can run backend without LDAP/DB/Loki/Nebula dependencies:

```bash
DEMO_MODE=true
DEMO_USERNAME=demo
DEMO_PASSWORD=demo123
```

In this mode, summary/log/topology/job endpoints return synthetic demo data.
