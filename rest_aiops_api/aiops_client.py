from __future__ import annotations

from typing import Any, Optional

import requests


def post_json(url: str, payload: dict[str, Any], *, timeout_seconds: int = 1200) -> dict[str, Any]:
    resp = requests.post(url, json=payload, timeout=timeout_seconds)
    resp.raise_for_status()
    data = resp.json()
    return data if isinstance(data, dict) else {"data": data}


def build_aiops_payload(
    *,
    keyword: str,
    lookback_hours: int = 3,
    start_utc: Optional[str] = None,
    end_utc: Optional[str] = None,
) -> dict[str, Any]:
    req: dict[str, Any] = {"keyword": keyword, "lookback_hours": int(lookback_hours)}
    if start_utc and end_utc:
        req["start_utc"] = start_utc
        req["end_utc"] = end_utc
    return req

