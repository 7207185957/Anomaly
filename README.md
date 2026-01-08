# Anomaly

This repo now includes a **FastAPI REST service** under `rest_aiops_api/` that mirrors the Streamlit app’s data flow (incidents/alerts → keyword extraction → AIOps summarize calls → RCA report JSON).

See `rest_aiops_api/README.md` for install/run instructions.

It also includes a **React enterprise UI** under `web/` (MUI DataGrid + Plotly) that replaces the Streamlit interface and talks to the REST API.