# ICU
ICU (I See You) is a simple messenger ICQ-like style.

## Run everything in Docker

From the repository root:

```bash
docker compose up -d --build
```

- **API:** http://127.0.0.1:8000  
- **OpenAPI:** http://127.0.0.1:8000/docs  
- **PostgreSQL:** `localhost:5432` (user/password/db: `icu` / `icu` / `icu`)  
- **Redis:** `localhost:6379`

On startup the `api` container runs `alembic upgrade head`, then starts Uvicorn.

Optional env overrides (host shell): `ICU_JWT_SECRET`, `ICU_OTP_PEPPER` (see `docker-compose.yml`).

## Flutter client

See [flutter_app/README.md](flutter_app/README.md). After installing Flutter, run `flutter create .` inside `flutter_app/`, then `flutter pub get` and `flutter run` (set `API_BASE` if the API is not on `127.0.0.1:8000`).

## Documentation

See [docs/README.md](docs/README.md) (architecture, MVP scope, UIN).

## Backend (local development without Docker for the app)

See [backend/README.md](backend/README.md) — PostgreSQL and Redis are still easiest via `docker compose up -d postgres redis`.
