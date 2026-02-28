from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
from dateutil import parser
from fastapi import HTTPException

from app.schemas.summary import SummaryRequest


def safe_parse_ts(ts: Any) -> datetime | None:
    if ts is None:
        return None
    if isinstance(ts, datetime):
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    try:
        dtt = parser.isoparse(str(ts))
        return dtt if dtt.tzinfo else dtt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def floor_to_minute(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(second=0, microsecond=0)


def lookback_cutoff(hours: int) -> datetime:
    hours = max(1, min(int(hours or 3), 168))
    return datetime.now(timezone.utc) - timedelta(hours=hours)


def resolve_time_window(req: SummaryRequest) -> tuple[datetime, datetime]:
    if req.start_utc:
        since = safe_parse_ts(req.start_utc)
        if since is None:
            raise HTTPException(
                status_code=400,
                detail="Invalid start_utc. Use ISO-8601, e.g. 2025-12-22T00:00:00Z",
            )
    else:
        since = lookback_cutoff(req.lookback_hours)

    if req.end_utc:
        end_ts = safe_parse_ts(req.end_utc)
        if end_ts is None:
            raise HTTPException(
                status_code=400,
                detail="Invalid end_utc. Use ISO-8601, e.g. 2025-12-22T23:59:59Z",
            )
    else:
        end_ts = datetime.now(timezone.utc)

    if since > end_ts:
        raise HTTPException(status_code=400, detail="start_utc must be <= end_utc")
    return since, end_ts


def extend_start_for_signature(since: datetime, window_minutes: int) -> datetime:
    return floor_to_minute(since) - timedelta(minutes=max(0, int(window_minutes) - 1))


def trim_rows_to_requested_window(
    rows: list[dict[str, Any]],
    since: datetime,
    end_ts: datetime,
) -> list[dict[str, Any]]:
    since_m = floor_to_minute(since)
    end_m = floor_to_minute(end_ts)
    out: list[dict[str, Any]] = []
    for r in rows or []:
        m = safe_parse_ts(r.get("minute"))
        if not m:
            continue
        m = floor_to_minute(m)
        if since_m <= m <= end_m:
            out.append(r)
    return out


def collapse_grouped_counts_to_global(grouped: dict[str, dict[datetime, int]]) -> dict[datetime, int]:
    totals: dict[datetime, int] = defaultdict(int)
    for _, mm in (grouped or {}).items():
        for minute_dt, count in (mm or {}).items():
            if minute_dt is None:
                continue
            totals[floor_to_minute(minute_dt)] += int(count or 0)
    return dict(totals)


def _normalize_log_counts(d: dict[Any, Any] | None) -> dict[datetime, int]:
    out: dict[datetime, int] = defaultdict(int)
    for k, v in (d or {}).items():
        m = safe_parse_ts(k) if isinstance(k, str) else k
        if hasattr(m, "to_pydatetime"):
            m = m.to_pydatetime()
        if not isinstance(m, datetime):
            continue
        out[floor_to_minute(m)] += int(v or 0)
    return dict(out)


def build_incident_timeline(
    anomalies: list[dict[str, Any]],
    changes: list[dict[str, Any]],
    incidents: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    timeline: list[dict[str, Any]] = []
    for c in changes or []:
        ts = safe_parse_ts(c.get("timestamp"))
        if not ts:
            continue
        timeline.append(
            {
                "type": "change",
                "timestamp": ts.isoformat(),
                "description": c.get("description", ""),
                "asset_id": c.get("asset_id"),
                "severity": c.get("severity"),
            }
        )

    for a in anomalies or []:
        ts = safe_parse_ts(a.get("timestamp") or a.get("ts"))
        if not ts:
            continue
        timeline.append(
            {
                "type": "anomaly",
                "timestamp": ts.isoformat(),
                "metric": a.get("metric"),
                "value": a.get("value"),
                "severity": a.get("severity"),
                "instance": a.get("instance"),
                "source": a.get("source", "unknown"),
            }
        )

    for i in incidents or []:
        ts = safe_parse_ts(i.get("start_time"))
        if not ts:
            continue
        timeline.append(
            {
                "type": "incident",
                "timestamp": ts.isoformat(),
                "incident_id": i.get("incident_id"),
                "title": i.get("title"),
                "severity": i.get("severity"),
                "service_impacted": i.get("service_impacted"),
            }
        )

    timeline.sort(key=lambda x: safe_parse_ts(x["timestamp"]) or datetime.min.replace(tzinfo=timezone.utc))
    return timeline


def compute_health_failure_timeline(
    anomalies: list[dict[str, Any]],
    changes: list[dict[str, Any]],
    incidents: list[dict[str, Any]] | None,
    *,
    start: datetime,
    end: datetime,
    app_log_counts: dict[Any, Any] | None = None,
    dag_log_counts: dict[Any, Any] | None = None,
) -> list[dict[str, Any]]:
    start = floor_to_minute(start)
    end = floor_to_minute(end)
    if end < start:
        start, end = end, start

    sev_health = {"critical": 12.0, "high": 10.0, "medium": 5.0, "low": 1.0}
    sev_failure = {"critical": 14.0, "high": 10.0, "medium": 5.0, "low": 1.0}
    sev_risk = {"critical": 8.0, "high": 5.0, "medium": 1.0, "low": 0.5}

    app_log_counts = _normalize_log_counts(app_log_counts)
    dag_log_counts = _normalize_log_counts(dag_log_counts)

    deltas: dict[datetime, list[float]] = defaultdict(lambda: [0.0, 0.0, 0.0])
    counts: dict[datetime, dict[str, int]] = defaultdict(
        lambda: {"infra": 0, "app": 0, "app_logs": 0, "dag_logs": 0, "total": 0}
    )

    for a in anomalies or []:
        ts = safe_parse_ts(a.get("timestamp") or a.get("ts"))
        if not ts:
            continue
        m = floor_to_minute(ts)
        if m < start or m > end:
            continue
        sev = str(a.get("severity") or "medium").lower()
        deltas[m][0] -= sev_health.get(sev, 5.0)
        deltas[m][1] += sev_failure.get(sev, 2.0)
        deltas[m][2] += sev_risk.get(sev, 3.0)
        src = str(a.get("source") or "infra").lower()
        if src not in ("infra", "app"):
            src = "infra"
        counts[m][src] += 1
        counts[m]["total"] += 1

    for c in changes or []:
        ts = safe_parse_ts(c.get("timestamp"))
        if not ts:
            continue
        m = floor_to_minute(ts)
        if m < start or m > end:
            continue
        deltas[m][1] += 2.0
        deltas[m][2] += 5.0

    for i in incidents or []:
        ts = safe_parse_ts(i.get("start_time"))
        if not ts:
            continue
        m = floor_to_minute(ts)
        if m < start or m > end:
            continue
        sev = str(i.get("severity") or "high").lower()
        deltas[m][0] -= sev_health.get(sev, 5.0)
        deltas[m][1] += sev_failure.get(sev, 2.0)
        deltas[m][2] += sev_risk.get(sev, 3.0)

    APP_LOG_FAIL_PER_ERR = 0.15
    APP_LOG_RISK_PER_ERR = 0.10
    DAG_LOG_FAIL_PER_ERR = 0.25
    DAG_LOG_RISK_PER_ERR = 0.15
    APP_LOG_HEALTH_PER_ERR = 0.10
    DAG_LOG_HEALTH_PER_ERR = 0.05
    MAX_LOG_HEALTH_PENALTY = 30.0

    for m, cnt in app_log_counts.items():
        if m < start or m > end:
            continue
        cnt_i = int(cnt or 0)
        if cnt_i <= 0:
            continue
        counts[m]["app_logs"] += cnt_i
        counts[m]["total"] += cnt_i
        deltas[m][1] += cnt_i * APP_LOG_FAIL_PER_ERR
        deltas[m][2] += cnt_i * APP_LOG_RISK_PER_ERR
        deltas[m][0] -= min(MAX_LOG_HEALTH_PENALTY, cnt_i * APP_LOG_HEALTH_PER_ERR)

    for m, cnt in dag_log_counts.items():
        if m < start or m > end:
            continue
        cnt_i = int(cnt or 0)
        if cnt_i <= 0:
            continue
        counts[m]["dag_logs"] += cnt_i
        counts[m]["total"] += cnt_i
        deltas[m][1] += cnt_i * DAG_LOG_FAIL_PER_ERR
        deltas[m][2] += cnt_i * DAG_LOG_RISK_PER_ERR
        deltas[m][0] -= min(MAX_LOG_HEALTH_PENALTY, cnt_i * DAG_LOG_HEALTH_PER_ERR)

    out = []
    cur = start
    while cur <= end:
        d_health, d_failure, d_risk = deltas.get(cur, (0.0, 0.0, 0.0))
        cc = counts.get(cur, {"infra": 0, "app": 0, "app_logs": 0, "dag_logs": 0, "total": 0})
        out.append(
            {
                "minute": cur.isoformat(),
                "health": float(max(0.0, min(100.0, 100.0 + d_health))),
                "failure": float(max(0.0, min(100.0, d_failure))),
                "risk": float(max(0.0, min(100.0, d_risk))),
                "infra_anomalies": int(cc["infra"]),
                "app_anomalies": int(cc["app"]),
                "total_anomalies": int(cc["infra"]) + int(cc["app"]),
                "app_log_errors": int(cc["app_logs"]),
                "dag_log_errors": int(cc["dag_logs"]),
                "total_events": int(cc["total"]),
            }
        )
        cur += timedelta(minutes=1)
    return out


def clamp_score(x: float) -> int:
    return int(max(0, min(100, round(float(x)))))


def cluster_score_from_timeline(
    hf_rows: list[dict[str, Any]],
    *,
    window_minutes: int = 15,
    mode: str = "p10",
) -> int:
    if not hf_rows:
        return 100
    tail = hf_rows[-window_minutes:] if len(hf_rows) >= window_minutes else hf_rows
    vals = [float(r.get("health", 100)) for r in tail]
    if mode == "last":
        return clamp_score(vals[-1])
    if mode == "avg":
        return clamp_score(sum(vals) / max(1, len(vals)))
    if mode == "min":
        return clamp_score(min(vals))
    return clamp_score(float(np.percentile(np.array(vals, dtype=float), 10)))


def _health_symbol(v: float) -> str:
    if v >= 90:
        return "A"
    if v >= 80:
        return "B"
    if v >= 70:
        return "C"
    if v >= 60:
        return "D"
    return "E"


def _label_health_archetype(seq: list[str]) -> str:
    if not seq:
        return "UNKNOWN"
    flips = sum(seq[i] != seq[i - 1] for i in range(1, len(seq)))
    if flips >= 4:
        return "FLAPPING"
    first_rank = "ABCDE".find(seq[0])
    last_rank = "ABCDE".find(seq[-1])
    if first_rank == -1 or last_rank == -1:
        return "UNKNOWN"
    if last_rank - first_rank >= 1:
        return "UNHEALTHY_DEGRADING" if last_rank >= 2 else "HEALTHY_DEGRADING"
    if first_rank - last_rank >= 1:
        return "RECOVERED_STABLE"
    return "HEALTHY_STABLE" if last_rank <= 1 else "UNHEALTHY_STABLE"


def _label_level(v: float) -> str:
    if v < 20:
        return "Low"
    if v < 50:
        return "Medium"
    return "High"


def attach_signatures_to_timeline(
    hf_rows: list[dict[str, Any]],
    *,
    window_minutes: int = 15,
) -> list[dict[str, Any]]:
    if not hf_rows:
        return hf_rows
    rows = [dict(r) for r in hf_rows]
    for idx in range(len(rows)):
        window = rows[max(0, idx - window_minutes + 1) : idx + 1]
        hseq = [_health_symbol(float(r.get("health", 100))) for r in window]
        fseq = ["L" if float(r.get("failure", 0)) < 20 else ("M" if float(r.get("failure", 0)) < 50 else "H") for r in window]
        rseq = ["L" if float(r.get("risk", 0)) < 20 else ("M" if float(r.get("risk", 0)) < 50 else "H") for r in window]
        rows[idx]["health_sequence"] = "".join(hseq)
        rows[idx]["failure_sequence"] = "".join(fseq)
        rows[idx]["risk_sequence"] = "".join(rseq)
        rows[idx]["health_archetype"] = _label_health_archetype(hseq)
        rows[idx]["failure_archetype"] = "HIGH" if fseq and fseq[-1] == "H" else "NORMAL"
        rows[idx]["risk_archetype"] = "HIGH" if rseq and rseq[-1] == "H" else "NORMAL"
    return rows


def signature_block_from_timeline(
    hf_rows: list[dict[str, Any]],
    *,
    window_minutes: int = 15,
) -> dict[str, Any]:
    if not hf_rows:
        return {
            "signature_id": "H0",
            "health_state": "N/A",
            "confidence": 0,
            "archetypes": {},
            "sequences": {},
        }
    tail = hf_rows[-window_minutes:] if len(hf_rows) >= window_minutes else hf_rows
    health_series = [float(r.get("health", 100)) for r in tail]
    p10 = float(np.percentile(np.array(health_series, dtype=float), 10))
    health_state = ("Healthy" if p10 >= 80 else "Unhealthy") + (" Degrading" if health_series[0] - health_series[-1] >= 5 else " Stable")
    last = tail[-1]
    return {
        "signature_id": f"H-{abs(hash(last.get('health_sequence', '')))%100000}",
        "health_state": health_state,
        "confidence": max(0.0, 100.0 - min(100.0, float(sum(abs(health_series[i]-health_series[i-1]) for i in range(1, len(health_series)))))),
        "archetypes": {
            "health": last.get("health_archetype"),
            "failure": last.get("failure_archetype"),
            "risk": last.get("risk_archetype"),
        },
        "sequences": {
            "health": last.get("health_sequence"),
            "failure": last.get("failure_sequence"),
            "risk": last.get("risk_sequence"),
        },
        "health_p10": p10,
        "health_last": float(last.get("health", 100)),
        "failure_state": _label_level(float(last.get("failure", 0))),
        "risk_state": _label_level(float(last.get("risk", 0))),
        "signature_window_minutes": int(window_minutes),
        "signature_end_utc": last.get("minute"),
    }


def _sev_weight(sev: str) -> float:
    sev = (sev or "unknown").lower()
    return {"critical": 12.0, "high": 8.0, "medium": 3.0, "low": 1.0}.get(sev, 2.0)


def top_affected_metrics(
    anoms: list[dict[str, Any]],
    *,
    source: str,
    start: datetime,
    end: datetime,
    top_n: int = 5,
) -> list[dict[str, Any]]:
    start_m = floor_to_minute(start)
    end_m = floor_to_minute(end)
    agg: dict[str, dict[str, Any]] = {}
    for a in anoms or []:
        ts = safe_parse_ts(a.get("timestamp") or a.get("ts"))
        if not ts:
            continue
        m = floor_to_minute(ts)
        if m < start_m or m > end_m:
            continue
        if str(a.get("source", "")).lower() != source:
            continue
        metric = a.get("metric") or a.get("metric_name") or a.get("kpi") or "unknown_metric"
        inst = a.get("instance") or a.get("instance_name") or "unknown_instance"
        sev = str(a.get("severity") or "unknown").lower()
        if metric not in agg:
            agg[metric] = {
                "metric": metric,
                "count": 0,
                "impact": 0.0,
                "severity_breakdown": defaultdict(int),
                "instances": set(),
            }
        agg[metric]["count"] += 1
        agg[metric]["impact"] += _sev_weight(sev)
        agg[metric]["severity_breakdown"][sev] += 1
        agg[metric]["instances"].add(str(inst))

    out = list(agg.values())
    out.sort(key=lambda x: (x["impact"], x["count"]), reverse=True)
    for item in out:
        item["impact"] = round(float(item["impact"]), 2)
        item["severity_breakdown"] = dict(item["severity_breakdown"])
        item["instances"] = sorted(item["instances"])[:10]
    return out[:top_n]


def extract_metric_names(affected_metrics: list[dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    names: list[str] = []
    for metric in affected_metrics or []:
        name = metric.get("metric")
        if name and name not in seen:
            seen.add(name)
            names.append(name)
    return names


def affected_instances_from_anoms(
    anoms: list[dict[str, Any]],
    *,
    source: str,
    start: datetime,
    end: datetime,
    top_n: int = 25,
) -> list[str]:
    start_m = floor_to_minute(start)
    end_m = floor_to_minute(end)
    out = set()
    for a in anoms or []:
        if str(a.get("source", "")).lower() != source:
            continue
        ts = safe_parse_ts(a.get("timestamp") or a.get("ts"))
        if not ts:
            continue
        m = floor_to_minute(ts)
        if m < start_m or m > end_m:
            continue
        inst = a.get("instance") or a.get("instance_name")
        if inst:
            out.add(str(inst))
    return sorted(out)[:top_n]


def affected_instances_by_metric_from_anoms(
    anoms: list[dict[str, Any]],
    *,
    source: str,
    start: datetime,
    end: datetime,
) -> dict[str, list[str]]:
    start_m = floor_to_minute(start)
    end_m = floor_to_minute(end)
    per_metric: dict[str, set[str]] = defaultdict(set)
    counts: dict[str, int] = defaultdict(int)

    for a in anoms or []:
        if str(a.get("source", "")).lower() != source:
            continue
        ts = safe_parse_ts(a.get("timestamp") or a.get("ts"))
        if not ts:
            continue
        m = floor_to_minute(ts)
        if m < start_m or m > end_m:
            continue
        metric = str(a.get("metric") or a.get("metric_name") or "unknown_metric")
        inst = str(a.get("instance") or a.get("instance_name") or "unknown_instance")
        per_metric[metric].add(inst)
        counts[metric] += 1

    ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:10]
    keep = {k for k, _ in ranked}
    return {metric: sorted(per_metric[metric])[:10] for metric in keep}


def count_anoms_in_window(
    anoms: list[dict[str, Any]],
    source: str,
    start_dt: datetime,
    end_dt: datetime,
) -> int:
    start_m = floor_to_minute(start_dt)
    end_m = floor_to_minute(end_dt)
    c = 0
    for a in anoms or []:
        if str(a.get("source", "")).lower() != source:
            continue
        ts = safe_parse_ts(a.get("timestamp") or a.get("ts"))
        if not ts:
            continue
        m = floor_to_minute(ts)
        if start_m <= m <= end_m:
            c += 1
    return c


def count_logs_in_window(log_counts: dict[Any, Any], start_dt: datetime, end_dt: datetime) -> int:
    start_m = floor_to_minute(start_dt)
    end_m = floor_to_minute(end_dt)
    total = 0
    for m, c in _normalize_log_counts(log_counts).items():
        if start_m <= m <= end_m:
            total += int(c or 0)
    return total


def logs_affected_metrics(
    app_log_counts: dict[Any, Any],
    dag_log_counts: dict[Any, Any],
    *,
    start: datetime,
    end: datetime,
) -> tuple[list[dict[str, Any]], int, int]:
    app_total = count_logs_in_window(app_log_counts, start, end)
    dag_total = count_logs_in_window(dag_log_counts, start, end)
    out: list[dict[str, Any]] = []
    if app_total > 0:
        out.append({"metric": "app_error_logs", "count": app_total})
    if dag_total > 0:
        out.append({"metric": "dag_error_logs", "count": dag_total})
    return out, app_total, dag_total


def compute_component_health_scores(
    infra_anoms: list[dict[str, Any]],
    app_anoms: list[dict[str, Any]],
    app_log_counts: dict[Any, Any],
    dag_log_counts: dict[Any, Any],
    *,
    since: datetime,
    end_ts: datetime,
    culprit_window_minutes: int = 15,
) -> dict[str, Any]:
    dip_start = max(since, end_ts - timedelta(minutes=culprit_window_minutes))
    dip_end = end_ts
    infra_hf = compute_health_failure_timeline(
        infra_anoms, [], None, start=since, end=end_ts, app_log_counts={}, dag_log_counts={}
    )
    app_hf = compute_health_failure_timeline(
        app_anoms, [], None, start=since, end=end_ts, app_log_counts={}, dag_log_counts={}
    )
    logs_hf = compute_health_failure_timeline(
        [], [], None, start=since, end=end_ts, app_log_counts=app_log_counts, dag_log_counts=dag_log_counts
    )
    combined_hf = compute_health_failure_timeline(
        infra_anoms + app_anoms,
        [],
        None,
        start=since,
        end=end_ts,
        app_log_counts=app_log_counts,
        dag_log_counts=dag_log_counts,
    )
    infra_affected = top_affected_metrics(infra_anoms, source="infra", start=dip_start, end=dip_end, top_n=5)
    app_affected = top_affected_metrics(app_anoms, source="app", start=dip_start, end=dip_end, top_n=5)
    logs_affected, _, _ = logs_affected_metrics(app_log_counts, dag_log_counts, start=dip_start, end=dip_end)

    return {
        "health_score": cluster_score_from_timeline(combined_hf, window_minutes=culprit_window_minutes, mode="p10"),
        "infra_metrics": {
            "health_score": cluster_score_from_timeline(infra_hf, window_minutes=culprit_window_minutes, mode="p10"),
            "affected_metrics": infra_affected,
            "affected_metric_names": extract_metric_names(infra_affected),
            "affected_instances": affected_instances_from_anoms(infra_anoms, source="infra", start=dip_start, end=dip_end),
            "affected_instances_by_metric": affected_instances_by_metric_from_anoms(infra_anoms, source="infra", start=dip_start, end=dip_end),
        },
        "app_metrics": {
            "health_score": cluster_score_from_timeline(app_hf, window_minutes=culprit_window_minutes, mode="p10"),
            "affected_metrics": app_affected,
            "affected_metric_names": extract_metric_names(app_affected),
            "affected_instances": affected_instances_from_anoms(app_anoms, source="app", start=dip_start, end=dip_end),
            "affected_instances_by_metric": affected_instances_by_metric_from_anoms(app_anoms, source="app", start=dip_start, end=dip_end),
        },
        "logs_metrics": {
            "health_score": cluster_score_from_timeline(logs_hf, window_minutes=culprit_window_minutes, mode="p10"),
            "affected_metrics": logs_affected,
            "affected_metric_names": extract_metric_names(logs_affected),
            "affected_instances": [],
            "affected_instances_by_metric": {},
        },
        "counts": {
            "infra_anomalies": count_anoms_in_window(infra_anoms, "infra", dip_start, dip_end),
            "app_anomalies": count_anoms_in_window(app_anoms, "app", dip_start, dip_end),
            "app_error_logs": count_logs_in_window(app_log_counts, dip_start, dip_end),
            "dag_error_logs": count_logs_in_window(dag_log_counts, dip_start, dip_end),
            "score_mode": "p10",
            "culprit_window_minutes": int(culprit_window_minutes),
            "culprit_start_utc": dip_start.isoformat(),
            "culprit_end_utc": dip_end.isoformat(),
        },
    }


def severity_breakdown(anomalies: list[dict[str, Any]]) -> dict[str, int]:
    out: dict[str, int] = defaultdict(int)
    for a in anomalies or []:
        sev = str(a.get("severity") or "unknown").lower()
        out[sev] += 1
    return dict(out)


def top_metrics_causing_dip(
    anoms: list[dict[str, Any]],
    *,
    source: str,
    start: datetime,
    end: datetime,
    top_n: int = 8,
) -> list[dict[str, Any]]:
    start_m = floor_to_minute(start)
    end_m = floor_to_minute(end)
    impact_by_metric: dict[str, float] = defaultdict(float)
    count_by_metric: dict[str, int] = defaultdict(int)
    sev_by_metric: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for a in anoms or []:
        if str(a.get("source", "")).lower() != source:
            continue
        ts = safe_parse_ts(a.get("timestamp") or a.get("ts"))
        if not ts:
            continue
        m = floor_to_minute(ts)
        if m < start_m or m > end_m:
            continue
        metric = a.get("metric") or a.get("metric_name") or "unknown_metric"
        sev = str(a.get("severity") or "unknown").lower()
        impact_by_metric[str(metric)] += _sev_weight(sev)
        count_by_metric[str(metric)] += 1
        sev_by_metric[str(metric)][sev] += 1
    ranked = sorted(impact_by_metric.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
    return [
        {
            "metric": metric,
            "impact": round(float(impact), 2),
            "count": int(count_by_metric[metric]),
            "severity_breakdown": dict(sev_by_metric[metric]),
        }
        for metric, impact in ranked
    ]

