import json
from typing import Any, Optional

from openai import OpenAI

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger()

CONV_PROMPT = """You analyze conversation transcripts to extract reminder/task intents.
Output JSON only with tasks array. Each task: title, due_iso, priority, tags, people, location, notes, fingerprint.
Only create tasks for explicit commitments. fingerprint = lowercased(title + due_iso or 'none')."""

CHAT_PROMPT = """You are Task Scribe for quick task capture from chat.
Output JSON only with tasks array. Each task: title, due_iso, priority, tags, people, location, notes, fingerprint."""

STRICT_SUFFIX = "\nReturn ONLY valid JSON matching the output spec. No prose."


def _client() -> OpenAI:
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY not configured")
    return OpenAI(api_key=settings.openai_api_key)


def _chat_json(system: str, user: str) -> dict:
    settings = get_settings()
    client = _client()
    resp = client.chat.completions.create(
        model=settings.openai_model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system + STRICT_SUFFIX},
            {"role": "user", "content": user},
        ],
        temperature=0.1,
    )
    raw = resp.choices[0].message.content or "{}"
    return json.loads(raw)


def extract_action_items(transcript: str) -> list[dict]:
    try:
        data = _chat_json(CONV_PROMPT, transcript)
        return data.get("tasks", [])
    except Exception as e:
        logger.exception("extract_action_items_failed", error=str(e))
        return []


def summarize_memory(transcript: str) -> dict:
    system = (
        "Summarize this Omi memory conversation. Return JSON with: "
        "title, overview, action_items (list of {description, priority})."
    )
    try:
        return _chat_json(system, transcript)
    except Exception as e:
        logger.exception("summarize_memory_failed", error=str(e))
        return {"title": "Memory", "overview": transcript[:500], "action_items": []}


def classify_intent(text: str) -> dict:
    system = (
        "Classify user intent from spoken text. Return JSON: "
        "intent (create_task|save_note|send_google_chat|assistant_command|log_business_idea|none), "
        "confidence (0-1), arguments (title, body, message, command as applicable)."
    )
    try:
        return _chat_json(system, text)
    except Exception as e:
        logger.exception("classify_intent_failed", error=str(e))
        return {"intent": "none", "confidence": 0.0, "arguments": {}}


def clean_transcript(text: str) -> str:
    if not text:
        return ""
    return text.strip()
