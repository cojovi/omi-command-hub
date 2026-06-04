import json
from typing import Optional

from fastapi import APIRouter, Request

from app.core.security import validate_webhook_request
from app.services.webhook_store import record_and_enqueue

router = APIRouter(prefix="/webhooks/omi", tags=["omi-webhooks"])
legacy_router = APIRouter(prefix="/omi", tags=["omi-legacy"])


def _parse_json_body(raw: bytes) -> dict | list:
    if not raw:
        return {}
    return json.loads(raw)


def _uid_from_request(request: Request, payload: dict | list) -> Optional[str]:
    uid = request.query_params.get("uid")
    if uid:
        return uid
    if isinstance(payload, dict):
        return payload.get("uid") or payload.get("user_id")
    return None


async def _handle_webhook(
    request: Request,
    event_type: str,
    job_type: str,
    extra: Optional[dict] = None,
):
    raw = await validate_webhook_request(request)
    try:
        payload = _parse_json_body(raw)
    except json.JSONDecodeError:
        payload = {"raw": raw.decode("utf-8", errors="replace") if raw else ""}

    omi_uid = _uid_from_request(request, payload if isinstance(payload, dict) else {})
    merged_extra = dict(extra or {})
    if request.query_params.get("session_id"):
        merged_extra["session_id"] = request.query_params.get("session_id")
    if request.query_params.get("sample_rate"):
        merged_extra["sample_rate"] = request.query_params.get("sample_rate")

    return record_and_enqueue(
        event_type=event_type,
        omi_uid=omi_uid,
        raw_payload=payload,
        headers=dict(request.headers),
        job_type=job_type,
        extra_payload=merged_extra,
    )


@router.post("/memory")
async def omi_memory_webhook(request: Request):
    return await _handle_webhook(request, "memory", "process_memory")


@router.post("/realtime")
async def omi_realtime_webhook(request: Request):
    return await _handle_webhook(request, "realtime_transcript", "process_realtime_segment")


@router.post("/audio")
async def omi_audio_webhook(request: Request):
    raw = await validate_webhook_request(request)
    omi_uid = request.query_params.get("uid")
    payload = {
        "content_length": len(raw),
        "sample_rate": request.query_params.get("sample_rate"),
        "stub": True,
    }
    return record_and_enqueue(
        event_type="audio",
        omi_uid=omi_uid,
        raw_payload=payload,
        headers=dict(request.headers),
        job_type="process_audio_chunk",
        extra_payload={"sample_rate": request.query_params.get("sample_rate")},
    )


@router.post("/daily-summary")
async def omi_daily_summary_webhook(request: Request):
    return await _handle_webhook(request, "daily_summary", "process_daily_summary")


@legacy_router.post("/transcript")
async def legacy_transcript(request: Request):
    return await omi_realtime_webhook(request)


@legacy_router.post("/chat")
async def legacy_chat(request: Request):
    return await omi_realtime_webhook(request)
