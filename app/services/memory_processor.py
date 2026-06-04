from datetime import datetime
from typing import Any, Optional

from app.core.logging import get_logger
from app.db.models import Memory, WebhookEvent
from app.db.session import get_session_sync
from app.services import openai_service, task_extractor
from app.utils.text import join_transcript_segments

logger = get_logger()


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00").replace("+00:00", ""))
    except ValueError:
        return None


def process_memory_payload(payload: dict, omi_uid: Optional[str]) -> dict:
    session = get_session_sync()
    try:
        memory_id = payload.get("id")
        structured = payload.get("structured") or {}
        segments = payload.get("transcript_segments") or []
        transcript = join_transcript_segments(segments)
        if not transcript and structured.get("overview"):
            transcript = structured.get("overview", "")

        summary_data = {}
        if transcript:
            summary_data = openai_service.summarize_memory(transcript)

        mem = Memory(
            omi_memory_id=memory_id,
            omi_uid=omi_uid,
            title=structured.get("title") or summary_data.get("title"),
            summary=structured.get("overview") or summary_data.get("overview"),
            transcript=transcript,
            started_at=_parse_dt(payload.get("started_at")),
            ended_at=_parse_dt(payload.get("finished_at")),
            raw_payload=payload,
        )
        session.add(mem)
        session.commit()
        session.refresh(mem)

        stats = {"memory_id": mem.id}
        if omi_uid and transcript:
            stats["tasks"] = task_extractor.ingest_tasks_from_text(
                omi_uid, transcript, source_memory_id=mem.id
            )
        return stats
    finally:
        session.close()


def mark_event_processed(webhook_event_id: str, error: Optional[str] = None):
    session = get_session_sync()
    try:
        event = session.get(WebhookEvent, webhook_event_id)
        if event:
            event.status = "failed" if error else "processed"
            event.processed_at = datetime.utcnow()
            event.error = error
            session.add(event)
            session.commit()
    finally:
        session.close()
