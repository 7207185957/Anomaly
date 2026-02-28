from datetime import datetime
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


class PostgresRepository:
    def __init__(self) -> None:
        settings = get_settings()
        self._cfg = {
            "host": settings.pg_host,
            "port": settings.pg_port,
            "user": settings.pg_user,
            "password": settings.pg_password,
            "dbname": settings.pg_db,
        }

    def _conn(self):
        return psycopg2.connect(**self._cfg)

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
        q = """
            SELECT *
            FROM incidents
            WHERE service_impacted ILIKE %(kw)s
              AND (%(since)s IS NULL OR start_time >= %(since)s)
              AND (%(until)s IS NULL OR start_time <= %(until)s)
            ORDER BY start_time ASC
        """
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(
                    q,
                    {"kw": f"%{keyword}%", "since": since_ts, "until": until_ts},
                )
                rows = cur.fetchall()
        finally:
            conn.close()

        out = []
        for r in rows:
            d = dict(r)
            d["start_time"] = safe_parse_ts(d.get("start_time"))
            d["end_time"] = safe_parse_ts(d.get("end_time"))
            d["created_at"] = safe_parse_ts(d.get("created_at"))
            d["updated_at"] = safe_parse_ts(d.get("updated_at"))
            out.append(d)
        return out

