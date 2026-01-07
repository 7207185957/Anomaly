from __future__ import annotations

from typing import Any, Iterable


def smart_fix_recommendation(keyword: str, service: str, title: str, description: str, alerts: Iterable[dict[str, Any]]):
    keyword_l = (keyword or "").lower()
    title_l = (title or "").lower()
    description_l = (description or "").lower()

    has_cpu = "cpu" in title_l or "cpu" in description_l
    has_mem = "memory" in title_l or "mem" in description_l
    has_latency = "latency" in title_l or "slow" in description_l
    has_error = "error" in title_l or "exception" in description_l

    if has_cpu:
        return (
            f"Investigate workloads linked to '{keyword_l}' that increased CPU usage on {service}. "
            "Throttle or disable the faulty job, restart the affected workers, and rebalance "
            "load across cluster nodes. Validate CPU normalization after fix."
        )

    if has_mem:
        return (
            f"Review memory-intensive processes associated with '{keyword_l}' on {service}. "
            "Restart leaking components, purge caches, and ensure no runaway tasks are active."
        )

    if has_latency:
        return (
            f"Check upstream/downstream dependencies modified around the '{keyword_l}' change. "
            f"Optimize slow queries, scale {service} replicas, and flush connection pools."
        )

    if has_error:
        return (
            f"Errors linked to '{keyword_l}' suggest a failing component in {service}. "
            "Rollback the latest config/deployment, restart impacted services, and validate logs."
        )

    if "airflow" in keyword_l:
        return (
            "Disable the problematic Airflow DAG, revert task configuration changes, "
            f"and clear queues impacting {service}. Restart scheduler & workers."
        )

    if "network" in keyword_l:
        return (
            f"Revert the latest network policy/firewall/routing update affecting {service}. "
            "Validate reachability and restore prior stable routing state."
        )

    if "db" in keyword_l or "database" in keyword_l:
        return (
            f"Check DB connection pool saturation due to '{keyword_l}'. "
            "Restart DB connectors, tune pool limits, and verify query performance."
        )

    return (
        f"Investigate the change associated with '{keyword_l}' and restore the last known "
        f"stable configuration for {service}. Validate health metrics afterward."
    )


def probable_change_text(keyword: str, service: str) -> str:
    return (
        "The incident is most likely linked to a recent change associated "
        f"with '{keyword}', which impacted the '{service}' service. "
        "The behaviour observed closely matches the incident symptoms."
    )

