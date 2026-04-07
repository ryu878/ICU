# Specification: Architecture and MVP (Team Lead)

Format: **EPIC → User Stories → Tasks** with decisions recorded.

---

## EPIC 1 — Architecture and baseline stack

### User Story 1.1 — Choose and lock the technology stack

| Task | Decision |
|------|----------|
| Single client stack (desktop + mobile) | **Flutter** — one codebase for Android, iOS, Windows, macOS, Linux. Alternative: React Native + separate desktop (harder to keep unified). |
| Backend | **Python 3.12+**, **FastAPI** + **Uvicorn** — REST and WebSocket in one app, async, typing. |
| Realtime | **WebSocket** (Starlette/FastAPI); with multiple instances — **Redis Pub/Sub** for fan-out. A separate broker (Kafka, etc.) is not required for MVP. |
| Database and cache | **PostgreSQL** — users, conversations, messages, durable history. **Redis** — OTP, rate limits, presence, optional session cache. |
| Email for codes | External **transactional email** (SendGrid / AWS SES / Postmark / Resend): API from backend, no self-hosted SMTP in production. |
| Files (future-ready) | **S3-compatible** storage (S3, R2, MinIO in dev); DB holds `bucket`, `key`, `mime`, size. No uploads in MVP. |

**Rationale:** one client framework lowers feature cost; FastAPI + PostgreSQL + Redis is the smallest viable path for chat with WebSocket and horizontal scaling without extra infrastructure.

### User Story 1.2 — High-level architecture

- **Overview:** clients (Flutter) ↔ **HTTPS REST** + **WSS** ↔ API/realtime layer ↔ **PostgreSQL** (source of truth) + **Redis** (ephemeral data, pub/sub, presence).
- **Backend boundary:** business rules, authorization, idempotency, message ordering, token issuance — server-side only.
- **Dedicated realtime service:** not required for MVP — one service with WS + Redis pub/sub when running >1 replica. Split out a WS gateway when load demands it.
- **Interaction style:** **REST** + **WebSocket** (chat events, presence, delivery acks).
- **Data flow:** send → write to PG → publish to Redis → deliver over WS; offline clients catch up via REST after reconnect.
- **Source of truth:** **PostgreSQL** for messages and profiles; Redis is not the message history source.

---

## EPIC 2 — Authentication and accounts

### User Story 2.1 — Email registration with OTP

- **Flow:** enter email → `POST /auth/request-otp` → email with **6-digit** code → enter code → confirm.
- **Code generation and lifetime:** cryptographically strong 100000–999999; store in Redis with TTL **5–10 minutes** (hash the code, no plaintext in logs).
- **Rate limit / cooldown:** per email — at most 1 OTP / **60 s**, cap **N requests/hour** (e.g. 5); soft limit per IP.
- **Brute-force protection:** after **5 wrong** attempts — lock OTP key for **15–30 min** or until a new code is sent; counter in Redis.
- **Resend:** new code invalidates the old one; respect cooldown.

### User Story 2.2 — Confirmation and account creation

- **Code validation:** match Redis, TTL, lock after too many attempts.
- **User creation:** PostgreSQL transaction; UIN details in [uin.md](uin.md).
- **Baseline profile:** `uin`, `email`, `display_name`, `avatar_url` (null), `created_at`.

### User Story 2.3 — Sessions and sign-in

- **Tokens:** **JWT access** (short TTL, 15–30 min) + **opaque refresh** (Redis/table, long TTL, rotation).
- **Device/session:** `sessions` / `refresh_tokens`: `user_id`, `device_id` (UUID from client), `user_agent`, `created_at`, `last_used_at`, `revoked_at`.
- **Trusted device:** refresh stored on client (secure storage); server stores refresh hash and metadata.
- **Logout:** revoke refresh; optional access blacklist (short access TTL reduces need).
- **Invalidation:** “sign out everywhere” — revoke all refresh tokens for the user.

---

## EPIC 3 — Client applications

### User Story 3.1 — Single client for all platforms

- **UI stack:** Flutter + Material/Cupertino adaptation.
- **Platform specifics:** push (FCM/APNs), iOS background limits, system tray / desktop windows, desktop hotkeys.
- **UI adaptation:** breakpoints; desktop — master-detail (list + chat); mobile — navigation stack.
- **Updates:** app stores for mobile; desktop — auto-update or manual version check.

### User Story 3.2 — MVP screens

- Auth screen (email → code).
- Conversation list.
- Chat screen.
- Profile screen.
- Navigation: shell with bottom bar (mobile) / master-detail (desktop).

### User Story 3.3 — Client behavior

- **Offline:** outbound queue (local store); cached history for read-only viewing.
- **Retry:** exponential backoff (REST); WS reconnect with jitter.
- **Message status:** sending / sent / delivered / failed (shown on the bubble).
- **Sync on reconnect:** `GET` history with `since_message_id` or cursor.

---

## EPIC 4 — Chats and messages

### User Story 4.1 — Direct (1:1) conversations

- **Model:** `conversations` (type direct), `conversation_members`; unique user pair for direct.
- **Create/find:** idempotent “open chat with `user_uin`”.

### User Story 4.2 — Sending messages

- **Flow:** `client_message_id` (UUID) → `POST .../messages` with idempotency → persist, response with server `id`, seq, timestamp.
- **Ordering:** `seq` per conversation or `created_at` + `id` as tie-break.
- **Idempotency:** unique index `(conversation_id, client_message_id)`.

### User Story 4.3 — Message status

- Minimum: **sent**, **delivered**; optional **read**.
- Updates via WS + REST for sync.
- Storage: per-message and/or per-recipient for read.

---

## EPIC 5 — Realtime layer

### User Story 5.1 — WebSocket connection

- **Channel:** WSS, JSON frames.
- **Lifecycle:** connect → auth (access JWT) → subscribe to channels → heartbeat.
- **Reconnect:** exponential backoff, max delay; optional resume with `last_event_id`.

### User Story 5.2 — Message delivery

- **Fan-out:** by `user_id` → active connections in Redis; cross-server — pub/sub.
- **Fallback:** no WS — REST polling or wait for reconnect; PG write always happens.

### User Story 5.3 — Presence (basic)

- online/offline in Redis, TTL **30–60 s**, renewed by WS heartbeat.

---

## EPIC 6 — Backend and API

### User Story 6.1 — API layer

- Layout: `/v1/auth/*`, `/v1/users/*`, `/v1/conversations/*`, `/v1/messages/*`.
- **REST** is primary; unified error shape (code, message, `request_id`).
- **Versioning:** `/v1` prefix; breaking changes → `v2`.

### User Story 6.2 — User logic

- MVP: minimal CRUD on own profile; user lookup **by UIN** (exact match).

### User Story 6.3 — Message logic

- Writes with idempotency; history with cursor pagination; source of truth — PostgreSQL.

---

## EPIC 7 — Data storage

### User Story 7.1 — Primary store

- Relational **PostgreSQL**; users, chats, messages, refresh sessions.

### User Story 7.2 — Cache and ephemeral data

- **Redis:** OTP, rate limits, presence, pub/sub; TTL and eviction policy per key type.

### User Story 7.3 — Files (future-ready)

- External S3-compatible storage; URLs and metadata in DB; **not in MVP**.

---

## EPIC 8 — Non-functional requirements

### User Story 8.1 — Scalability

- Horizontal scaling of API behind a load balancer; stateless REST; WS + sticky sessions or shared state in Redis.
- Realtime scaling: multiple workers + Redis pub/sub.

### User Story 8.2 — Security

- HTTPS/WSS; input validation; rate limiting on auth and API; CORS allowlist; secrets in env/secret manager.

### User Story 8.3 — Logging and observability

- Structured (JSON) logs with `request_id`; key events (otp_sent, login, message_created).
- **Health:** `GET /health`, `GET /ready` (PostgreSQL + Redis).

---

## EPIC 9 — MVP scope limits

**Out of MVP:**

- group chats  
- calls  
- files  
- reactions  
- message editing  
- complex multi-device logic (basic sessions — yes)  

Architecture should allow extension. Over-engineering risk: microservices and a dedicated chat-only service before real load appears.

---

## EPIC 10 — Delivery plan

| Phase | Scope | Depends on |
|-------|--------|------------|
| **1** | Architecture, ADR, Auth (OTP + JWT/refresh) | — |
| **2** | DB schema, users, conversations, messages REST | Phase 1 |
| **3** | Client MVP: auth + list + chat + profile | Phase 2 |
| **4** | WebSocket, delivery, presence | Phase 2–3 |
| **5** | Hardening, load testing, observability | Phase 4 |

**MVP release:** Phase 3 + working Phase 4 (product minimum includes realtime delivery over WS).

---

## Related documents

- [uin.md](uin.md) — sequential UIN generation, atomicity, no reuse after deletion.
