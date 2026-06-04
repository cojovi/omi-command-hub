# Omi Command Hub

Central backend for Omi.me integration apps: webhooks, Chat Tools, async workers, Postgres, and integrations (OpenAI, Notion, Google Chat).

## Quick start

```bash
cd /home/cojovi/cojo_omi/omi-command-hub
cp .env.example .env
# Edit .env: set POSTGRES_PASSWORD, OMI_WEBHOOK_SECRET, API keys

docker compose up -d --build
docker compose exec api alembic upgrade head
curl http://localhost:8000/health
# or via nginx (default host port 8080 if 80 is taken):
curl http://localhost:8080/health
```

## Services

| Service | Port | Role |
|---------|------|------|
| omi-bridge-proxy | 80 (internal) | Registers `omi.cojovi.com` with **nginx-proxy** (same stack as OpenWebUI) |
| nginx (omi_nginx) | `127.0.0.1:8080` only | App reverse proxy; not bound to public 80/443 |
| api | 8000 | FastAPI |
| worker | — | RQ job processor |
| postgres | 5432 (internal) | Database |
| redis | 6379 (internal) | Job queue |

### Public HTTPS (nginx-proxy)

This VM already runs `nginx-proxy` + `nginx-proxy-acme` for OpenWebUI (`reroof.cmacroofing.com`). Omi uses the same proxy:

```
Internet → nginx-proxy:443 → omi_bridge_proxy → omi_nginx → api
```

Do **not** bind Omi to host ports 80/443. The `omi-bridge-proxy` service sets `VIRTUAL_HOST=omi.cojovi.com` so docker-gen adds a vhost automatically.

## Public endpoints

```
GET  /health
POST /webhooks/omi/memory?uid=UID&secret=SECRET
POST /webhooks/omi/realtime?uid=UID&session_id=SID&secret=SECRET
POST /webhooks/omi/audio?uid=UID&secret=SECRET
POST /webhooks/omi/daily-summary?uid=UID&secret=SECRET
GET  /.well-known/omi-tools.json
POST /omi/tools/<tool_name>
GET  /admin/events          (HTTP basic auth)
```

Legacy routes (set `LEGACY_OMI_ROUTES=1`):

```
POST /omi/transcript
POST /omi/chat
```

## Omi Developer Settings

**Setup Completed URL** (required if you configured this field in the Omi app — wrong URL causes “setup is completed” errors on Enable):

```
https://omi.cojovi.com/setup/status
```

Omi will call it as `GET .../setup/status?uid=YOUR_UID`. Response must be `{"is_setup_completed": true}`.

Do **not** use `/health` for setup — it returns a different JSON shape.

Point your Integration App webhooks to:

```
https://omi.cojovi.com/webhooks/omi/memory?secret=YOUR_SECRET
https://omi.cojovi.com/webhooks/omi/realtime?secret=YOUR_SECRET
https://omi.cojovi.com/webhooks/omi/daily-summary?secret=YOUR_SECRET
```

Chat Tools manifest URL:

```
https://omi.cojovi.com/.well-known/omi-tools.json
```

Security: use `?secret=` query param and/or `X-Omi-Signature: sha256=...` HMAC (`OMI_SIGNING_SECRET`).

## VM setup (first time)

```bash
chmod +x scripts/*.sh
./scripts/install_vm.sh
# Log out and back in for docker group
./scripts/deploy.sh
```

## Database migrations

```bash
docker compose exec api alembic upgrade head
```

## Backups

```bash
./scripts/backup_db.sh
# Optional cron: 0 3 * * * cd /path/to/omi-command-hub && ./scripts/backup_db.sh
```

## HTTPS / DNS (omi.cojovi.com)

1. **A record** `omi.cojovi.com` → VM IP (e.g. via Cloudflare).
2. Ensure `omi-bridge-proxy` is running (`docker compose up -d`).
3. `nginx-proxy-acme` will request a Let's Encrypt cert when it sees `LETSENCRYPT_HOST=omi.cojovi.com`.
4. Set `APP_BASE_URL=https://omi.cojovi.com` in `.env`.

Verify:

```bash
curl -s https://omi.cojovi.com/health
```

Local debug (not public):

```bash
curl -s http://127.0.0.1:8080/health
```

If Cloudflare proxies HTTPS, use **Full** SSL mode so origin cert from Let's Encrypt works.

## Environment variables

See [`.env.example`](.env.example). Minimum for production traffic:

- `DATABASE_URL`, `POSTGRES_PASSWORD`, `REDIS_URL`
- `OMI_WEBHOOK_SECRET`
- `OMI_APP_ID`, `OMI_APP_SECRET` (notifications)
- `OPENAI_API_KEY`
- `ADMIN_PASSWORD` (admin routes)

## Architecture

Omi → nginx → FastAPI (fast ack) → Redis queue → worker → Postgres / OpenAI / Notion / Google Chat / Omi API

Every webhook stores a raw `webhook_events` row before processing.
