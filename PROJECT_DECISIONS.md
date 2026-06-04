# Project Decisions — Omi Command Hub

## Architecture

- **Single hub backend** for all Omi apps (webhooks + Chat Tools), not one server per app.
- **Fast path webhooks**: validate → `webhook_events` → Redis RQ → 200 OK; no OpenAI/Notion in the HTTP handler.
- **Postgres** is the system of record; SQLite from `super_c_omi.py` was not carried forward.

## Security

- Supports **query `?secret=`** (strategy doc) and **`X-Omi-Signature` HMAC** (from prototype).
- Home Assistant calls use a **whitelist** only (`app/services/home_assistant.py`).

## Deployment

- Docker Compose: `api`, `worker`, `postgres`, `redis`, `nginx`, `omi-bridge-proxy`.
- **Public HTTPS** uses existing `nginx-proxy` + `nginx-proxy-acme` (same as OpenWebUI `reroof.cmacroofing.com`). `omi-bridge-proxy` sets `VIRTUAL_HOST=omi.cojovi.com` and forwards to host port **8080** (`omi_nginx`). Omi does **not** bind host 80/443.
- Internal/debug: `http://127.0.0.1:8080/health`.
- Schema managed by **Alembic** migration `001`; do not rely on `create_all` at startup.

## Omi API alignment

- Chat Tools manifest at `/.well-known/omi-tools.json` with per-tool POST endpoints (per official docs).
- Daily summary uses **`summary_json`** when present.
- Audio webhook is a **stub** in v1 (metadata logged only).

## Ported from `super_c_omi.py`

- Task extraction prompts and Notion property mapping → `openai_service.py`, `notion.py`, `task_extractor.py`
- Omi notifications → `omi_notifications.py`
- 7-day fingerprint dedupe → Postgres unique `(omi_uid, fingerprint)` on `action_items`
