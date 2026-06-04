import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger()

# Whitelist: domain -> allowed services -> entity_id patterns
WHITELIST: dict[str, dict[str, list[str]]] = {
    "light": {
        "turn_on": ["light.office", "light.living_room"],
        "turn_off": ["light.office", "light.living_room"],
    },
    "switch": {
        "turn_on": ["switch.focus_mode"],
        "turn_off": ["switch.focus_mode"],
    },
}


def call_service(
    domain: str,
    service: str,
    entity_id: str,
    data: dict | None = None,
) -> dict:
    settings = get_settings()
    if not (settings.home_assistant_base_url and settings.home_assistant_token):
        return {"ok": False, "error": "Home Assistant not configured"}

    allowed = WHITELIST.get(domain, {}).get(service, [])
    if entity_id not in allowed:
        return {"ok": False, "error": f"Entity {entity_id} not in whitelist for {domain}.{service}"}

    url = f"{settings.home_assistant_base_url.rstrip('/')}/api/services/{domain}/{service}"
    payload = {"entity_id": entity_id, **(data or {})}
    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.post(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {settings.home_assistant_token}",
                    "Content-Type": "application/json",
                },
            )
            if r.status_code >= 300:
                return {"ok": False, "error": r.text}
            return {"ok": True, "result": r.json() if r.content else {}}
    except Exception as e:
        logger.exception("home_assistant_error", error=str(e))
        return {"ok": False, "error": str(e)}
