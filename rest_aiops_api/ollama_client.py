from __future__ import annotations

import json
from typing import Iterable

import requests


def get_keywords_from_ollama(
    *,
    ollama_url_generate: str,
    model: str,
    text_values: Iterable[str],
    timeout_seconds: int = 30,
) -> str:
    prompt = f"""
Extract the primary descriptive keywords from the following text entries.
Respond with ONLY comma-separated keywords.

Text:
{list(text_values)}
"""
    payload = {"model": model, "prompt": prompt}

    r = requests.post(ollama_url_generate, json=payload, timeout=timeout_seconds)
    r.raise_for_status()

    # Ollama can return either JSON or newline-delimited JSON streaming.
    try:
        data = r.json()
        if isinstance(data, dict) and "response" in data:
            return str(data["response"]).strip()
    except ValueError:
        pass

    result = ""
    for line in r.text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict) and "response" in obj:
                result += str(obj["response"])
        except Exception:
            continue
    return result.strip()

