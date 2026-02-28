from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

from ollama import Client

from app.core.config import get_settings
from app.services.ollama_mlflow_wrapper import configure_mlflow, ollama_chat_with_mlflow


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

