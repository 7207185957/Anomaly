from __future__ import annotations

import json
import re
from collections import defaultdict
from typing import Any

from ollama import Client

from app.core.config import get_settings
from app.services.ollama_mlflow_wrapper import configure_mlflow, ollama_chat_with_mlflow


def _parse_json_object(text: str) -> dict[str, Any] | None:
    raw = (text or "").strip()
    if not raw:
        return None
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", raw, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        raw = fenced.group(1).strip()
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    first = raw.find("{")
    last = raw.rfind("}")
    if first >= 0 and last > first:
        snippet = raw[first : last + 1]
        try:
            parsed = json.loads(snippet)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return None
    return None


class LlmService:
    def __init__(self) -> None:
        self.settings = get_settings()
        configure_mlflow()
        self.client = Client(host=self.settings.ollama_host)

    def summarize_top_anomalies(
        self,
        *,
        keyword: str,
        assets: list[dict[str, Any]],
        anomalies: list[dict[str, Any]],
        pg_source: dict[str, Any] | None = None,
        pg_tables: list[dict[str, Any]] | None = None,
        pg_query_ctx: dict[str, Any] | None = None,
        pg_snapshot: Any = None,
    ) -> list[dict[str, Any]]:
        grouped: dict[tuple[str, str], int] = defaultdict(int)
        for a in anomalies or []:
            metric = a.get("metric")
            instance = a.get("instance")
            if metric and instance:
                grouped[(str(metric), str(instance))] += 1

        summary_groups = []
        for (metric, instance), count in grouped.items():
            asset_info = next((x for x in assets if x.get("asset_id") == instance), {})
            summary_groups.append(
                {
                    "metric": metric,
                    "asset_id": instance,
                    "asset_name": asset_info.get("name", ""),
                    "anomaly_count": count,
                }
            )
        top_groups = sorted(summary_groups, key=lambda x: x["anomaly_count"], reverse=True)[:5]
        if not top_groups:
            return []

        formatted_groups = "\n".join(
            f"- {g['metric']} | {g['asset_id']} | {g['anomaly_count']}" for g in top_groups
        )
        prompt = f"""
AIOps anomaly summarizer.

Return JSON ONLY:
[
  {{
    "metric": "<metric>",
    "asset_id": "<asset>",
    "anomaly_count": <count>,
    "summary": "<1 sentence>",
    "recommendation": "<1 action>"
  }}
]

Groups:
{formatted_groups}
""".strip()

        result = ollama_chat_with_mlflow(
            client=self.client,
            model=self.settings.ollama_model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1, "num_predict": 220, "seed": 42},
            run_name="generate_llm_outputs_assets_only_v3",
            tags={"service": "aiops", "fn": "generate_llm_outputs_assets_only_v3", "keyword": keyword},
            log_dataset=True,
            dataset_name="infra_anomaly_inputs",
            log_postgres_dataset=True,
            postgres_source=pg_source or {},
            postgres_tables=pg_tables or [],
            postgres_query_context=pg_query_ctx or {},
            postgres_snapshot=pg_snapshot,
            postgres_snapshot_max_rows=200,
        )
        msg = result.get("content", "")
        try:
            parsed = json.loads(msg)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
        return [
            {
                "metric": g["metric"],
                "asset_id": g["asset_id"],
                "anomaly_count": g["anomaly_count"],
                "summary": msg,
                "recommendation": msg,
            }
            for g in top_groups
        ]

    def generate_bucket_summary(self, payload_text: str) -> str:
        prompt = f"""
You are an SRE incident commander.
Return plain text with 6-9 short sentences.
Include top anomaly metrics, likely health score drivers, impact explanation, and affected instances.
Do not hallucinate unknown numbers.

DATA:
{payload_text}
""".strip()
        result = ollama_chat_with_mlflow(
            client=self.client,
            model=self.settings.ollama_model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.2, "num_predict": 400},
            run_name="rca_bucket_summary",
            tags={"service": "aiops", "fn": "rca_bucket_summary"},
            log_dataset=True,
        )
        return result.get("content", "")

    def generate_incident_executive_summary(
        self,
        *,
        incident: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        context = context or {}
        prompt = f"""
You are an SRE incident commander.
Return JSON only with exactly these keys:
{{
  "executive_summary": "<2-4 short lines>",
  "incident_summary": "<what happened, impact, current status>",
  "probable_cause": "<most probable cause based on given incident + context>",
  "recommended_fix": "<next concrete remediation and validation actions>"
}}

Rules:
- Do not invent unavailable facts.
- If evidence is missing, explicitly say "insufficient evidence".
- Keep each field concise and action-oriented.

INCIDENT:
{json.dumps(incident, default=str, ensure_ascii=False)}

CONTEXT:
{json.dumps(context, default=str, ensure_ascii=False)}
""".strip()
        result = ollama_chat_with_mlflow(
            client=self.client,
            model=self.settings.ollama_model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.15, "num_predict": 420, "seed": 42},
            run_name="incident_executive_summary",
            tags={"service": "aiops", "fn": "incident_executive_summary"},
            log_dataset=True,
            dataset_name="incident_summary_inputs",
        )
        content = result.get("content", "")
        parsed = _parse_json_object(content)
        if parsed:
            return {
                "executive_summary": str(parsed.get("executive_summary") or "").strip(),
                "incident_summary": str(parsed.get("incident_summary") or "").strip(),
                "probable_cause": str(parsed.get("probable_cause") or "").strip(),
                "recommended_fix": str(parsed.get("recommended_fix") or "").strip(),
            }
        # Fallback if the model doesn't return strict JSON.
        plain = (content or "").strip() or "insufficient evidence"
        return {
            "executive_summary": plain,
            "incident_summary": plain,
            "probable_cause": "insufficient evidence",
            "recommended_fix": "Collect additional incident context and rerun summary generation.",
        }

