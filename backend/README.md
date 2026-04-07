# ICU backend

FastAPI service: auth (email OTP), JWT access + refresh, sequential UIN, direct conversations and messages.

## Run in Docker (recommended)

From the **repository root**:

```bash
docker compose up -d --build
```

API: http://127.0.0.1:8000/docs  

The image applies migrations on startup (`alembic upgrade head`).

## Local run (Python app on the host)

### Prerequisites

- **Python 3.10+**
- **PostgreSQL** and **Redis** (e.g. `docker compose up -d postgres redis` from the repo root)

### Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
# Edit .env: point ICU_DATABASE_URL / ICU_REDIS_URL at localhost if DBs are exposed from Docker
alembic upgrade head
uvicorn icu.main:app --reload --host 0.0.0.0 --port 8000
```

## Endpoints (v1)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health`, `/ready` | Liveness / readiness (DB + Redis) |
| POST | `/v1/auth/request-otp` | Send OTP |
| POST | `/v1/auth/verify-otp` | Verify code, tokens + user |
| POST | `/v1/auth/refresh`, `/v1/auth/logout` | Refresh / revoke |
| GET | `/v1/users/me` | Current user (Bearer) |
| GET | `/v1/conversations` | List direct chats |
| POST | `/v1/conversations/direct` | Open or create 1:1 chat (`peer_uin`) |
| GET | `/v1/conversations/{id}/messages` | Message history (`before_id`, `limit`) |
| POST | `/v1/conversations/{id}/messages` | Send message (`client_message_id`, `body`) |
| POST | `/v1/conversations/{id}/receipts` | Receipts (`delivered_up_to_message_id` / `read_up_to_message_id`) |
| GET | `/v1/users/by-uin/{uin}` | User card by UIN (auth) |
| GET | `/v1/users/by-uin/{uin}/presence` | Online/offline (Redis; auth) |
| WS | `/v1/ws?token=…` | Realtime: welcome, ping/pong, JSON events (`new_message`, `receipt`) |

With `ICU_DEV_LOG_OTP=true`, the OTP is returned in `dev_code` on `request-otp` (for tests).

Optional **Resend** email: set `ICU_RESEND_API_KEY` and `ICU_RESEND_FROM_EMAIL` (see `.env.example`).

## Docker image

`backend/Dockerfile` builds the API; `docker-compose.yml` in the repo root wires `postgres`, `redis`, and `api`.
