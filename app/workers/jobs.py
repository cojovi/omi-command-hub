from datetime import datetime
from typing import Any, Callable

from sqlmodel import select

from app.core.logging import get_logger
from app.db.models import DailySummary, JobRecord, WebhookEvent
from app.db.session import get_session_sync
from app.services import (
    google_chat,
    memory_processor,
    transcript_processor,
)

logger = get_logger()
MAX_ATTEMPTS = 3


def _update_job(job_payload: dict, status: str, error: str | None = None):
    session = get_session_sync()
    try:
        event_id = job_payload.get("webhook_event_id")
        if event_id:
            event = session.get(WebhookEvent, event_id)
            if event:
                event.status = "failed" if error else "processed"
                event.processed_at = datetime.utcnow()
                event.error = error
                session.add(event)
        session.commit()
    finally:
        session.close()


def process_memory(payload: dict[str, Any]) -> dict:
    webhook_event_id = payload.get("webhook_event_id")
    omi_uid = payload.get("omi_uid")
    try:
        session = get_session_sync()
        event = session.get(WebhookEvent, webhook_event_id) if webhook_event_id else None
        raw = event.raw_payload if event else payload.get("memory") or {}
        session.close()

        result = memory_processor.process_memory_payload(raw, omi_uid)
        memory_processor.mark_event_processed(webhook_event_id)
        return result
    except Exception as e:
        logger.exception("process_memory_failed", error=str(e))
        if webhook_event_id:
            memory_processor.mark_event_processed(webhook_event_id, error=str(e))
        raise


def process_realtime_segment(payload: dict[str, Any]) -> dict:
    webhook_event_id = payload.get("webhook_event_id")
    omi_uid = payload.get("omi_uid")
    session_id = payload.get("session_id")
    try:
        session = get_session_sync()
        event = session.get(WebhookEvent, webhook_event_id) if webhook_event_id else None
        raw = event.raw_payload if event else payload.get("segments") or []
        session.close()

        result = transcript_processor.process_realtime_payload(raw, omi_uid, session_id)
        transcript_processor.mark_event_processed(webhook_event_id)
        return result
    except Exception as e:
        logger.exception("process_realtime_failed", error=str(e))
        if webhook_event_id:
            transcript_processor.mark_event_processed(webhook_event_id, error=str(e))
        raise


def process_audio_chunk(payload: dict[str, Any]) -> dict:
    webhook_event_id = payload.get("webhook_event_id")
    logger.info(
        "audio_chunk_stub",
        sample_rate=payload.get("sample_rate"),
        webhook_event_id=webhook_event_id,
    )
    if webhook_event_id:
        memory_processor.mark_event_processed(webhook_event_id)
    return {"status": "stub", "message": "Audio processing not implemented in v1"}


def process_daily_summary(payload: dict[str, Any]) -> dict:
    webhook_event_id = payload.get("webhook_event_id")
    omi_uid = payload.get("omi_uid")
    try:
        session = get_session_sync()
        event = session.get(WebhookEvent, webhook_event_id) if webhook_event_id else None
        raw = event.raw_payload if event else {}
        session.close()

        summary_json = raw.get("summary_json")
        if not summary_json and raw.get("summary"):
            import ast

            try:
                summary_json = ast.literal_eval(raw.get("summary"))
            except (ValueError, SyntaxError):
                summary_json = {"overview": str(raw.get("summary"))}

        if not isinstance(summary_json, dict):
            summary_json = {}

        row = DailySummary(
            omi_uid=omi_uid or raw.get("uid") or "unknown",
            summary_date=summary_json.get("date"),
            headline=summary_json.get("headline"),
            overview=summary_json.get("overview"),
            raw_payload=raw,
        )
        session = get_session_sync()
        session.add(row)
        session.commit()
        session.refresh(row)
        summary_id = row.id
        session.close()

        digest = summary_json.get("headline") or summary_json.get("overview") or "Daily summary received"
        google_chat.send_google_chat_message(f"📅 Daily digest: {digest}")

        if webhook_event_id:
            memory_processor.mark_event_processed(webhook_event_id)
        return {"summary_id": summary_id}
    except Exception as e:
        logger.exception("process_daily_summary_failed", error=str(e))
        if webhook_event_id:
            memory_processor.mark_event_processed(webhook_event_id, error=str(e))
        raise


def execute_tool_call(payload: dict[str, Any]) -> dict:
    from app.api.omi_tools import execute_tool_internal

    return execute_tool_internal(payload)


def send_google_chat_message(payload: dict[str, Any]) -> dict:
    return google_chat.send_google_chat_message(payload.get("message", ""))


JOB_HANDLERS: dict[str, Callable[[dict[str, Any]], dict]] = {
    "process_memory": process_memory,
    "process_realtime_segment": process_realtime_segment,
    "process_audio_chunk": process_audio_chunk,
    "process_daily_summary": process_daily_summary,
    "execute_tool_call": execute_tool_call,
    "send_google_chat_message": send_google_chat_message,
}
