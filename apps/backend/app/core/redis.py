from functools import lru_cache

from redis import Redis
from rq import Queue

from app.core.config import get_settings


@lru_cache(maxsize=1)
def get_redis() -> Redis:
    settings = get_settings()
    return Redis.from_url(settings.redis_url)


def get_queue(name: str | None = None) -> Queue:
    settings = get_settings()
    return Queue(name or settings.rca_queue_name, connection=get_redis())

