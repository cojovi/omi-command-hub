import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger()


def send_google_chat_message(text: str, webhook_url: str | None = None) -> dict:
    settings = get_settings()
    url = webhook_url or settings.google_chat_webhook_url
    if not url:
        return {"ok": False, "error": "Google Chat webhook URL not configured"}
    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.post(url, json={"text": text})
            if r.status_code >= 300:
                logger.warning("google_chat_failed", status=r.status_code)
                return {"ok": False, "error": r.text}
            return {"ok": True}
    except Exception as e:
        logger.exception("google_chat_error", error=str(e))
        return {"ok": False, "error": str(e)}
