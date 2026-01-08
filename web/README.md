# React Enterprise UI (Streamlit replacement)

This is a React + TypeScript “enterprise” UI that mirrors the Streamlit app UX, but uses the REST service in `rest_aiops_api/`.

## Configure

Create `.env` from `.env.example`:

```bash
cp .env.example .env
```

Set:

- `VITE_API_BASE_URL` (default `http://127.0.0.1:9010`)

## Install / run

```bash
npm install
npm run dev
```

## Backend requirement

Start the REST API first:

```bash
export DB_URI="postgresql+psycopg2://USER:PASS@HOST:5432/DB"
uvicorn rest_aiops_api.main:app --host 0.0.0.0 --port 9010
```

Also ensure your existing AIOps backend (the one that exposes `/summarize*`) is running and reachable from the REST API.

