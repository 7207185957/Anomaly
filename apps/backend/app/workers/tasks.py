from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.llm_service import LlmService


def run_rca_job(keyword: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    llm = LlmService()
    context = context or {}
    payload = f"keyword={keyword}\ncontext={context}"
    summary = llm.generate_bucket_summary(payload)
    return {
        "keyword": keyword,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "context": context,
    }

