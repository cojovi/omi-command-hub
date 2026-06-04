from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlmodel import select

from app.core.logging import get_logger
from app.db.models import Memory, Note, ToolCall
from app.db.session import get_session_sync
from app.services import google_chat, home_assistant, notion, openai_service, task_extractor

router = APIRouter(tags=["omi-tools"])
logger = get_logger()

MANIFEST = {
    "tools": [
        {
            "name": "save_note",
            "description": "Save a note from the user's Omi conversation.",
            "endpoint": "/omi/tools/save_note",
            "method": "POST",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "body": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["body"],
            },
            "status_message": "Saving note...",
        },
        {
            "name": "create_task",
            "description": "Create a task from the user's Omi conversation.",
            "endpoint": "/omi/tools/create_task",
            "method": "POST",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "due_at": {"type": "string"},
                },
                "required": ["title"],
            },
            "status_message": "Creating task...",
        },
        {
            "name": "send_google_chat",
            "description": "Send a message to the configured Google Chat space.",
            "endpoint": "/omi/tools/send_google_chat",
            "method": "POST",
            "parameters": {
                "type": "object",
                "properties": {"message": {"type": "string"}},
                "required": ["message"],
            },
            "status_message": "Sending to Google Chat...",
        },
        {
            "name": "search_memories",
            "description": "Search stored Omi memories by keyword.",
            "endpoint": "/omi/tools/search_memories",
            "method": "POST",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer"},
                },
                "required": ["query"],
            },
            "status_message": "Searching memories...",
        },
        {
            "name": "summarize_recent_memories",
            "description": "Summarize the most recent stored memories.",
            "endpoint": "/omi/tools/summarize_recent_memories",
            "method": "POST",
            "parameters": {
                "type": "object",
                "properties": {"limit": {"type": "integer"}},
            },
            "status_message": "Summarizing recent memories...",
        },
        {
            "name": "trigger_home_assistant",
            "description": "Trigger a whitelisted Home Assistant action.",
            "endpoint": "/omi/tools/trigger_home_assistant",
            "method": "POST",
            "parameters": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string"},
                    "service": {"type": "string"},
                    "entity_id": {"type": "string"},
                },
                "required": ["domain", "service", "entity_id"],
            },
            "auth_required": True,
            "status_message": "Calling Home Assistant...",
        },
        {
            "name": "log_business_idea",
            "description": "Log a business idea as a tagged note.",
            "endpoint": "/omi/tools/log_business_idea",
            "method": "POST",
            "parameters": {
                "type": "object",
                "properties": {
                    "idea": {"type": "string"},
                    "title": {"type": "string"},
                },
                "required": ["idea"],
            },
            "status_message": "Logging business idea...",
        },
    ]
}


@router.get("/.well-known/omi-tools.json")
def omi_tools_manifest():
    return MANIFEST


def _persist_tool_call(
    uid: Optional[str],
    tool_name: str,
    arguments: dict,
    result: Optional[dict] = None,
    error: Optional[str] = None,
) -> ToolCall:
    session = get_session_sync()
    try:
        tc = ToolCall(
            omi_uid=uid,
            tool_name=tool_name,
            arguments=arguments,
            result=result,
            status="failed" if error else "completed",
            error=error,
            completed_at=datetime.utcnow(),
        )
        session.add(tc)
        session.commit()
        session.refresh(tc)
        return tc
    finally:
        session.close()


def execute_tool_internal(data: dict[str, Any]) -> dict:
    uid = data.get("uid") or data.get("user_id")
    tool_name = data.get("tool_name", "")

    try:
        if tool_name == "save_note":
            body = data.get("body") or ""
            title = data.get("title") or body[:80]
            session = get_session_sync()
            note = Note(omi_uid=uid or "unknown", title=title, body=body, tags=data.get("tags") or [])
            session.add(note)
            session.commit()
            notion.create_note_page(title, body, data.get("tags"))
            return {"result": f"Saved note: {title}"}

        if tool_name == "create_task":
            title = data.get("title") or ""
            r = task_extractor.create_task_manual(
                uid or "unknown",
                title=title,
                description=data.get("description"),
                due_at=data.get("due_at"),
            )
            if r.get("skipped"):
                return {"result": "Task already exists (duplicate)."}
            return {"result": f"Task created: {title}"}

        if tool_name == "send_google_chat":
            msg = data.get("message") or ""
            r = google_chat.send_google_chat_message(msg)
            if not r.get("ok"):
                return {"error": r.get("error", "Failed to send message")}
            return {"result": "Message sent to Google Chat."}

        if tool_name == "search_memories":
            query = (data.get("query") or "").lower()
            limit = int(data.get("limit") or 5)
            session = get_session_sync()
            stmt = select(Memory).order_by(Memory.created_at.desc()).limit(50)
            rows = session.exec(stmt).all()
            session.close()
            matches = []
            for m in rows:
                hay = f"{m.title or ''} {m.summary or ''} {m.transcript or ''}".lower()
                if query in hay:
                    matches.append(f"- {m.title or 'Untitled'}: {(m.summary or '')[:120]}")
                if len(matches) >= limit:
                    break
            if not matches:
                return {"result": f'No memories found for "{query}".'}
            return {"result": "Found memories:\n" + "\n".join(matches)}

        if tool_name == "summarize_recent_memories":
            limit = int(data.get("limit") or 3)
            session = get_session_sync()
            stmt = select(Memory).order_by(Memory.created_at.desc()).limit(limit)
            rows = session.exec(stmt).all()
            session.close()
            texts = [m.transcript or m.summary or "" for m in rows if m.transcript or m.summary]
            if not texts:
                return {"result": "No recent memories to summarize."}
            combined = "\n\n".join(texts)
            summary = openai_service.summarize_memory(combined)
            return {"result": summary.get("overview") or summary.get("title") or "Summary complete."}

        if tool_name == "trigger_home_assistant":
            r = home_assistant.call_service(
                data.get("domain", ""),
                data.get("service", ""),
                data.get("entity_id", ""),
                data.get("data"),
            )
            if not r.get("ok"):
                return {"error": r.get("error", "Home Assistant call failed")}
            return {"result": f"Triggered {data.get('domain')}.{data.get('service')} on {data.get('entity_id')}"}

        if tool_name == "log_business_idea":
            idea = data.get("idea") or ""
            title = data.get("title") or idea[:80]
            session = get_session_sync()
            note = Note(
                omi_uid=uid or "unknown",
                title=title,
                body=idea,
                tags=["business_idea"],
                source="chat_tool",
            )
            session.add(note)
            session.commit()
            notion.create_note_page(title, idea, ["business_idea"])
            return {"result": f"Logged business idea: {title}"}

        return {"error": f"Unknown tool: {tool_name}"}
    except Exception as e:
        logger.exception("tool_execution_failed", tool=tool_name, error=str(e))
        return {"error": "Tool execution failed. Please try again."}


async def _tool_handler(request: Request, tool_name: str):
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    data["tool_name"] = tool_name
    uid = data.get("uid") or data.get("user_id")

    result = execute_tool_internal(data)
    _persist_tool_call(
        uid,
        tool_name,
        data,
        result=result if "result" in result else None,
        error=result.get("error"),
    )

    if "error" in result:
        return JSONResponse(result, status_code=400)
    return result


@router.post("/omi/tools/save_note")
async def tool_save_note(request: Request):
    return await _tool_handler(request, "save_note")


@router.post("/omi/tools/create_task")
async def tool_create_task(request: Request):
    return await _tool_handler(request, "create_task")


@router.post("/omi/tools/send_google_chat")
async def tool_send_google_chat(request: Request):
    return await _tool_handler(request, "send_google_chat")


@router.post("/omi/tools/search_memories")
async def tool_search_memories(request: Request):
    return await _tool_handler(request, "search_memories")


@router.post("/omi/tools/summarize_recent_memories")
async def tool_summarize_recent(request: Request):
    return await _tool_handler(request, "summarize_recent_memories")


@router.post("/omi/tools/trigger_home_assistant")
async def tool_trigger_ha(request: Request):
    return await _tool_handler(request, "trigger_home_assistant")


@router.post("/omi/tools/log_business_idea")
async def tool_log_business_idea(request: Request):
    return await _tool_handler(request, "log_business_idea")
