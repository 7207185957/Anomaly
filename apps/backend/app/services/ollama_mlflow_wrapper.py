from __future__ import annotations

from contextlib import nullcontext
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

import mlflow
from ollama import Client

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None

logger = logging.getLogger(__name__)


def _safe_mlflow_call(action: str, fn, *args, **kwargs):  # type: ignore[no-untyped-def]
    try:
        return fn(*args, **kwargs)
    except ModuleNotFoundError as exc:
        if str(exc) == "No module named 'boto3'":
            logger.warning("Skipping MLflow %s because boto3 is unavailable", action)
            return None
        raise
    except Exception as exc:  # pragma: no cover
        logger.warning("Skipping MLflow %s due to error: %s", action, exc)
        return None


def _start_mlflow_run(run_name: str | None):
    run_ctx = _safe_mlflow_call("start_run", mlflow.start_run, run_name=run_name, nested=True)
    return run_ctx if run_ctx is not None else nullcontext()


def configure_mlflow() -> None:
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
    if tracking_uri:
        _safe_mlflow_call("set_tracking_uri", mlflow.set_tracking_uri, tracking_uri)
    experiment_name = os.getenv("MLFLOW_EXPERIMENT", "wcs-dataops-mlflow/dataops/infra-anomalies")
    _safe_mlflow_call("set_experiment", mlflow.set_experiment, experiment_name)


def _safe_json(obj: Any) -> str:
    try:
        return json.dumps(obj, default=str, ensure_ascii=False)
    except Exception:
        return str(obj)


def _extract_content(resp: Any) -> str:
    if hasattr(resp, "model_dump"):
        data = resp.model_dump()
    elif isinstance(resp, dict):
        data = resp
    else:
        return str(resp)
    msg = data.get("message") or {}
    return msg.get("content", "") or ""


def _extract_stats(resp: Any) -> dict[str, Any]:
    if hasattr(resp, "model_dump"):
        data = resp.model_dump()
    elif isinstance(resp, dict):
        data = resp
    else:
        data = {"raw": str(resp)}
    return {
        "prompt_eval_count": data.get("prompt_eval_count"),
        "eval_count": data.get("eval_count"),
        "prompt_eval_duration": data.get("prompt_eval_duration"),
        "eval_duration": data.get("eval_duration"),
        "total_duration": data.get("total_duration"),
        "load_duration": data.get("load_duration"),
        "done_reason": data.get("done_reason"),
    }


def _flatten_row(row: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in row.items():
        out[k] = json.dumps(v, default=str) if isinstance(v, (list, dict)) else v
    return out


def _log_postgres_dataset(
    *,
    source: dict[str, Any],
    tables: list[dict[str, Any]],
    query_context: dict[str, Any],
    snapshot: Any,
    name: str,
    max_rows: int = 200,
) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    os.makedirs("datasets", exist_ok=True)

    safe_source = dict(source or {})
    for key in ("password", "pass", "pwd"):
        if key in safe_source:
            safe_source[key] = "***"

    if snapshot is None:
        rows: list[dict[str, Any]] = []
    elif pd is not None and isinstance(snapshot, pd.DataFrame):
        rows = snapshot.to_dict(orient="records")
    elif isinstance(snapshot, list):
        rows = snapshot
    elif isinstance(snapshot, dict):
        rows = [snapshot]
    else:
        rows = [{"raw": str(snapshot)}]
    rows = rows[:max_rows]

    snap_path = os.path.join("datasets", f"{name}_snapshot_{ts}.jsonl")
    with open(snap_path, "w", encoding="utf-8") as f:
        for idx, row in enumerate(rows):
            f.write(json.dumps({"idx": idx, **row}, default=str) + "\n")

    meta_path = os.path.join("datasets", f"{name}_meta_{ts}.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "source": safe_source,
                "tables": tables or [],
                "query_context": query_context or {},
                "rows": len(rows),
                "snapshot_path": snap_path,
            },
            f,
            default=str,
            indent=2,
        )

    _safe_mlflow_call("log_artifact(snapshot)", mlflow.log_artifact, snap_path, artifact_path="datasets")
    _safe_mlflow_call("log_artifact(metadata)", mlflow.log_artifact, meta_path, artifact_path="datasets")
    if pd is not None and hasattr(mlflow, "log_input") and hasattr(mlflow, "data"):
        frame = pd.DataFrame([_flatten_row(r) for r in rows]) if rows else pd.DataFrame([{"note": "empty"}])
        ds = mlflow.data.from_pandas(frame, source=snap_path, name=name)
        _safe_mlflow_call("log_input", mlflow.log_input, ds, context="inference")


def ollama_chat_with_mlflow(
    *,
    client: Client,
    model: str,
    messages: list[dict[str, str]],
    options: dict[str, Any] | None = None,
    run_name: str | None = None,
    tags: dict[str, str] | None = None,
    log_dataset: bool = True,
    dataset_name: str = "ollama_messages",
    log_postgres_dataset: bool = False,
    postgres_source: dict[str, Any] | None = None,
    postgres_tables: list[dict[str, Any]] | None = None,
    postgres_query_context: dict[str, Any] | None = None,
    postgres_snapshot: Any = None,
    postgres_snapshot_max_rows: int = 200,
) -> dict[str, Any]:
    merged_options = {
        "temperature": 0.2,
        "top_p": 0.9,
        "top_k": 40,
        "num_predict": 256,
        "repeat_penalty": 1.1,
        "seed": 42,
        **(options or {}),
    }

    with _start_mlflow_run(run_name):
        if tags:
            _safe_mlflow_call("set_tags", mlflow.set_tags, tags)
        _safe_mlflow_call("log_param(ollama_model)", mlflow.log_param, "ollama_model", model)
        for k, v in merged_options.items():
            _safe_mlflow_call("log_param(options)", mlflow.log_param, f"ollama_{k}", v)

        if log_dataset:
            ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            os.makedirs("datasets", exist_ok=True)
            jsonl_path = os.path.join("datasets", f"{dataset_name}_{ts}.jsonl")
            with open(jsonl_path, "w", encoding="utf-8") as f:
                for idx, m in enumerate(messages):
                    f.write(json.dumps({"idx": idx, **m}, ensure_ascii=False) + "\n")
            _safe_mlflow_call("log_artifact(messages)", mlflow.log_artifact, jsonl_path, artifact_path="datasets")

        if log_postgres_dataset:
            _log_postgres_dataset(
                source=postgres_source or {},
                tables=postgres_tables or [],
                query_context=postgres_query_context or {},
                snapshot=postgres_snapshot,
                name="postgres_inputs",
                max_rows=postgres_snapshot_max_rows,
            )

        t0 = time.time()
        resp = client.chat(model=model, messages=messages, options=merged_options, stream=False)
        latency = round(time.time() - t0, 4)

        content = _extract_content(resp)
        stats = _extract_stats(resp)

        _safe_mlflow_call("log_metric(latency_seconds)", mlflow.log_metric, "latency_seconds", latency)
        if stats.get("prompt_eval_count") is not None:
            _safe_mlflow_call("log_metric(input_tokens)", mlflow.log_metric, "input_tokens", float(stats["prompt_eval_count"]))
        if stats.get("eval_count") is not None:
            _safe_mlflow_call("log_metric(output_tokens)", mlflow.log_metric, "output_tokens", float(stats["eval_count"]))
        for key in ("prompt_eval_duration", "eval_duration", "total_duration", "load_duration"):
            if stats.get(key) is not None:
                _safe_mlflow_call(f"log_metric({key})", mlflow.log_metric, key, float(stats[key]))

        _safe_mlflow_call("log_text(prompt)", mlflow.log_text, _safe_json(messages), artifact_file="prompt.json")
        _safe_mlflow_call("log_text(response)", mlflow.log_text, content, artifact_file="response.txt")
        return {"content": content, "stats": stats, "raw": resp.model_dump() if hasattr(resp, "model_dump") else resp}

