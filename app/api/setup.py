"""Omi integration app setup / enablement checks."""

from typing import Optional

from fastapi import APIRouter, Query

from app.core.config import get_settings

router = APIRouter(tags=["setup"])


def _setup_status(uid: Optional[str] = None) -> dict:
    """
    Omi calls the Setup Completed URL on enable with ?uid=...
    Must return: {"is_setup_completed": true|false}
    """
    settings = get_settings()
    # Hub is ready when webhook auth is configured (minimum for integration apps).
    ready = bool(settings.omi_webhook_secret)
    return {
        "is_setup_completed": ready,
        "uid": uid,
        "service": settings.app_name,
    }


@router.get("/setup/status")
def setup_status(uid: Optional[str] = Query(None)):
    return _setup_status(uid)


@router.get("/setup/check")
def setup_check(uid: Optional[str] = Query(None)):
    """Alias used by some Omi community plugins."""
    return _setup_status(uid)


@router.get("/")
def root(uid: Optional[str] = Query(None)):
    """
    Omi sometimes probes the app base URL on enable.
    Return setup shape when uid is present, otherwise a simple OK payload.
    """
    if uid is not None:
        return _setup_status(uid)
    settings = get_settings()
    return {"status": "ok", "service": settings.app_name}
