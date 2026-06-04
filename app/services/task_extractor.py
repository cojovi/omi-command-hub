from datetime import datetime, timedelta
from typing import Optional

from sqlmodel import select

from app.core.logging import get_logger
from app.db.models import ActionItem
from app.db.session import get_session_sync
from app.services import google_chat, notion, omi_notifications, openai_service

logger = get_logger()


def fingerprint_for(title: str, due_iso: Optional[str] = None) -> str:
    return (title.lower().strip() + "|" + (due_iso or "none")).lower()


def within_dedupe_window(omi_uid: str, fp: str, days: int = 7) -> bool:
    session = get_session_sync()
    try:
        stmt = (
            select(ActionItem)
            .where(ActionItem.omi_uid == omi_uid, ActionItem.fingerprint == fp)
            .order_by(ActionItem.created_at.desc())
        )
        item = session.exec(stmt).first()
        if not item:
            return False
        return datetime.utcnow() - item.created_at < timedelta(days=days)
    finally:
        session.close()


def ingest_tasks_from_text(omi_uid: str, text: str, source_memory_id: Optional[str] = None) -> dict:
    tasks_raw = openai_service.extract_action_items(text)
    created = 0
    skipped = 0
    session = get_session_sync()
    try:
        for item in tasks_raw:
            title = (item.get("title") or "").strip()
            if not title:
                continue
            due_iso = item.get("due_iso")
            fp = item.get("fingerprint") or fingerprint_for(title, due_iso)
            if within_dedupe_window(omi_uid, fp):
                skipped += 1
                continue

            notion_result = notion.create_task_page(
                title=title,
                due_at=due_iso,
                priority=item.get("priority") or "med",
                tags=item.get("tags") or [],
                people=item.get("people") or [],
                location=item.get("location"),
                notes=item.get("notes"),
                fingerprint=fp,
            )

            action = ActionItem(
                omi_uid=omi_uid,
                source_memory_id=source_memory_id,
                title=title,
                description=item.get("notes"),
                status="open",
                fingerprint=fp,
                priority=item.get("priority") or "med",
                tags=item.get("tags") or [],
                people=item.get("people") or [],
                location=item.get("location"),
                notes=item.get("notes"),
                external_id=notion_result.get("page_id") if notion_result.get("ok") else None,
                destination="notion" if notion_result.get("ok") else None,
            )
            session.add(action)
            session.commit()
            created += 1

            due = due_iso or "no date"
            msg = f"✅ Added: {title} — {due}."
            omi_notifications.send_omi_notification(omi_uid, msg)
            google_chat.send_google_chat_message(msg)

        return {"created": created, "skipped": skipped, "total": len(tasks_raw)}
    finally:
        session.close()


def create_task_manual(
    omi_uid: str,
    title: str,
    description: Optional[str] = None,
    due_at: Optional[str] = None,
) -> dict:
    fp = fingerprint_for(title, due_at)
    if within_dedupe_window(omi_uid, fp):
        return {"ok": True, "skipped": True, "reason": "duplicate"}
    notion_result = notion.create_task_page(
        title=title,
        description=description,
        due_at=due_at,
        fingerprint=fp,
    )
    session = get_session_sync()
    try:
        action = ActionItem(
            omi_uid=omi_uid,
            title=title,
            description=description,
            fingerprint=fp,
            external_id=notion_result.get("page_id"),
            destination="notion" if notion_result.get("ok") else None,
        )
        session.add(action)
        session.commit()
        msg = f"✅ Task created: {title}"
        omi_notifications.send_omi_notification(omi_uid, msg)
        return {"ok": True, "task_id": action.id}
    finally:
        session.close()
