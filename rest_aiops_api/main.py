from __future__ import annotations

from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query

from .aiops_client import build_aiops_payload, post_json
from .db import Db
from .ollama_client import get_keywords_from_ollama
from .rca_logic import probable_change_text, smart_fix_recommendation
from .schemas import (
    AIOpsSummaryRequest,
    KeywordExtractRequest,
    KeywordExtractResponse,
    RCAReportRequest,
    RCAReportResponse,
)
from .settings import get_settings


settings = get_settings()
db = Db(settings)

app = FastAPI(title="REST AIOps API", version="0.1.0")


@app.get("/healthz")
def healthz() -> dict[str, Any]:
    return {"ok": True, "version": app.version}


@app.get("/incidents")
def list_incidents(
    limit: int = Query(100, ge=1, le=5000),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    try:
        rows = db.fetch_all(
            "SELECT * FROM incidents ORDER BY start_time DESC LIMIT :limit OFFSET :offset",
            {"limit": limit, "offset": offset},
        )
        return {"items": rows, "limit": limit, "offset": offset, "count": len(rows)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/alerts")
def list_alerts(
    incident_id: Optional[str] = None,
    limit: int = Query(1000, ge=1, le=20000),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    try:
        if incident_id:
            rows = db.fetch_all(
                "SELECT * FROM alerts WHERE incident_id = :incident_id ORDER BY alert_time DESC LIMIT :limit OFFSET :offset",
                {"incident_id": incident_id, "limit": limit, "offset": offset},
            )
        else:
            rows = db.fetch_all(
                "SELECT * FROM alerts ORDER BY alert_time DESC LIMIT :limit OFFSET :offset",
                {"limit": limit, "offset": offset},
            )
        return {"items": rows, "incident_id": incident_id, "limit": limit, "offset": offset, "count": len(rows)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/keywords/extract", response_model=KeywordExtractResponse)
def extract_keywords(req: KeywordExtractRequest) -> KeywordExtractResponse:
    try:
        raw = get_keywords_from_ollama(
            ollama_url_generate=settings.ollama_url_generate,
            model=settings.ollama_model,
            text_values=req.texts,
            timeout_seconds=30,
        )
        keywords = sorted({k.strip() for k in raw.split(",") if k.strip()})
        return KeywordExtractResponse(raw=raw, keywords=keywords)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ollama keyword extraction failed: {e}")


@app.post("/aiops/summary")
def aiops_summary(req: AIOpsSummaryRequest) -> dict[str, Any]:
    try:
        payload = build_aiops_payload(
            keyword=req.keyword,
            lookback_hours=req.lookback_hours,
            start_utc=req.start_utc,
            end_utc=req.end_utc,
        )
        return post_json(settings.aiops_api_url, payload, timeout_seconds=settings.request_timeout_seconds)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AIOps /summarize call failed: {e}")


@app.post("/aiops/summary_app")
def aiops_summary_app(req: AIOpsSummaryRequest) -> dict[str, Any]:
    try:
        payload = build_aiops_payload(
            keyword=req.keyword,
            lookback_hours=req.lookback_hours,
            start_utc=req.start_utc,
            end_utc=req.end_utc,
        )
        return post_json(settings.aiops_api_url_app, payload, timeout_seconds=settings.request_timeout_seconds)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AIOps /summarize_app call failed: {e}")


@app.post("/aiops/summary_combined")
def aiops_summary_combined(req: AIOpsSummaryRequest) -> dict[str, Any]:
    try:
        payload = build_aiops_payload(
            keyword=req.keyword,
            lookback_hours=req.lookback_hours,
            start_utc=req.start_utc,
            end_utc=req.end_utc,
        )
        return post_json(settings.aiops_api_url_combined, payload, timeout_seconds=settings.request_timeout_seconds)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AIOps /summarize_combined call failed: {e}")


@app.post("/rca/report", response_model=RCAReportResponse)
def rca_report(req: RCAReportRequest) -> RCAReportResponse:
    if not settings.db_uri and req.incident_id:
        raise HTTPException(status_code=500, detail="DB_URI is not set; incident_id lookup cannot be performed")

    incident: dict[str, Any] = {}
    alerts: list[dict[str, Any]] = []

    if req.incident_id:
        try:
            rows = db.fetch_all("SELECT * FROM incidents WHERE incident_id = :id LIMIT 1", {"id": req.incident_id})
            incident = rows[0] if rows else {}
            alerts = db.fetch_all(
                "SELECT * FROM alerts WHERE incident_id = :id ORDER BY alert_time DESC LIMIT 5000",
                {"id": req.incident_id},
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"DB lookup failed: {e}")

    keyword = (req.keyword or "").strip()
    if not keyword:
        # Fallback: extract from incident + alerts text (Streamlit-like behavior)
        candidate_texts = []
        for field in ["title", "description", "service_impacted", "root_cause"]:
            v = incident.get(field)
            if v:
                candidate_texts.append(str(v))
        for a in alerts[:100]:
            for field in ["alert_name", "service", "severity"]:
                v = a.get(field)
                if v:
                    candidate_texts.append(str(v))

        if candidate_texts:
            try:
                raw = get_keywords_from_ollama(
                    ollama_url_generate=settings.ollama_url_generate,
                    model=settings.ollama_model,
                    text_values=candidate_texts,
                    timeout_seconds=30,
                )
                kws = [k.strip() for k in raw.split(",") if k.strip()]
                keyword = kws[0] if kws else ""
            except Exception:
                keyword = ""

    if not keyword:
        raise HTTPException(status_code=400, detail="keyword is required (or provide incident_id with extractable text)")

    service = (req.service_impacted or incident.get("service_impacted") or "unknown").strip()
    title = (req.title or incident.get("title") or "").strip()
    description = (req.description or incident.get("description") or "").strip()

    executive = {
        "probable_change": probable_change_text(keyword, service),
        "recommended_fix": smart_fix_recommendation(keyword, service, title, description, alerts),
        "service_impacted": service,
        "title": title,
        "description": description,
    }

    aiops: dict[str, Any] = {}

    payload = build_aiops_payload(
        keyword=keyword,
        lookback_hours=req.lookback_hours,
        start_utc=req.start_utc,
        end_utc=req.end_utc,
    )

    if req.include_aiops_combined:
        try:
            aiops["combined"] = post_json(
                settings.aiops_api_url_combined,
                payload,
                timeout_seconds=settings.request_timeout_seconds,
            )
        except Exception as e:
            aiops["combined_error"] = str(e)

    if req.include_aiops_infra:
        try:
            aiops["infra"] = post_json(settings.aiops_api_url, payload, timeout_seconds=settings.request_timeout_seconds)
        except Exception as e:
            aiops["infra_error"] = str(e)

    if req.include_aiops_app:
        try:
            aiops["app"] = post_json(
                settings.aiops_api_url_app,
                payload,
                timeout_seconds=settings.request_timeout_seconds,
            )
        except Exception as e:
            aiops["app_error"] = str(e)

    return RCAReportResponse(
        keyword=keyword,
        incident_id=req.incident_id,
        executive_summary=executive,
        aiops=aiops,
    )

