# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Club Maravilha is a management system for a sports club with about 300 members. It is a monorepo with three services and a Postgres database, run together by `docker-compose.yml`:

- `backend/`: FastAPI with Python 3.11 and async SQLAlchemy 2.0 (asyncpg). It also runs the billing scheduler and the WhatsApp send queue in-process.
- `frontend/`: React 18, Vite, TypeScript and Tailwind.
- `whatsapp-engine/`: a Node 20/TypeScript microservice wrapping Baileys. The backend calls it over HTTP with the `x-api-key` header. Its README still calls it a "placeholder", but it is fully implemented.

Domain language is Brazilian Portuguese (associados, faturas, convidados, régua de cobrança, catraca). Write identifiers, comments, docstrings, test names and commit messages in Portuguese to match. Commits use Conventional Commits with a Portuguese subject, e.g. `feat(cobranca): ...` or `refactor(admin): aplica melhorias de code review em ...`. Features are built with TDD as three commits: `test(...)`, then `feat(...)`, then `refactor(...)` after code review.

## Commands

### Backend (run from `backend/`; the venv is at `backend/.venv`)
```powershell
.\.venv\Scripts\pytest.exe                                          # full suite (SQLite in memory, asyncio_mode=auto)
.\.venv\Scripts\pytest.exe tests/unit/test_catraca_service.py       # one file
.\.venv\Scripts\pytest.exe tests/unit/test_catraca_service.py -k nome_do_teste
python -m scripts.migrate     # prepare DB: empty DB -> create_all + `alembic stamp head`; existing DB -> `alembic upgrade head`
python -m scripts.seed_admin  # idempotent admin seed from ADMIN_EMAIL / ADMIN_PASSWORD
```
The tests in `tests/integration/test_postgres_opcional.py` are skipped unless `TEST_POSTGRES_URL` is set. They cover Postgres-only SQL semantics and concurrency.

### Frontend (run from `frontend/`)
```bash
npm run dev
npm run build          # tsc -b && vite build (this is the type check)
npm test               # vitest run
npx vitest run src/admin/pages/MensalidadesPage.test.tsx
```
`npm run lint` is defined, but eslint is not in devDependencies.

### WhatsApp engine (run from `whatsapp-engine/`)
```bash
npm run dev            # tsx watch
npm run typecheck
npm test
npx vitest run src/services/baileys.service.test.ts
```

### Docker
```bash
docker compose up -d --build
docker compose exec backend python -m scripts.migrate
docker compose down -v      # also wipes the DB and the WhatsApp session volume
```
Local ports: frontend 5173, API 8000 (Swagger at `/docs`), engine 3001 (loopback only), Postgres `${POSTGRES_PORT}`. On this machine Postgres is mapped to 5433 because a native Postgres already uses 5432. After adding npm packages, run `npm install` inside the frontend container, because `node_modules` lives in an anonymous volume.

## Backend architecture

- **Layers:** `api/v1/endpoints` → `services` → `repositories` → `models`, with Pydantic DTOs in `schemas`. Services raise `fastapi.HTTPException` directly for business-rule violations.
- **Auth boundary** (`api/v1/api.py`): public routers (health, auth, catraca, webhooks) are mounted on `api_router`. Every admin router is mounted on `admin_router`, which has `Depends(get_current_admin)` (JWT). A new admin router goes under `admin_router` so it is protected automatically.
- **Schema management is a hybrid:**
  - On startup, the API runs `Base.metadata.create_all`. This creates new tables but never alters existing ones.
  - The Alembic history is a chain of deltas on top of a schema built by `create_all`, so `alembic upgrade head` cannot build a database from scratch. That is why `scripts/migrate.py` exists.
  - Migrations must be idempotent against tables `create_all` may already have made. For an example, see the `sa.inspect(...).get_table_names()` check in `e5a1b2c3d4e5`.
  - Production (`docker-compose.prod.yml`) runs `scripts.migrate && uvicorn ... --workers 1`.
- **Time:** always use `app/core/clock.py` (`agora_clube()` / `hoje_clube()`, `settings.TIMEZONE`). Never use a naive `date.today()` or `datetime.now()`, because containers run in UTC.
- **DB portability:** code runs on Postgres in production and on SQLite in tests. For dialect-specific upserts (`INSERT ... ON CONFLICT`), use `repositories/_dialect.insert_do_dialeto(session.bind.dialect.name)`.
- **Billing flow** (`jobs/billing_scheduler.py` and `services/billing_engine_service.py`):
  - APScheduler runs a daily job at `Configuracao.horario_disparo`. It marks overdue invoices, then runs the reminder sequence (régua): D-3, D0, D+3 and D+7.
  - Each step's messages are enqueued on a single global `WhatsAppQueueService`. This is an in-memory priority queue whose worker waits a random anti-ban delay after each send.
  - Idempotency comes from `logs_mensagens` (fatura_id + etapa).
  - Business constants are in `core/constants.py`. The D+7 reminder does not change member status. A member becomes INADIMPLENTE and is blocked at the turnstile (catraca) only after `DIAS_CARENCIA_BLOQUEIO` (30) days overdue.
  - The scheduler and worker run only when `ENVIRONMENT != "test"` and `SCHEDULER_ENABLED` is on. They must run in exactly one process, which is why production uses `--workers 1`.
- **WhatsApp providers** (`services/whatsapp_service.py`): `get_whatsapp_provider()` returns `MockWhatsAppProvider` or `BaileysWhatsAppProvider` based on `WHATSAPP_PROVIDER`. An unknown value makes startup fail.
- **Configuration:** `configuracoes` is a singleton row (`id = 1`) read through `ConfiguracaoRepository.get_or_create()`. It holds the fee amounts, guest quota, Pix key, reminder schedule and on/off switch, and the message templates (rendered by `template_service`).

### Backend tests
- `tests/conftest.py` forces `WHATSAPP_PROVIDER=MOCK` before `app` is imported, and recreates an in-memory SQLite schema for every test with `PRAGMA foreign_keys=ON`.
- `async_client` overrides `get_current_admin` with a fake admin.
- `async_client_sem_auth` exercises real JWT auth. Don't use both fixtures in one test, because they share `app.dependency_overrides`.
- The login rate limiter is global in-memory state and is reset by an autouse fixture.
- Files named `test_featureN_review*.py` and `*.review.test.tsx` hold regression tests added after code reviews.

## Frontend architecture

- `src/Root.tsx` splits on pathname:
  - `/admin/*` loads `src/admin/AdminApp`, the real admin panel. It uses react-router, react-query, axios `admin/api/client.ts` with a JWT in localStorage, and `ProtectedRoute`.
  - Every other path loads `src/App.tsx`, the public landing page and member-portal mockups. These use hash-based navigation and the legacy `components/` tree (including a mock `components/admin/AdminDashboardPage.tsx`, which is not the real admin).
- The API base URL is `VITE_API_URL` plus `/api/v1`.
- Tests use Vitest with jsdom and MSW:
  - `src/test/setup.ts` sets `onUnhandledRequest: 'error'`, so every HTTP call in a test needs a handler (`src/test/handlers.ts`, or `server.use(...)` in the test).
  - The test API origin is `http://api.test`, and TZ is fixed to `America/Sao_Paulo`.
  - `vitest.config.ts` aliases axios to its browser build so multipart uploads work under jsdom.

## Related docs
- `DEPLOY.md`: VPS deployment with `docker-compose.prod.yml` and nginx (`docker/nginx`).
- `ROADMAP.md`: next phases (member portal, court booking, turnstile integration).
- `RELATORIO_MVP.md`: MVP delivery report.
- `.env.example`: every environment variable, with comments. `WHATSAPP_API_KEY` and `POSTGRES_PASSWORD` are required in production.
