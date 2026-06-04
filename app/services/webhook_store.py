import json
from datetime import datetime
from typing import Any, Optional

from sqlmodel import Session, select

from app.core.logging import get_logger
from app.core.queue import enqueue_job
from app.db.models import JobRecord, WebhookEvent
from app.db.session import get_session_sync

logger = get_logger()


def _headers_dict(request_headers: dict) -> dict:
    return {k: v for k, v in request_headers.items()}


def record_and_enqueue(
    event_type: str,
    omi_uid: Optional[str],
    raw_payload: Any,
    headers: dict,
    job_type: str,
    extra_payload: Optional[dict] = None,
) -> dict:
    session = get_session_sync()
    try:
        event = WebhookEvent(
            source="omi",
            event_type=event_type,
            omi_uid=omi_uid,
            raw_payload=raw_payload if isinstance(raw_payload, dict) else {"data": raw_payload},
            headers=_headers_dict(headers),
            status="received",
        )
        session.add(event)
        session.commit()
        session.refresh(event)

        job_payload = {
            "webhook_event_id": event.id,
            "omi_uid": omi_uid,
            **(extra_payload or {}),
        }
        job_record = JobRecord(
            job_type=job_type,
            status="queued",
            payload=job_payload,
        )
        session.add(job_record)
        session.commit()
        session.refresh(job_record)

        try:
            rq_id = enqueue_job(job_type, job_payload)
            job_record.rq_job_id = rq_id
            job_record.status = "queued"
            session.add(job_record)
            session.commit()
        except Exception as e:
            logger.exception("enqueue_failed", job_type=job_type, error=str(e))
            job_record.status = "failed"
            job_record.last_error = str(e)
            event.status = "enqueue_failed"
            event.error = str(e)
            session.add(job_record)
            session.add(event)
            session.commit()

        return {"status": "ok", "event_id": event.id}
    finally:
        session.close()


def replay_webhook_event(event_id: str) -> dict:
    session = get_session_sync()
    try:
        event = session.get(WebhookEvent, event_id)
        if not event:
            return {"error": "Event not found"}

        job_type_map = {
            "memory": "process_memory",
            "realtime_transcript": "process_realtime_segment",
            "audio": "process_audio_chunk",
            "daily_summary": "process_daily_summary",
        }
        job_type = job_type_map.get(event.event_type)
        if not job_type:
            return {"error": f"Cannot replay event type: {event.event_type}"}

        payload = {
            "webhook_event_id": event.id,
            "omi_uid": event.omi_uid,
            "replay": True,
        }
        rq_id = enqueue_job(job_type, payload)
        event.status = "requeued"
        session.add(event)
        session.commit()
        return {"status": "ok", "rq_job_id": rq_id}
    finally:
        session.close()
