from datetime import datetime
from typing import Any, Optional

from sqlmodel import select

from app.core.logging import get_logger
from app.db.models import Note, TranscriptSegment, WebhookEvent
from app.db.session import get_session_sync
from app.services import google_chat, omi_notifications, router, task_extractor
from app.utils.ids import segment_hash
from app.utils.text import join_transcript_segments

logger = get_logger()


def _store_segments(
    omi_uid: Optional[str],
    session_id: Optional[str],
    segments: list[dict],
) -> list[str]:
    session = get_session_sync()
    stored_ids = []
    try:
        for seg in segments:
            if not isinstance(seg, dict):
                continue
            text = seg.get("text") or ""
            if not text.strip():
                continue
            sh = segment_hash(session_id or "unknown", seg)
            existing = session.exec(
                select(TranscriptSegment).where(TranscriptSegment.segment_hash == sh)
            ).first()
            if existing:
                continue
            row = TranscriptSegment(
                omi_uid=omi_uid,
                session_id=session_id,
                segment_hash=sh,
                speaker=seg.get("speaker") or seg.get("speaker_name"),
                text=text,
                raw_payload=seg,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            stored_ids.append(row.id)
        return stored_ids
    finally:
        session.close()


def _handle_routed_intent(omi_uid: str, intent: router.RoutedIntent) -> None:
    args = intent.arguments
    if intent.intent == "create_task":
        task_extractor.create_task_manual(
            omi_uid, title=args.get("title") or args.get("remainder") or "Task"
        )
    elif intent.intent in ("save_note", "log_business_idea"):
        session = get_session_sync()
        try:
            note = Note(
                omi_uid=omi_uid,
                title=args.get("title"),
                body=args.get("body") or args.get("text", ""),
                tags=["business_idea"] if intent.intent == "log_business_idea" else [],
                source="realtime_router",
            )
            session.add(note)
            session.commit()
            omi_notifications.send_omi_notification(omi_uid, f"📝 Note saved: {note.title or 'untitled'}")
        finally:
            session.close()
    elif intent.intent == "send_google_chat":
        google_chat.send_google_chat_message(args.get("message") or "")
    elif intent.intent == "assistant_command":
        task_extractor.ingest_tasks_from_text(omi_uid, args.get("command") or args.get("text", ""))


def process_realtime_payload(
    payload: Any,
    omi_uid: Optional[str],
    session_id: Optional[str] = None,
) -> dict:
    segments: list[dict] = []
    if isinstance(payload, list):
        segments = payload
    elif isinstance(payload, dict):
        segments = payload.get("segments") or payload.get("transcript_segments") or []
        if payload.get("text"):
            segments = [{"text": payload.get("text")}]

    stored = _store_segments(omi_uid, session_id, segments)
    full_text = join_transcript_segments(segments)

    routed = None
    if full_text and omi_uid:
        routed = router.route_text(full_text)
        if routed:
            _handle_routed_intent(omi_uid, routed)
        elif any(
            kw in full_text.lower()
            for kw in ("remind me", "don't forget", "i need to", "add to my tasks")
        ):
            task_extractor.ingest_tasks_from_text(omi_uid, full_text)

    return {
        "segments_stored": len(stored),
        "routed": routed.intent if routed else None,
    }


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
