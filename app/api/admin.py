from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlmodel import select

from app.core.config import get_settings
from app.core.security import verify_admin_credentials
from app.db.models import Memory, ToolCall, WebhookEvent
from app.db.session import get_session_sync
from app.services.webhook_store import replay_webhook_event

router = APIRouter(prefix="/admin", tags=["admin"])
security = HTTPBasic()


def require_admin(credentials: HTTPBasicCredentials = Depends(security)):
    if not verify_admin_credentials(credentials.username, credentials.password):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials


@router.get("/events")
def list_events(
    limit: int = 50,
    status: Optional[str] = None,
    _=Depends(require_admin),
):
    session = get_session_sync()
    try:
        stmt = select(WebhookEvent).order_by(WebhookEvent.received_at.desc()).limit(limit)
        if status:
            stmt = stmt.where(WebhookEvent.status == status)
        events = session.exec(stmt).all()
        return {
            "events": [
                {
                    "id": e.id,
                    "event_type": e.event_type,
                    "omi_uid": e.omi_uid,
                    "status": e.status,
                    "received_at": e.received_at.isoformat(),
                    "error": e.error,
                }
                for e in events
            ]
        }
    finally:
        session.close()


@router.get("/memories")
def list_memories(limit: int = 50, _=Depends(require_admin)):
    session = get_session_sync()
    try:
        stmt = select(Memory).order_by(Memory.created_at.desc()).limit(limit)
        rows = session.exec(stmt).all()
        return {
            "memories": [
                {
                    "id": m.id,
                    "omi_memory_id": m.omi_memory_id,
                    "title": m.title,
                    "omi_uid": m.omi_uid,
                    "created_at": m.created_at.isoformat(),
                }
                for m in rows
            ]
        }
    finally:
        session.close()


@router.get("/tool-calls")
def list_tool_calls(limit: int = 50, _=Depends(require_admin)):
    session = get_session_sync()
    try:
        stmt = select(ToolCall).order_by(ToolCall.created_at.desc()).limit(limit)
        rows = session.exec(stmt).all()
        return {
            "tool_calls": [
                {
                    "id": t.id,
                    "tool_name": t.tool_name,
                    "omi_uid": t.omi_uid,
                    "status": t.status,
                    "created_at": t.created_at.isoformat(),
                    "error": t.error,
                }
                for t in rows
            ]
        }
    finally:
        session.close()


@router.post("/events/{event_id}/replay")
def replay_event(event_id: str, _=Depends(require_admin)):
    return replay_webhook_event(event_id)
