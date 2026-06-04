from typing import Any

from redis import Redis
from rq import Queue

from app.core.config import get_settings

QUEUE_NAME = "omi_jobs"


def get_redis() -> Redis:
    settings = get_settings()
    return Redis.from_url(settings.redis_url)


def get_queue() -> Queue:
    return Queue(QUEUE_NAME, connection=get_redis())


def enqueue_job(job_type: str, payload: dict[str, Any]) -> str:
    """Enqueue a background job. Returns RQ job id."""
    from app.workers.jobs import JOB_HANDLERS

    handler = JOB_HANDLERS.get(job_type)
    if not handler:
        raise ValueError(f"Unknown job type: {job_type}")

    q = get_queue()
    job = q.enqueue(handler, payload, job_timeout=600, result_ttl=86400)
    return job.id
