from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    db_uri: str
    ollama_url_generate: str
    ollama_model: str

    aiops_api_url: str
    aiops_api_url_app: str
    aiops_api_url_combined: str

    request_timeout_seconds: int = 1200


def get_settings() -> Settings:
    db_uri = os.getenv("DB_URI", "").strip()
    if not db_uri:
        # Keep the service importable; endpoints will fail with a clear error.
        db_uri = ""

    return Settings(
        db_uri=db_uri,
        ollama_url_generate=os.getenv("OLLAMA_URL_GENERATE", "http://172.16.109.94:11435/api/generate"),
        ollama_model=os.getenv("OLLAMA_MODEL", "mistral:latest"),
        aiops_api_url=os.getenv("AIOPS_API_URL", "http://127.0.0.1:9001/summarize"),
        aiops_api_url_app=os.getenv("AIOPS_API_URL_APP", "http://127.0.0.1:9001/summarize_app"),
        aiops_api_url_combined=os.getenv("AIOPS_API_URL_COMBINED", "http://127.0.0.1:9001/summarize_combined"),
        request_timeout_seconds=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "1200")),
    )

