import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger()


def send_omi_notification(uid: str, message: str) -> bool:
    settings = get_settings()
    if not (settings.omi_app_id and settings.omi_app_secret and settings.omi_notify):
        return False
    try:
        url = f"{settings.omi_api_base.rstrip('/')}/v2/integrations/{settings.omi_app_id}/notification"
        params = {"uid": uid, "message": message}
        headers = {
            "Authorization": f"Bearer {settings.omi_app_secret}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=10.0) as client:
            r = client.post(url, params=params, headers=headers)
            if r.status_code >= 300:
                logger.warning("omi_notification_failed", status=r.status_code, body=r.text)
                return False
            return True
    except Exception as e:
        logger.exception("omi_notification_error", error=str(e))
        return False
