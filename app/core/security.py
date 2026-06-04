import hmac
import hashlib
import secrets
from typing import Optional

from fastapi import HTTPException, Request

from app.core.config import get_settings


def verify_webhook_secret(secret: Optional[str]) -> bool:
    settings = get_settings()
    if not settings.omi_webhook_secret:
        return True
    if not secret:
        return False
    return secrets.compare_digest(secret, settings.omi_webhook_secret)


def verify_hmac_signature(raw_body: bytes, header_sig: Optional[str]) -> bool:
    settings = get_settings()
    if not settings.omi_signing_secret:
        return True
    if not header_sig or not header_sig.startswith("sha256="):
        return False
    mac = hmac.new(
        settings.omi_signing_secret.encode(),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest("sha256=" + mac, header_sig)


async def validate_webhook_request(request: Request) -> bytes:
    """Validate webhook via query secret and/or HMAC header. Returns raw body."""
    settings = get_settings()
    raw = await request.body()

    secret_ok = verify_webhook_secret(request.query_params.get("secret"))
    hmac_ok = verify_hmac_signature(raw, request.headers.get("X-Omi-Signature"))

    if settings.omi_webhook_secret and settings.omi_signing_secret:
        if not (secret_ok or hmac_ok):
            raise HTTPException(status_code=401, detail="Unauthorized")
    elif settings.omi_webhook_secret and not secret_ok:
        raise HTTPException(status_code=401, detail="Unauthorized")
    elif settings.omi_signing_secret and not hmac_ok:
        raise HTTPException(status_code=401, detail="Unauthorized")

    return raw


def verify_admin_credentials(username: str, password: str) -> bool:
    settings = get_settings()
    if not settings.admin_password:
        return False
    return (
        secrets.compare_digest(username, settings.admin_username)
        and secrets.compare_digest(password, settings.admin_password)
    )
