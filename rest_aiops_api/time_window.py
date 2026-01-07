from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from dateutil import parser


def safe_parse_ts(ts: object) -> Optional[datetime]:
    if ts is None:
        return None
    if isinstance(ts, datetime):
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    try:
        dtt = parser.isoparse(str(ts))
        return dtt if dtt.tzinfo else dtt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def lookback_cutoff(hours: int) -> datetime:
    hours = max(1, min(int(hours or 3), 168))  # clamp 1..168
    return datetime.now(timezone.utc) - timedelta(hours=hours)


def resolve_time_window(
    *,
    lookback_hours: int = 3,
    start_utc: Optional[str] = None,
    end_utc: Optional[str] = None,
) -> Tuple[datetime, datetime]:
    if start_utc:
        since = safe_parse_ts(start_utc)
        if since is None:
            raise ValueError("Invalid start_utc. Use ISO-8601, e.g. 2025-12-22T00:00:00Z")
    else:
        since = lookback_cutoff(lookback_hours)

    if end_utc:
        end_ts = safe_parse_ts(end_utc)
        if end_ts is None:
            raise ValueError("Invalid end_utc. Use ISO-8601, e.g. 2025-12-22T23:59:59Z")
    else:
        end_ts = datetime.now(timezone.utc)

    if since > end_ts:
        raise ValueError("start_utc must be <= end_utc")

    return since, end_ts

