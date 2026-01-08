from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from .settings import Settings


class Db:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._engine: Optional[Engine] = None

    @property
    def engine(self) -> Engine:
        if self._engine is None:
            if not self._settings.db_uri:
                raise RuntimeError("DB_URI is not set")
            self._engine = create_engine(self._settings.db_uri, pool_pre_ping=True, future=True)
        return self._engine

    def fetch_all(self, sql: str, params: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
        params = params or {}
        with self.engine.connect() as conn:
            rows = conn.execute(text(sql), params).mappings().all()
            return [dict(r) for r in rows]

