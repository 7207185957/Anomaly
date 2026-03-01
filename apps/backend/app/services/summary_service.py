from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Any

from app.domain.health import (
    attach_signatures_to_timeline,
    build_incident_timeline,
    cluster_score_from_timeline,
    collapse_grouped_counts_to_global,
    compute_component_health_scores,
    compute_asset_health_statistical_with_contributors,
    compute_health_failure_timeline,
    extend_start_for_signature,
    resolve_time_window,
    severity_breakdown,
    signature_block_from_timeline,
    top_affected_metrics,
    top_metrics_causing_dip,
    trim_rows_to_requested_window,
)
from app.core.config import get_settings
from app.repositories.postgres_repository import PostgresRepository
from app.schemas.summary import SummaryRequest
from app.services.demo_data_service import DemoDataService
from app.services.llm_service import LlmService
from app.services.loki_service import LokiService


Q_DAG = '{job="promtail", service="airflow-dag-log"} |= "error" !~ "py:109.*WARNING"'
Q_APP = '{job="promtail", service=~"rabbitmq-log|airflow-scheduler-log"} |= "error" !~ "py:109.*WARNING"'


class SummaryService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.demo = DemoDataService()
        if self.settings.demo_mode:
            self.pg = None
            self.loki = None
            self.llm = None
            return
        self.pg = PostgresRepository()
        self.loki = LokiService()
        self.llm = LlmService()

    @staticmethod
    def _build_pg_lineage(
        keyword: str,
        assets: list[dict[str, Any]],
        changes: list[dict[str, Any]],
        relationships: list[dict[str, Any]],
        anomalies: list[dict[str, Any]],
        incidents: list[dict[str, Any]],
    ) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
        pg_source = {"kind": "postgres"}
        pg_tables = [
            {"schema": "public", "table": "cmdb_assets", "rows": len(assets), "query_name": "fetch_assets"},
            {"schema": "public", "table": "cmdb_changes", "rows": len(changes), "query_name": "fetch_changes"},
            {"schema": "public", "table": "cmdb_relationships", "rows": len(relationships), "query_name": "fetch_relationships"},
            {"schema": "public", "table": "infra/app_metrics", "rows": len(anomalies), "query_name": "fetch_anomalies"},
            {"schema": "public", "table": "incidents", "rows": len(incidents), "query_name": "fetch_incidents"},
        ]
        query_ctx = {"keyword": keyword, "extracted_at_utc": datetime.now(timezone.utc).isoformat()}
        snapshot = {
            "assets": assets,
            "changes": changes,
            "relationships": relationships,
            "anomalies": anomalies[:5000],
            "incidents": incidents,
        }
        return pg_source, pg_tables, query_ctx, snapshot

    def get_combined_summary(self, req: SummaryRequest) -> dict[str, Any]:
        if self.settings.demo_mode:
            return self.demo.get_combined_summary(req)

        keyword = req.keyword.strip()
        since_req, end_ts = resolve_time_window(req)
        sig_window_min = 15
        since_calc = extend_start_for_signature(since_req, sig_window_min)

        assets = self.pg.fetch_assets(keyword)
        asset_ids = [a["asset_id"] for a in assets if a.get("asset_id")]

        with ThreadPoolExecutor(max_workers=12) as ex:
            f_changes = ex.submit(self.pg.fetch_changes, asset_ids, since_calc, end_ts)
            f_relationships = ex.submit(self.pg.fetch_relationships, asset_ids)
            f_infra = ex.submit(self.pg.fetch_infra_anomalies, asset_ids, since_calc, end_ts)
            f_app = ex.submit(self.pg.fetch_app_anomalies, asset_ids, since_calc, end_ts)
            f_incidents = ex.submit(
                self.pg.fetch_open_incidents,
                team_name=self.settings.incident_team_name,
                keyword=keyword,
                since_ts=since_calc,
                until_ts=end_ts,
                include_resolved=False,
            )
            f_app_logs_by_host = ex.submit(self.loki.query_count_per_minute_by_host_ip, logql=Q_APP, start_dt=since_calc, end_dt=end_ts)
            f_dag_logs_by_host = ex.submit(self.loki.query_count_per_minute_by_host_ip, logql=Q_DAG, start_dt=since_calc, end_dt=end_ts)

            changes = f_changes.result() or []
            relationships = f_relationships.result() or []
            infra_anoms = f_infra.result() or []
            app_anoms = f_app.result() or []
            incidents = f_incidents.result() or []
            app_logs_by_host = f_app_logs_by_host.result() or {}
            dag_logs_by_host = f_dag_logs_by_host.result() or {}

        app_log_counts = collapse_grouped_counts_to_global(app_logs_by_host)
        dag_log_counts = collapse_grouped_counts_to_global(dag_logs_by_host)
        combined_anoms = (infra_anoms or []) + (app_anoms or [])

        with ThreadPoolExecutor(max_workers=8) as ex:
            f_timeline = ex.submit(build_incident_timeline, combined_anoms, changes, incidents)
            f_combined_hf = ex.submit(
                compute_health_failure_timeline,
                combined_anoms,
                changes,
                incidents,
                start=since_calc,
                end=end_ts,
                app_log_counts=app_log_counts,
                dag_log_counts=dag_log_counts,
            )
            f_infra_hf = ex.submit(
                compute_health_failure_timeline,
                infra_anoms,
                changes,
                incidents,
                start=since_calc,
                end=end_ts,
                app_log_counts={},
                dag_log_counts={},
            )
            f_app_hf = ex.submit(
                compute_health_failure_timeline,
                app_anoms,
                changes,
                incidents,
                start=since_calc,
                end=end_ts,
                app_log_counts=app_log_counts,
                dag_log_counts=dag_log_counts,
            )

            timeline = f_timeline.result() or []
            combined_hf = f_combined_hf.result() or []
            infra_hf = f_infra_hf.result() or []
            app_hf = f_app_hf.result() or []

        combined_hf = attach_signatures_to_timeline(combined_hf, window_minutes=sig_window_min)
        infra_hf = attach_signatures_to_timeline(infra_hf, window_minutes=sig_window_min)
        app_hf = attach_signatures_to_timeline(app_hf, window_minutes=sig_window_min)

        combined_trim = trim_rows_to_requested_window(combined_hf, since_req, end_ts)
        infra_trim = trim_rows_to_requested_window(infra_hf, since_req, end_ts)
        app_trim = trim_rows_to_requested_window(app_hf, since_req, end_ts)

        dip_start = max(since_req, end_ts - timedelta(minutes=15))
        dip_end = end_ts
        infra_top_metrics = top_metrics_causing_dip(
            infra_anoms,
            source="infra",
            start=dip_start,
            end=dip_end,
            top_n=8,
        )
        infra_affected_metrics = top_affected_metrics(
            infra_anoms,
            source="infra",
            start=dip_start,
            end=dip_end,
            top_n=8,
        )

        pg_source, pg_tables, pg_query_ctx, pg_snapshot = self._build_pg_lineage(
            keyword, assets, changes, relationships, combined_anoms, incidents
        )
        rca = self.llm.summarize_top_anomalies(
            keyword=keyword,
            assets=assets,
            anomalies=combined_anoms,
            pg_source=pg_source,
            pg_tables=pg_tables,
            pg_query_ctx=pg_query_ctx,
            pg_snapshot=pg_snapshot,
        )

        asset_health_timeline = compute_asset_health_statistical_with_contributors(
            assets,
            combined_anoms,
            app_log_counts_by_host_ip=app_logs_by_host,
            dag_log_counts_by_host_ip=dag_logs_by_host,
            start=since_calc,
            end=end_ts,
            alpha=0.30,
            top_n=3,
        )
        asset_health_timeline_infra = compute_asset_health_statistical_with_contributors(
            assets,
            infra_anoms,
            app_log_counts_by_host_ip={},
            dag_log_counts_by_host_ip={},
            start=since_calc,
            end=end_ts,
            alpha=0.30,
            top_n=3,
        )
        asset_health_timeline_app = compute_asset_health_statistical_with_contributors(
            assets,
            app_anoms,
            app_log_counts_by_host_ip=app_logs_by_host,
            dag_log_counts_by_host_ip=dag_logs_by_host,
            start=since_calc,
            end=end_ts,
            alpha=0.30,
            top_n=3,
        )

        return {
            "keyword": keyword,
            "lookback_hours": req.lookback_hours,
            "start_utc": req.start_utc,
            "end_utc": req.end_utc,
            "since_utc": since_calc.isoformat(),
            "until_utc": end_ts.isoformat(),
            "assets": assets,
            "changes": changes,
            "relationships": relationships,
            "infra_anomalies": infra_anoms,
            "app_anomalies": app_anoms,
            "anomalies": combined_anoms,
            "incidents": incidents,
            "infra_anomaly_count": len(infra_anoms),
            "app_anomaly_count": len(app_anoms),
            "anomaly_count": len(combined_anoms),
            "infra_top_metrics_causing_dip": infra_top_metrics,
            "infra_affected_metrics": infra_affected_metrics,
            "infra_only": {
                "cluster_health": cluster_score_from_timeline(infra_trim, window_minutes=sig_window_min, mode="p10"),
                "health_failure_timeline": infra_trim,
                "asset_health_timeline": asset_health_timeline_infra,
            },
            "app_only": {
                "cluster_health": cluster_score_from_timeline(app_trim, window_minutes=sig_window_min, mode="p10"),
                "health_failure_timeline": app_trim,
                "asset_health_timeline": asset_health_timeline_app,
            },
            "app_log_error_count": int(sum(app_log_counts.values())) if app_log_counts else 0,
            "dag_log_error_count": int(sum(dag_log_counts.values())) if dag_log_counts else 0,
            "severity_breakdown": severity_breakdown(combined_anoms),
            "cluster_health": cluster_score_from_timeline(combined_trim, window_minutes=sig_window_min, mode="p10"),
            "incident_timeline": timeline,
            "health_failure_timeline": combined_trim,
            "asset_health_timeline": asset_health_timeline,
            "health_signature": signature_block_from_timeline(combined_trim, window_minutes=sig_window_min),
            "summary": "",
            "rca": rca,
        }

    def get_cluster_health(self, req: SummaryRequest) -> dict[str, Any]:
        if self.settings.demo_mode:
            return self.demo.get_cluster_health(req)

        keyword = req.keyword.strip()
        since_req, end_ts = resolve_time_window(req)
        sig_window_min = 15
        since_calc = extend_start_for_signature(since_req, sig_window_min)
        assets = self.pg.fetch_assets(keyword)
        asset_ids = [a["asset_id"] for a in assets if a.get("asset_id")]

        with ThreadPoolExecutor(max_workers=8) as ex:
            f_infra = ex.submit(self.pg.fetch_infra_anomalies, asset_ids, since_calc, end_ts)
            f_app = ex.submit(self.pg.fetch_app_anomalies, asset_ids, since_calc, end_ts)
            f_app_logs_by_host = ex.submit(self.loki.query_count_per_minute_by_host_ip, logql=Q_APP, start_dt=since_calc, end_dt=end_ts)
            f_dag_logs_by_host = ex.submit(self.loki.query_count_per_minute_by_host_ip, logql=Q_DAG, start_dt=since_calc, end_dt=end_ts)

            infra_anoms = f_infra.result() or []
            app_anoms = f_app.result() or []
            app_logs_by_host = f_app_logs_by_host.result() or {}
            dag_logs_by_host = f_dag_logs_by_host.result() or {}

        app_log_counts = collapse_grouped_counts_to_global(app_logs_by_host)
        dag_log_counts = collapse_grouped_counts_to_global(dag_logs_by_host)
        payload = compute_component_health_scores(
            infra_anoms=infra_anoms,
            app_anoms=app_anoms,
            app_log_counts=app_log_counts,
            dag_log_counts=dag_log_counts,
            since=since_calc,
            end_ts=end_ts,
            culprit_window_minutes=sig_window_min,
        )
        combined_anoms = infra_anoms + app_anoms
        combined_hf = compute_health_failure_timeline(
            combined_anoms,
            [],
            None,
            start=since_calc,
            end=end_ts,
            app_log_counts=app_log_counts,
            dag_log_counts=dag_log_counts,
        )
        infra_hf = compute_health_failure_timeline(
            infra_anoms,
            [],
            None,
            start=since_calc,
            end=end_ts,
            app_log_counts={},
            dag_log_counts={},
        )
        app_hf = compute_health_failure_timeline(
            app_anoms,
            [],
            None,
            start=since_calc,
            end=end_ts,
            app_log_counts=app_log_counts,
            dag_log_counts=dag_log_counts,
        )
        combined_hf = attach_signatures_to_timeline(combined_hf, window_minutes=sig_window_min)
        infra_hf = attach_signatures_to_timeline(infra_hf, window_minutes=sig_window_min)
        app_hf = attach_signatures_to_timeline(app_hf, window_minutes=sig_window_min)
        combined_hf = trim_rows_to_requested_window(combined_hf, since_req, end_ts)
        infra_hf = trim_rows_to_requested_window(infra_hf, since_req, end_ts)
        app_hf = trim_rows_to_requested_window(app_hf, since_req, end_ts)
        last_row = combined_hf[-1] if combined_hf else None

        asset_health_timeline = compute_asset_health_statistical_with_contributors(
            assets,
            combined_anoms,
            app_log_counts_by_host_ip=app_logs_by_host,
            dag_log_counts_by_host_ip=dag_logs_by_host,
            start=since_calc,
            end=end_ts,
            alpha=0.30,
            top_n=3,
        )
        asset_health_timeline_infra = compute_asset_health_statistical_with_contributors(
            assets,
            infra_anoms,
            app_log_counts_by_host_ip={},
            dag_log_counts_by_host_ip={},
            start=since_calc,
            end=end_ts,
            alpha=0.30,
            top_n=3,
        )
        asset_health_timeline_app = compute_asset_health_statistical_with_contributors(
            assets,
            app_anoms,
            app_log_counts_by_host_ip=app_logs_by_host,
            dag_log_counts_by_host_ip=dag_logs_by_host,
            start=since_calc,
            end=end_ts,
            alpha=0.30,
            top_n=3,
        )

        return {
            "keyword": keyword,
            "since_utc": since_calc.isoformat(),
            "until_utc": end_ts.isoformat(),
            **payload,
            "health_signature": signature_block_from_timeline(combined_hf, window_minutes=sig_window_min),
            "health_failure_last": last_row,
            "health_score_window": cluster_score_from_timeline(combined_hf, window_minutes=sig_window_min, mode="p10"),
            "health_archetype_last": (last_row or {}).get("health_archetype"),
            "health_sequence_last": (last_row or {}).get("health_sequence"),
            "health_failure_timeline": combined_hf,
            "asset_health_timeline": asset_health_timeline,
            "infra_only": {
                "cluster_health": cluster_score_from_timeline(infra_hf, window_minutes=sig_window_min, mode="p10"),
                "health_failure_timeline": infra_hf,
                "asset_health_timeline": asset_health_timeline_infra,
            },
            "app_only": {
                "cluster_health": cluster_score_from_timeline(app_hf, window_minutes=sig_window_min, mode="p10"),
                "health_failure_timeline": app_hf,
                "asset_health_timeline": asset_health_timeline_app,
            },
            "debug": {
                "sig_window_minutes": sig_window_min,
                "app_log_total": int(sum(app_log_counts.values())) if app_log_counts else 0,
                "dag_log_total": int(sum(dag_log_counts.values())) if dag_log_counts else 0,
                "combined_anomaly_count": int(len(combined_anoms)),
            },
        }

