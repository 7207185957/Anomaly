from datetime import datetime
import logging
from typing import Any

import psycopg2
import psycopg2.extras
from dateutil import parser

from app.core.config import get_settings


def safe_parse_ts(ts: Any) -> datetime | None:
    if ts is None:
        return None
    if isinstance(ts, datetime):
        return ts
    try:
        return parser.isoparse(str(ts))
    except Exception:
        return None


logger = logging.getLogger(__name__)


class PostgresRepository:
    def __init__(self) -> None:
        settings = get_settings()
        self._settings = settings
        self._cfg = {
            "host": settings.pg_host,
            "port": settings.pg_port,
            "user": settings.pg_user,
            "password": settings.pg_password,
            "dbname": settings.pg_db,
            "connect_timeout": settings.pg_connect_timeout_sec,
        }
        self._incident_cfg = {
            "host": settings.incident_pg_host or settings.pg_host,
            "port": settings.incident_pg_port or settings.pg_port,
            "user": settings.incident_pg_user or settings.pg_user,
            "password": settings.incident_pg_password or settings.pg_password,
            "dbname": settings.incident_pg_db or settings.pg_db,
            "connect_timeout": settings.pg_connect_timeout_sec,
        }

    def _conn(self):
        return psycopg2.connect(**self._cfg)

    def _incident_conn(self):
        return psycopg2.connect(**self._incident_cfg)

    def fetch_assets(self, keyword: str) -> list[dict[str, Any]]:
        q = """
            SELECT *
            FROM cmdb_assets
            WHERE name ILIKE %(kw)s OR asset_id ILIKE %(kw)s
        """
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(q, {"kw": f"%{keyword}%"})
                rows = cur.fetchall()
        finally:
            conn.close()

        out = []
        for r in rows:
            d = dict(r)
            d["created_at"] = safe_parse_ts(d.get("created_at"))
            d["updated_at"] = safe_parse_ts(d.get("updated_at"))
            out.append(d)
        return out

    def fetch_changes(
        self,
        asset_ids: list[str],
        since_ts: datetime | None,
        until_ts: datetime | None,
    ) -> list[dict[str, Any]]:
        if not asset_ids:
            return []

        q = """
            SELECT *
            FROM cmdb_changes
            WHERE asset_id = ANY(%(ids)s)
              AND (%(since)s IS NULL OR timestamp >= %(since)s)
              AND (%(until)s IS NULL OR timestamp <= %(until)s)
            ORDER BY timestamp ASC
        """
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(
                    q,
                    {"ids": asset_ids, "since": since_ts, "until": until_ts},
                )
                rows = cur.fetchall()
        finally:
            conn.close()

        out = []
        for r in rows:
            d = dict(r)
            d["timestamp"] = safe_parse_ts(d.get("timestamp"))
            out.append(d)
        return out

    def fetch_relationships(self, asset_ids: list[str]) -> list[dict[str, Any]]:
        if not asset_ids:
            return []

        q = """
            SELECT *
            FROM cmdb_relationships
            WHERE parent_asset_id = ANY(%(ids)s)
        """
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(q, {"ids": asset_ids})
                rows = cur.fetchall()
        finally:
            conn.close()

        out = []
        for r in rows:
            d = dict(r)
            d["created_at"] = safe_parse_ts(d.get("created_at"))
            out.append(d)
        return out

    def fetch_infra_anomalies(
        self,
        asset_ids: list[str],
        since_ts: datetime | None,
        until_ts: datetime | None,
    ) -> list[dict[str, Any]]:
        if not asset_ids:
            return []
        asset_ids_mod = [str(aid).replace("-", "_") for aid in asset_ids]
        q = """
            SELECT *
            FROM infra_metrics
            WHERE instance = ANY(%(ids)s)
              AND anomaly NOT IN ('f')
              AND (%(since)s IS NULL OR timestamp >= %(since)s)
              AND (%(until)s IS NULL OR timestamp <= %(until)s)
            ORDER BY timestamp ASC
        """
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(
                    q,
                    {"ids": asset_ids_mod, "since": since_ts, "until": until_ts},
                )
                rows = cur.fetchall()
        finally:
            conn.close()

        out = []
        for r in rows:
            d = dict(r)
            d["timestamp"] = safe_parse_ts(d.get("timestamp"))
            d["created_at"] = safe_parse_ts(d.get("created_at"))
            d["updated_at"] = safe_parse_ts(d.get("updated_at"))
            if d.get("instance"):
                d["instance"] = str(d["instance"]).replace("_", "-")
            d["source"] = "infra"
            out.append(d)
        return out

    def fetch_app_anomalies(
        self,
        asset_ids: list[str],
        since_ts: datetime | None,
        until_ts: datetime | None,
    ) -> list[dict[str, Any]]:
        if not asset_ids:
            return []
        asset_ids_mod = [str(aid).replace("_", "-") for aid in asset_ids]
        q = """
            SELECT *
            FROM app_metrics
            WHERE instance_name = ANY(%(ids)s)
              AND anomaly = 1
              AND (%(since)s IS NULL OR ts >= %(since)s)
              AND (%(until)s IS NULL OR ts <= %(until)s)
            ORDER BY ts ASC
        """
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(
                    q,
                    {"ids": asset_ids_mod, "since": since_ts, "until": until_ts},
                )
                rows = cur.fetchall()
        finally:
            conn.close()

        out = []
        for r in rows:
            d = dict(r)
            ts = d.get("ts") or d.get("timestamp")
            d["timestamp"] = safe_parse_ts(ts)
            d["created_at"] = safe_parse_ts(ts)
            d["updated_at"] = safe_parse_ts(ts)
            inst = d.get("instance_name") or d.get("instance") or ""
            d["instance"] = str(inst).replace("_", "-")
            d["metric"] = d.get("metric") or d.get("metric_name") or d.get("kpi") or "app_metric"
            d["severity"] = d.get("severity") or "low"
            d["source"] = "app"
            out.append(d)
        return out

    def fetch_incidents(
        self,
        keyword: str,
        since_ts: datetime | None,
        until_ts: datetime | None,
    ) -> list[dict[str, Any]]:
        return self.fetch_open_incidents(
            team_name=self._settings.incident_team_name,
            keyword=keyword,
            since_ts=since_ts,
            until_ts=until_ts,
            include_resolved=False,
        )

    @staticmethod
    def _normalize_incident_row(d: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(d)

        def pick(*keys: str):
            for k in keys:
                if normalized.get(k) not in (None, ""):
                    return normalized.get(k)
            return None

        normalized["incident_id"] = pick(
            "incident_id",
            "incidentnumber",
            "incident_number",
            "incidentuuid",
            "id",
        )
        normalized["title"] = pick("title", "entitydisplayname", "summary", "message", "alertname", "policy_name")
        normalized["description"] = pick("description", "details", "entityid", "incidentlink", "routingkey")
        normalized["severity"] = pick("severity", "currentphase", "priority", "entitystate") or "unknown"
        normalized["status"] = pick("status", "entitystate", "currentphase") or "open"
        normalized["service_impacted"] = pick(
            "service_impacted", "service", "team_name", "policy_name", "routingkey"
        )
        normalized["root_cause"] = pick("root_cause", "cause", "notes")

        start = pick("start_time", "starttime", "started_at", "created_at")
        end = pick("end_time", "endtime", "resolved_at", "closed_at")
        normalized["start_time"] = safe_parse_ts(start)
        normalized["end_time"] = safe_parse_ts(end)
        normalized["created_at"] = safe_parse_ts(pick("created_at", "starttime", "start_time"))
        normalized["updated_at"] = safe_parse_ts(pick("updated_at", "lastalerttime", "end_time"))
        return normalized

    def _fetch_victorops_incidents(
        self,
        team_name: str,
        keyword: str | None,
        since_ts: datetime | None,
        until_ts: datetime | None,
        include_resolved: bool,
    ) -> list[dict[str, Any]]:
        q = """
            SELECT policies.*, incidents.*
            FROM victorops_incidents_paged_policies_v1 AS policies
            INNER JOIN victorops_incidents_v1 AS incidents
                ON policies.firstalertuuid = incidents.firstalertuuid
            WHERE (%(team)s IS NULL OR policies.team_name = %(team)s)
              AND (
                    %(kw)s IS NULL
                    OR policies.policy_name ILIKE %(kw_like)s
                    OR incidents.entitydisplayname ILIKE %(kw_like)s
                    OR incidents.routingkey ILIKE %(kw_like)s
                  )
              AND (%(include_resolved)s = TRUE OR incidents.currentphase != 'RESOLVED')
            ORDER BY incidents.starttime DESC
            LIMIT 1000
        """
        conn = self._incident_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(
                    q,
                    {
                        "team": team_name or None,
                        "kw": keyword or None,
                        "kw_like": f"%{keyword}%" if keyword else None,
                        "include_resolved": include_resolved,
                    },
                )
                rows = cur.fetchall()
        finally:
            conn.close()

        out = []
        for r in rows:
            row = self._normalize_incident_row(dict(r))
            row_ts = safe_parse_ts(row.get("start_time"))
            if since_ts and row_ts and row_ts < since_ts:
                continue
            if until_ts and row_ts and row_ts > until_ts:
                continue
            out.append(row)
        return out

    def _fetch_fallback_incidents(
        self,
        keyword: str | None,
        since_ts: datetime | None,
        until_ts: datetime | None,
        include_resolved: bool,
    ) -> list[dict[str, Any]]:
        q = """
            SELECT *
            FROM incidents
            WHERE (%(kw)s IS NULL OR service_impacted ILIKE %(kw_like)s)
              AND (%(since)s IS NULL OR start_time >= %(since)s)
              AND (%(until)s IS NULL OR start_time <= %(until)s)
              AND (%(include_resolved)s = TRUE OR COALESCE(status, '') !~* 'resolved|closed')
            ORDER BY start_time DESC
            LIMIT 1000
        """
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(
                    q,
                    {
                        "kw": keyword or None,
                        "kw_like": f"%{keyword}%" if keyword else None,
                        "since": since_ts,
                        "until": until_ts,
                        "include_resolved": include_resolved,
                    },
                )
                rows = cur.fetchall()
        finally:
            conn.close()

        out = []
        for r in rows:
            out.append(self._normalize_incident_row(dict(r)))
        return out

    def fetch_open_incidents(
        self,
        *,
        team_name: str | None,
        keyword: str | None,
        since_ts: datetime | None,
        until_ts: datetime | None,
        include_resolved: bool = False,
    ) -> list[dict[str, Any]]:
        try:
            return self._fetch_victorops_incidents(
                team_name=team_name or self._settings.incident_team_name,
                keyword=keyword,
                since_ts=since_ts,
                until_ts=until_ts,
                include_resolved=include_resolved,
            )
        except Exception as exc:
            logger.warning("VictorOps incident query failed; falling back to incidents table: %s", exc)
            return self._fetch_fallback_incidents(
                keyword=keyword,
                since_ts=since_ts,
                until_ts=until_ts,
                include_resolved=include_resolved,
            )

