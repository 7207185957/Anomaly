from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

import requests

from app.core.config import get_settings
from app.domain.health import floor_to_minute


class LokiService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def query_raw_logs(
        self,
        *,
        logql: str,
        start_dt: datetime,
        end_dt: datetime,
        limit: int = 5000,
    ) -> list[dict[str, Any]]:
        params = {
            "query": logql,
            "start": int(start_dt.timestamp() * 1e9),
            "end": int(end_dt.timestamp() * 1e9),
            "limit": limit,
            "direction": "forward",
        }
        r = requests.get(self.settings.loki_url, params=params, timeout=90)
        r.raise_for_status()
        result = r.json().get("data", {}).get("result", []) or []

        rows: list[dict[str, Any]] = []
        for stream in result:
            labels = stream.get("stream", {}) or {}
            host_ip = labels.get("host_ip", "")
            filename = labels.get("filename", "")
            service = labels.get("service", "")
            for ts_ns, line in stream.get("values", []):
                ts_dt = datetime.fromtimestamp(float(ts_ns) / 1e9, tz=timezone.utc)
                rows.append(
                    {
                        "timestamp": ts_dt.isoformat(),
                        "host_ip": host_ip,
                        "filename": filename,
                        "service": service,
                        "log": line,
                    }
                )
        return rows

    def query_count_per_minute(
        self,
        *,
        logql: str,
        start_dt: datetime,
        end_dt: datetime,
    ) -> dict[datetime, int]:
        metric_query = f"sum(count_over_time({logql}[1m]))"
        params = {
            "query": metric_query,
            "start": int(start_dt.timestamp() * 1e9),
            "end": int(end_dt.timestamp() * 1e9),
            "step": 60,
        }
        r = requests.get(self.settings.loki_url, params=params, timeout=120)
        r.raise_for_status()
        result = r.json().get("data", {}).get("result", []) or []
        if not result:
            return {}
        series = result[0]
        out: dict[datetime, int] = {}
        for ts_s, val in series.get("values", []):
            ts_dt = datetime.fromtimestamp(float(ts_s), tz=timezone.utc)
            out[floor_to_minute(ts_dt)] = int(float(val))
        return out

    def query_count_per_minute_by_host_ip(
        self,
        *,
        logql: str,
        start_dt: datetime,
        end_dt: datetime,
    ) -> dict[str, dict[datetime, int]]:
        metric_query = f"sum by (host_ip) (count_over_time(({logql})[1m]))"
        params = {
            "query": metric_query,
            "start": int(start_dt.timestamp() * 1e9),
            "end": int(end_dt.timestamp() * 1e9),
            "step": 60,
        }
        r = requests.get(self.settings.loki_url, params=params, timeout=120)
        r.raise_for_status()
        result = r.json().get("data", {}).get("result", []) or []
        out: dict[str, dict[datetime, int]] = defaultdict(dict)
        for series in result:
            labels = series.get("metric", {}) or {}
            host_ip = labels.get("host_ip") or "unknown"
            for ts_s, val in series.get("values", []):
                ts_dt = datetime.fromtimestamp(float(ts_s), tz=timezone.utc)
                out[str(host_ip)][floor_to_minute(ts_dt)] = int(float(val))
        return dict(out)

