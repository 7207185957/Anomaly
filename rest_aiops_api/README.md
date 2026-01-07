# REST AIOps API (FastAPI)

This is a small REST service that mirrors the Streamlit app behavior:
- reads `incidents` and `alerts` from Postgres
- extracts keywords via Ollama `/api/generate`
- proxies to your existing AIOps backend endpoints (`/summarize`, `/summarize_app`, `/summarize_combined`)
- generates an RCA report JSON payload similar to the Streamlit “RCA Wizard”

## Configuration (env vars)

- `DB_URI` (required): Postgres SQLAlchemy URI  
  Example: `postgresql+psycopg2://ragpoc:ilikemypassword@10.248.194.83:5432/postgres`
- `OLLAMA_URL_GENERATE` (optional): default `http://172.16.109.94:11435/api/generate`
- `OLLAMA_MODEL` (optional): default `mistral:latest`
- `AIOPS_API_URL` (optional): default `http://127.0.0.1:9001/summarize`
- `AIOPS_API_URL_APP` (optional): default `http://127.0.0.1:9001/summarize_app`
- `AIOPS_API_URL_COMBINED` (optional): default `http://127.0.0.1:9001/summarize_combined`

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
export DB_URI="postgresql+psycopg2://ragpoc:ilikemypassword@10.248.194.83:5432/postgres"
uvicorn rest_aiops_api.main:app --host 0.0.0.0 --port 9010
```

## Endpoints

- `GET /healthz`
- `GET /incidents?limit=100&offset=0`
- `GET /alerts?incident_id=<id>&limit=1000&offset=0`
- `POST /keywords/extract`
- `POST /aiops/summary` (proxies `/summarize`)
- `POST /aiops/summary_app` (proxies `/summarize_app`)
- `POST /aiops/summary_combined` (proxies `/summarize_combined`)
- `POST /rca/report` (builds “executive summary” + optional AIOps data)

