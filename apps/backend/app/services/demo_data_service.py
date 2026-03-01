from __future__ import annotations

import hashlib
import math
from datetime import datetime, timedelta, timezone
from typing import Any

from app.domain.health import (
    attach_signatures_to_timeline,
    cluster_score_from_timeline,
    extend_start_for_signature,
    resolve_time_window,
    signature_block_from_timeline,
    trim_rows_to_requested_window,
)
from app.schemas.summary import SummaryRequest


def _seed(text: str) -> int:
    return int(hashlib.md5(text.encode("utf-8")).hexdigest()[:8], 16)


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


class DemoDataService:
    def _build_asset_timeline(
        self,
        *,
        keyword: str,
        start: datetime,
        end: datetime,
        mode: str,
    ) -> list[dict[str, Any]]:
        assets = self._build_mock_assets(keyword)
        timeline: list[dict[str, Any]] = []
        for idx, asset in enumerate(assets):
            seed = _seed(f"{asset['asset_id']}:{mode}")
            cur = start.replace(second=0, microsecond=0, tzinfo=timezone.utc)
            health = 96.0 - (idx * 1.7)
            while cur <= end:
                drift = math.sin((cur.minute + seed % 11) / 9.0) * 2.3
                penalty = 0.0
                if mode == "combined":
                    penalty = 4.0 if (cur.minute + idx) % 17 == 0 else 0.8
                elif mode == "infra":
                    penalty = 3.2 if (cur.minute + idx) % 19 == 0 else 0.5
                elif mode == "app":
                    penalty = 3.6 if (cur.minute + idx) % 13 == 0 else 0.6

                health = max(35.0, min(100.0, 0.35 * (100.0 - penalty + drift) + 0.65 * health))
                app_logs = int(max(0, round((75.0 - health) * 0.8)))
                dag_logs = int(max(0, round((72.0 - health) * 0.6)))
                contributors = [
                    {
                        "metric": "queue_depth" if mode != "infra" else "cpu_usage",
                        "value": round(100.0 - health, 2),
                        "severity": "high" if health < 70 else ("medium" if health < 82 else "low"),
                        "count": 1 + int(health < 75),
                        "instance": asset["asset_id"],
                        "asset_id": asset["asset_id"],
                    }
                ]
                timeline.append(
                    {
                        "asset_id": asset["asset_id"],
                        "host_ip": asset.get("ip_address"),
                        "minute": cur.isoformat(),
                        "health_score": round(float(health), 2),
                        "impact_total": round(float(100.0 - health), 2),
                        "contributors": contributors,
                        "app_log_errors": app_logs if mode in ("combined", "app") else 0,
                        "dag_log_errors": dag_logs if mode in ("combined", "app") else 0,
                    }
                )
                cur += timedelta(minutes=1)
        return timeline

    def _build_timeline(
        self,
        *,
        keyword: str,
        start: datetime,
        end: datetime,
        mode: str,
    ) -> list[dict[str, Any]]:
        seed = _seed(f"{keyword}:{mode}")
        cur = start.replace(second=0, microsecond=0, tzinfo=timezone.utc)
        end = end.replace(second=0, microsecond=0, tzinfo=timezone.utc)

        out: list[dict[str, Any]] = []
        idx = 0
        while cur <= end:
            trend = idx / max(1, int((end - start).total_seconds() // 60))
            wave = math.sin((idx + (seed % 17)) / 7.0) * 5.0
            pulse = 7.0 if (idx + seed) % 23 == 0 else 0.0

            mode_bias = {
                "combined": -4.0,
                "infra": -2.5,
                "app": -3.2,
            }.get(mode, -2.0)

            health = 92.0 + mode_bias - (trend * 12.0) + wave - pulse
            health = _clamp(health, 48.0, 99.0)

            infra = 0
            app = 0
            app_logs = 0
            dag_logs = 0

            if mode in ("combined", "infra"):
                infra = max(0, int(round((78.0 - health) / 9.0 + (1 if idx % 13 == 0 else 0))))
            if mode in ("combined", "app"):
                app = max(0, int(round((74.0 - health) / 10.0 + (1 if idx % 17 == 0 else 0))))
                app_logs = max(0, int(round((72.0 - health) * 0.8 + (2 if idx % 11 == 0 else 0))))
                dag_logs = max(0, int(round((70.0 - health) * 0.6 + (1 if idx % 19 == 0 else 0))))

            failure = _clamp((100.0 - health) * 1.1 + (infra * 1.2) + (app * 1.0), 0.0, 100.0)
            risk = _clamp((100.0 - health) * 0.9 + (infra * 0.8) + (app * 0.8), 0.0, 100.0)

            out.append(
                {
                    "minute": cur.isoformat(),
                    "health": round(float(health), 2),
                    "failure": round(float(failure), 2),
                    "risk": round(float(risk), 2),
                    "infra_anomalies": int(infra),
                    "app_anomalies": int(app),
                    "total_anomalies": int(infra + app),
                    "app_log_errors": int(app_logs),
                    "dag_log_errors": int(dag_logs),
                    "total_events": int(infra + app + app_logs + dag_logs),
                }
            )
            cur += timedelta(minutes=1)
            idx += 1

        return out

    def _build_rca_rows(self, keyword: str) -> list[dict[str, Any]]:
        base = [
            ("cpu_usage", "airflow-scheduler-1", 14),
            ("queue_depth", "rabbitmq-1", 12),
            ("task_failures", "airflow-worker-2", 11),
            ("dag_runtime", "airflow-web-1", 9),
            ("memory_pressure", "airflow-worker-1", 8),
        ]
        rows: list[dict[str, Any]] = []
        for metric, asset_id, count in base:
            rows.append(
                {
                    "metric": metric,
                    "asset_id": asset_id,
                    "anomaly_count": count,
                    "summary": f"{metric} increased around {keyword} activity window.",
                    "recommendation": f"Scale or tune {asset_id}, then validate {metric} recovery.",
                }
            )
        return rows

    def _build_mock_assets(self, keyword: str) -> list[dict[str, Any]]:
        return [
            {"asset_id": "airflow-scheduler-1", "name": f"{keyword}-scheduler", "ip_address": "10.0.1.10"},
            {"asset_id": "airflow-worker-1", "name": f"{keyword}-worker-1", "ip_address": "10.0.1.21"},
            {"asset_id": "airflow-worker-2", "name": f"{keyword}-worker-2", "ip_address": "10.0.1.22"},
            {"asset_id": "rabbitmq-1", "name": f"{keyword}-rabbitmq", "ip_address": "10.0.2.15"},
            {"asset_id": "airflow-web-1", "name": f"{keyword}-web", "ip_address": "10.0.1.30"},
        ]

    def get_combined_summary(self, req: SummaryRequest) -> dict[str, Any]:
        keyword = req.keyword.strip()
        since_req, end_ts = resolve_time_window(req)
        sig_window_min = 15
        since_calc = extend_start_for_signature(since_req, sig_window_min)

        combined_hf = self._build_timeline(keyword=keyword, start=since_calc, end=end_ts, mode="combined")
        infra_hf = self._build_timeline(keyword=keyword, start=since_calc, end=end_ts, mode="infra")
        app_hf = self._build_timeline(keyword=keyword, start=since_calc, end=end_ts, mode="app")
        combined_asset_timeline = self._build_asset_timeline(keyword=keyword, start=since_calc, end=end_ts, mode="combined")
        infra_asset_timeline = self._build_asset_timeline(keyword=keyword, start=since_calc, end=end_ts, mode="infra")
        app_asset_timeline = self._build_asset_timeline(keyword=keyword, start=since_calc, end=end_ts, mode="app")

        combined_hf = attach_signatures_to_timeline(combined_hf, window_minutes=sig_window_min)
        infra_hf = attach_signatures_to_timeline(infra_hf, window_minutes=sig_window_min)
        app_hf = attach_signatures_to_timeline(app_hf, window_minutes=sig_window_min)

        combined_trim = trim_rows_to_requested_window(combined_hf, since_req, end_ts)
        infra_trim = trim_rows_to_requested_window(infra_hf, since_req, end_ts)
        app_trim = trim_rows_to_requested_window(app_hf, since_req, end_ts)

        total_infra = int(sum(int(r.get("infra_anomalies", 0)) for r in combined_trim))
        total_app = int(sum(int(r.get("app_anomalies", 0)) for r in combined_trim))
        app_logs = int(sum(int(r.get("app_log_errors", 0)) for r in combined_trim))
        dag_logs = int(sum(int(r.get("dag_log_errors", 0)) for r in combined_trim))

        incident_ts = end_ts - timedelta(minutes=22)
        changes = [
            {
                "timestamp": (end_ts - timedelta(minutes=40)).isoformat(),
                "asset_id": "airflow-scheduler-1",
                "change_type": "config_update",
                "severity": "medium",
                "description": "Scheduler pool size adjusted for queue throughput.",
            },
            {
                "timestamp": (end_ts - timedelta(minutes=15)).isoformat(),
                "asset_id": "rabbitmq-1",
                "change_type": "deployment",
                "severity": "high",
                "description": "RabbitMQ plugin rollout triggered transient pressure.",
            },
        ]
        incident_timeline = [
            {
                "type": "change",
                "timestamp": changes[0]["timestamp"],
                "description": changes[0]["description"],
                "asset_id": changes[0]["asset_id"],
                "severity": changes[0]["severity"],
            },
            {
                "type": "anomaly",
                "timestamp": (incident_ts - timedelta(minutes=5)).isoformat(),
                "metric": "queue_depth",
                "value": 1280,
                "severity": "high",
                "instance": "rabbitmq-1",
                "source": "app",
            },
            {
                "type": "incident",
                "timestamp": incident_ts.isoformat(),
                "incident_id": "INC-DEMO-101",
                "title": "Demo incident: processing delay spike",
                "severity": "high",
                "service_impacted": keyword,
            },
        ]

        return {
            "keyword": keyword,
            "lookback_hours": req.lookback_hours,
            "start_utc": req.start_utc,
            "end_utc": req.end_utc,
            "since_utc": since_calc.isoformat(),
            "until_utc": end_ts.isoformat(),
            "assets": self._build_mock_assets(keyword),
            "changes": changes,
            "relationships": [
                {"parent_asset_id": "airflow-scheduler-1", "child_asset_id": "rabbitmq-1", "relationship_type": "depends_on"}
            ],
            "infra_anomalies": [],
            "app_anomalies": [],
            "anomalies": [],
            "incidents": [
                {
                    "incident_id": "INC-DEMO-101",
                    "start_time": incident_ts.isoformat(),
                    "end_time": None,
                    "severity": "high",
                    "service_impacted": keyword,
                    "title": "Demo incident: processing delay spike",
                }
            ],
            "infra_anomaly_count": total_infra,
            "app_anomaly_count": total_app,
            "anomaly_count": total_infra + total_app,
            "infra_top_metrics_causing_dip": [
                {"metric": "cpu_usage", "impact": 42.0, "count": 8, "severity_breakdown": {"high": 4, "medium": 4}},
                {"metric": "memory_pressure", "impact": 28.0, "count": 6, "severity_breakdown": {"medium": 6}},
            ],
            "infra_affected_metrics": [
                {"metric": "cpu_usage", "count": 8, "impact": 42.0, "severity_breakdown": {"high": 4, "medium": 4}, "instances": ["airflow-worker-1", "airflow-worker-2"]}
            ],
            "infra_only": {
                "cluster_health": cluster_score_from_timeline(infra_trim, window_minutes=sig_window_min, mode="p10"),
                "health_failure_timeline": infra_trim,
                "asset_health_timeline": infra_asset_timeline,
            },
            "app_only": {
                "cluster_health": cluster_score_from_timeline(app_trim, window_minutes=sig_window_min, mode="p10"),
                "health_failure_timeline": app_trim,
                "asset_health_timeline": app_asset_timeline,
            },
            "app_log_error_count": app_logs,
            "dag_log_error_count": dag_logs,
            "severity_breakdown": {
                "high": max(1, total_infra // 3),
                "medium": max(2, total_app // 3),
                "low": max(1, (total_infra + total_app) // 6),
            },
            "cluster_health": cluster_score_from_timeline(combined_trim, window_minutes=sig_window_min, mode="p10"),
            "incident_timeline": incident_timeline,
            "health_failure_timeline": combined_trim,
            "asset_health_timeline": combined_asset_timeline,
            "health_signature": signature_block_from_timeline(combined_trim, window_minutes=sig_window_min),
            "summary": "Demo mode summary generated from synthetic but realistic platform data.",
            "rca": self._build_rca_rows(keyword),
            "demo_mode": True,
        }

    def list_incidents(
        self,
        *,
        team_name: str | None,
        keyword: str | None,
        since: datetime,
        end: datetime,
        include_resolved: bool,
    ) -> list[dict[str, Any]]:
        base_time = end - timedelta(minutes=80)
        rows = [
            {
                "incident_id": "INC-DEMO-201",
                "title": "Airflow scheduler lag exceeded SLO",
                "description": "Task queue latency crossed threshold and impacted SLA jobs.",
                "severity": "high",
                "status": "open",
                "service_impacted": keyword or "airflow",
                "team_name": team_name,
                "start_time": (base_time + timedelta(minutes=5)).isoformat(),
                "end_time": None,
                "root_cause": None,
            },
            {
                "incident_id": "INC-DEMO-202",
                "title": "RabbitMQ queue depth spike",
                "description": "Queue depth rapidly increased after deployment update.",
                "severity": "medium",
                "status": "open",
                "service_impacted": keyword or "rabbitmq",
                "team_name": team_name,
                "start_time": (base_time + timedelta(minutes=25)).isoformat(),
                "end_time": None,
                "root_cause": None,
            },
            {
                "incident_id": "INC-DEMO-203",
                "title": "Worker memory pressure recovered",
                "description": "Worker pod memory increased during batch but recovered.",
                "severity": "low",
                "status": "resolved",
                "service_impacted": keyword or "airflow-worker",
                "team_name": team_name,
                "start_time": (base_time - timedelta(minutes=30)).isoformat(),
                "end_time": (base_time - timedelta(minutes=5)).isoformat(),
                "root_cause": "Burst workload",
            },
        ]
        filtered = []
        for row in rows:
            st = datetime.fromisoformat(row["start_time"]).astimezone(timezone.utc)
            if st < since or st > end:
                continue
            if not include_resolved and str(row.get("status", "")).lower() in {"resolved", "closed"}:
                continue
            filtered.append(row)
        return filtered

    def get_cluster_health(self, req: SummaryRequest) -> dict[str, Any]:
        summary = self.get_combined_summary(req)
        timeline = summary["health_failure_timeline"]
        sig_window_min = 15
        health_score = cluster_score_from_timeline(timeline, window_minutes=sig_window_min, mode="p10")
        last = timeline[-1] if timeline else None

        infra_score = summary["infra_only"]["cluster_health"]
        app_score = summary["app_only"]["cluster_health"]
        logs_score = int(round((infra_score * 0.35) + (app_score * 0.45) + 10))

        component_stub = {
            "health_score": infra_score,
            "affected_metrics": [
                {"metric": "queue_depth", "count": 12, "impact": 36.0, "severity_breakdown": {"high": 7, "medium": 5}, "instances": ["rabbitmq-1"]}
            ],
            "affected_metric_names": ["queue_depth"],
            "affected_instances": ["rabbitmq-1", "airflow-scheduler-1"],
            "affected_instances_by_metric": {"queue_depth": ["rabbitmq-1"]},
        }

        return {
            "keyword": summary["keyword"],
            "since_utc": summary["since_utc"],
            "until_utc": summary["until_utc"],
            "health_score": health_score,
            "infra_metrics": component_stub,
            "app_metrics": {**component_stub, "health_score": app_score, "affected_metric_names": ["task_failures"]},
            "logs_metrics": {**component_stub, "health_score": logs_score, "affected_metric_names": ["app_error_logs"]},
            "counts": {
                "infra_anomalies": summary["infra_anomaly_count"],
                "app_anomalies": summary["app_anomaly_count"],
                "app_error_logs": summary["app_log_error_count"],
                "dag_error_logs": summary["dag_log_error_count"],
                "score_mode": "p10",
                "culprit_window_minutes": sig_window_min,
            },
            "health_signature": signature_block_from_timeline(timeline, window_minutes=sig_window_min),
            "health_failure_last": last,
            "health_score_window": health_score,
            "health_archetype_last": (last or {}).get("health_archetype"),
            "health_sequence_last": (last or {}).get("health_sequence"),
            "health_failure_timeline": timeline,
            "asset_health_timeline": summary.get("asset_health_timeline", []),
            "infra_only": summary.get("infra_only", {}),
            "app_only": summary.get("app_only", {}),
            "debug": {"demo_mode": True},
        }

    def query_logs(self, *, keyword: str, start: datetime, end: datetime, group_by_host_ip: bool) -> dict[str, Any]:
        hosts = ["10.0.1.10", "10.0.1.21", "10.0.2.15"]
        services = ["airflow-scheduler-log", "airflow-worker-log", "rabbitmq-log"]

        if group_by_host_ip:
            rows = []
            cur = start
            while cur <= end:
                cur += timedelta(minutes=5)
            for idx, host in enumerate(hosts):
                minute_counts = {}
                cur = start
                step = 0
                while cur <= end:
                    minute_counts[cur.isoformat()] = int(max(0, round(2 + math.sin((step + idx) / 3.0) * 2)))
                    cur += timedelta(minutes=5)
                    step += 1
                rows.append({"host_ip": host, "minute_counts": minute_counts})
            return {"rows": rows, "total": len(rows)}

        rows: list[dict[str, Any]] = []
        cur = start
        i = 0
        while cur <= end and i < 240:
            host = hosts[i % len(hosts)]
            svc = services[i % len(services)]
            rows.append(
                {
                    "timestamp": cur.isoformat(),
                    "host_ip": host,
                    "service": svc,
                    "filename": f"/var/log/{svc}/{keyword or 'demo'}-{i % 7}.log",
                    "log": f"[ERROR] {keyword or 'demo'} pipeline latency above threshold on {svc} (event={i}).",
                }
            )
            cur += timedelta(seconds=45)
            i += 1
        return {"rows": rows, "total": len(rows)}

    def topology_graph(self, keyword: str, region_filter: list[str] | None = None) -> dict[str, Any]:
        region = (region_filter or ["us-west-2"])[0]
        nodes = [
            {"id": f"{keyword}-env-prod", "label": "Environment: prod"},
            {"id": f"{keyword}-scheduler", "label": "EC2: scheduler"},
            {"id": f"{keyword}-worker-1", "label": "EC2: worker-1"},
            {"id": f"{keyword}-worker-2", "label": "EC2: worker-2"},
            {"id": f"{keyword}-rabbitmq", "label": "EC2: rabbitmq"},
            {"id": f"{keyword}-subnet-a", "label": "Subnet: app-a"},
            {"id": f"{keyword}-vpc", "label": "VPC: main"},
            {"id": region, "label": f"Region: {region}"},
        ]
        edges = [
            {"id": "e1", "source": f"{keyword}-scheduler", "target": f"{keyword}-subnet-a", "type": "BELONGS_TO"},
            {"id": "e2", "source": f"{keyword}-worker-1", "target": f"{keyword}-subnet-a", "type": "BELONGS_TO"},
            {"id": "e3", "source": f"{keyword}-worker-2", "target": f"{keyword}-subnet-a", "type": "BELONGS_TO"},
            {"id": "e4", "source": f"{keyword}-rabbitmq", "target": f"{keyword}-subnet-a", "type": "BELONGS_TO"},
            {"id": "e5", "source": f"{keyword}-subnet-a", "target": f"{keyword}-vpc", "type": "PART_OF"},
            {"id": "e6", "source": f"{keyword}-vpc", "target": region, "type": "LOCATED_IN"},
            {"id": "e7", "source": f"{keyword}-scheduler", "target": f"{keyword}-env-prod", "type": "RUNS_IN"},
            {"id": "e8", "source": f"{keyword}-worker-1", "target": f"{keyword}-env-prod", "type": "RUNS_IN"},
            {"id": "e9", "source": f"{keyword}-worker-2", "target": f"{keyword}-env-prod", "type": "RUNS_IN"},
        ]
        return {
            "nodes": nodes,
            "edges": edges,
            "stats": {"nodes": len(nodes), "edges": len(edges), "instances": 4},
        }

    def demo_job_result(self, keyword: str, context: dict[str, Any]) -> dict[str, Any]:
        return {
            "keyword": keyword,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "summary": (
                f"Demo RCA for {keyword}: observed burst in queue depth and task failures. "
                "Scale workers, validate scheduler throughput, and monitor error logs for 15 minutes."
            ),
            "context": context,
            "mode": "demo",
        }

