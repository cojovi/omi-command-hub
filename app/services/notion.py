import json
from typing import Any, Optional

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger()


def create_task_page(
    title: str,
    description: Optional[str] = None,
    due_at: Optional[str] = None,
    priority: str = "med",
    tags: Optional[list[str]] = None,
    people: Optional[list[str]] = None,
    location: Optional[str] = None,
    notes: Optional[str] = None,
    fingerprint: Optional[str] = None,
) -> dict:
    settings = get_settings()
    if not (settings.notion_token and settings.notion_database_id):
        return {"ok": False, "skipped": True, "reason": "Notion not configured"}

    props: dict[str, Any] = {
        settings.notion_prop_name: {"title": [{"type": "text", "text": {"content": title}}]},
        settings.notion_prop_priority: {"select": {"name": (priority or "med").capitalize()}},
        settings.notion_prop_tags: {
            "multi_select": [{"name": t} for t in (tags or [])],
        },
        settings.notion_prop_people: {
            "multi_select": [{"name": p} for p in (people or [])],
        },
        settings.notion_prop_location: {
            "rich_text": [{"type": "text", "text": {"content": location}}],
        }
        if location
        else {"rich_text": []},
        settings.notion_prop_notes: {
            "rich_text": [{"type": "text", "text": {"content": notes or description or ""}}],
        },
    }
    if fingerprint:
        props[settings.notion_prop_fingerprint] = {
            "rich_text": [{"type": "text", "text": {"content": fingerprint}}],
        }
    if due_at:
        props[settings.notion_prop_due] = {"date": {"start": due_at}}
    else:
        props[settings.notion_prop_due] = {"date": None}

    payload = {"parent": {"database_id": settings.notion_database_id}, "properties": props}
    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.post(
                "https://api.notion.com/v1/pages",
                headers={
                    "Authorization": f"Bearer {settings.notion_token}",
                    "Notion-Version": "2022-06-28",
                    "Content-Type": "application/json",
                },
                content=json.dumps(payload),
            )
            if r.status_code >= 300:
                logger.warning("notion_create_failed", status=r.status_code, body=r.text)
                return {"ok": False, "error": r.text}
            data = r.json()
            return {"ok": True, "page_id": data.get("id")}
    except Exception as e:
        logger.exception("notion_create_error", error=str(e))
        return {"ok": False, "error": str(e)}


def create_note_page(title: str, body: str, tags: Optional[list[str]] = None) -> dict:
    return create_task_page(
        title=title,
        notes=body,
        tags=tags,
        priority="low",
    )
