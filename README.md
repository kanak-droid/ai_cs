# AstroHelp

An in-app AI support chatbot for astrologers on AstroLokal. Astrologers get instant, tool-backed
answers for payout/KYC/salary questions and a real ticket tracker for everything else; admins
triage and resolve tickets from a dashboard.

## Architecture

```
backend/            FastAPI + SQLAlchemy + Alembic + Postgres, Gemini tool-calling agent
chat-app/            Astrologer-facing chat webview (React + Vite), opened from a WebView
admin-app/           KAM/admin dashboard (React + Vite)
packages/shared/     Shared TypeScript types, status/color map, Tailwind design-token preset
docker-compose.yml   Postgres only — backend and both frontends run natively via their own tools
```

Backend layering (see `backend/app/`):

- `agent/` — the Gemini tool-calling orchestrator. Only imports `agent/tool_schemas.py` (pure
  data); never imports `integrations/` or `services/` directly.
- `agent/executor.py` — the one place that resolves a tool name to a handler and dispatches it.
  This is also the **security boundary**: it unconditionally strips whatever `astrologer_id`
  the model supplied in a tool call and replaces it with the id from the verified JWT, before any
  handler runs. Handlers never trust an `astrologer_id` from tool input.
- `integrations/` — mocked external systems (see below). Isolated, one file each.
- `services/` — cross-integration business logic (e.g. `ticket_service.create_ticket` does
  create → auto-assign → Slack-notify in one transaction). Routes and the agent never call
  integrations directly for anything that spans more than one system.
- `api/routes/` — thin FastAPI route handlers that call into `services/`.

## Prerequisites

- Python 3.12 (the repo's venv is built against this; earlier versions choke on `X | None`
  union syntax used throughout the SQLAlchemy 2.0 / Pydantic v2 code)
- Node.js 20+ and npm 10+ (npm workspaces — not pnpm/yarn)
- Docker (for Postgres via Docker Compose)

## Setup

### 1. Postgres

```bash
docker compose up -d
```

Brings up Postgres on `localhost:5434` (not 5432, to avoid clashing with other local Postgres
instances — see `docker-compose.yml`). Then create the two databases it expects:

```bash
docker exec astrohelp-postgres psql -U astrohelp -d astrohelp -c "CREATE DATABASE astrohelp_test;"
```

(`astrohelp` itself is created automatically by the Postgres image via `POSTGRES_DB`.)

### 2. Backend

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env        # edit if you changed ports/secrets
alembic upgrade head
python -m scripts.seed      # seeds 3 admins + 6 astrologers
uvicorn app.main:app --reload --port 8000
```

Env vars (`backend/.env`, see `.env.example` for the full list with defaults):

| Var | Purpose |
|---|---|
| `DATABASE_URL` / `TEST_DATABASE_URL` | Postgres connection strings |
| `JWT_SECRET` | Shared HS256 secret. The real AstroLokal backend signs astrologer JWTs with this; this service only verifies them. Admin JWTs are also signed with it, but carry a `role: "admin"` claim astrologer tokens never have, so the two can't be cross-presented. |
| `GEMINI_API_KEY` | Required for `/api/chat` to actually reach Gemini. Without it (or with a placeholder), the endpoint returns a graceful 500 (`{"detail": "Something went wrong..."}`) — everything else in the app works fine without it. |
| `GEMINI_MODEL` | Defaults to `gemini-flash-latest` (Google's rolling alias for its current fast/cheap model — the dated `gemini-2.5-flash` snapshot has since been retired for new API keys) |
| `MOCK_MODE` | Gates every file in `integrations/` — see "Mocked integrations" below |
| `N8N_BEAUTIFY_WEBHOOK_URL`, `SLACK_WEBHOOK_URL` | Real endpoints to call once `MOCK_MODE=false` |
| `CORS_ORIGINS` | Comma-separated list of frontend origins allowed to call the API |

Minting a local astrologer session token (no real AstroLokal backend to issue one locally):

```bash
python -m scripts.mint_dev_token --astrologer-id 1 --name "Priya Sharma" --language Hindi
```

Prints a signed JWT and a ready-to-open webview URL
(`http://localhost:5173/?token=<JWT>`).

Seeded admin login: `ananya@astrolokal.example` / `astrohelp123` (also `vikram@...` and
`meera@...`, same password — see `backend/scripts/seed.py`).

Backend tests:

```bash
pytest          # 14 tests: agent tool-selection incl. astrologer_id-override proof,
                 # ticket_service status/history invariants, chat + tickets routes
ruff check app scripts tests
```

### 3. Frontends

From the repo root (npm workspaces):

```bash
npm install
cp chat-app/.env.example chat-app/.env
cp admin-app/.env.example admin-app/.env
npm run dev:chat     # http://localhost:5173
npm run dev:admin    # http://localhost:5174
```

Both point at `VITE_API_BASE_URL=http://localhost:8000` by default.

## End-to-end flow to try

1. Mint a token for astrologer 1, open `http://localhost:5173/?token=<JWT>`.
2. Ask "when is my payout coming?" — the agent calls `get_payout_status` and answers from real
   (seeded) data, with a subtle "Checked your payout status" line above the reply. *(Requires
   `GEMINI_API_KEY` to be set to a real key — see above.)*
3. Say you want to change your profile photo, upload one — the agent calls
   `trigger_photo_beautify` then `create_support_ticket` with the beautified image attached.
4. Check the "My Tickets" tab — the new ticket shows `Submitted → Assigned` already filled in on
   the tracker.
5. Log into the admin dashboard, find the ticket in the queue, open it, move its status to
   "In Progress" with a note.
6. Back in the chat app, the tracker updates within ~15s (it polls until a ticket is resolved).
7. Check the admin dashboard's Slack Log page — a mocked notification for the ticket's creation
   is there.

## What's mocked, and how to make each one real

Every mocked integration lives in its own file under `backend/app/integrations/`, starts with a
`# MOCKED — replace with real API call` comment, and is gated by the `MOCK_MODE` env var. Nothing
outside the file needs to change to swap it — callers only ever see the function signature.

| File | Mocked behavior | To go live |
|---|---|---|
| `payout_client.py` | Deterministic, seeded-per-astrologer payout status/amount/dates | Replace the body with a real call to AstroLokal's payments service |
| `kyc_client.py` | Deterministic KYC status + rejection reason | Replace with a real KYC/compliance service call |
| `salary_client.py` | Deterministic monthly salary + revision dates | Replace with a real payroll service call |
| `admin_mapping_client.py` | Round-robins over whichever admins currently exist in our `admins` table (not hardcoded ids — see the file's docstring for why) | Replace with a real roster/ops API call; drop the `db` argument once it's a real HTTP call that doesn't need our own database |
| `n8n_client.py` | Already structured as a real `httpx.post(N8N_BEAUTIFY_WEBHOOK_URL, ...)` call — short-circuits before the network call under `MOCK_MODE` and returns a fabricated `processed_image_url` | Set `MOCK_MODE=false` and `N8N_BEAUTIFY_WEBHOOK_URL` to the real n8n workflow URL |
| `slack_client.py` | Already structured as a real Slack webhook call — under `MOCK_MODE` it skips the network call and writes a row to `slack_log` instead (what the admin dashboard's Slack Log page reads) | Set `MOCK_MODE=false` and `SLACK_WEBHOOK_URL` to a real incoming webhook |

Also mocked, not as an "integration" file but worth knowing about: the astrologer's `kyc_status`,
`payout_status`, and `monthly_salary_inr` columns on the `Astrologer` model exist only to make
`scripts/seed.py` produce plausible data — a real deployment would drop them and rely entirely on
the clients above.

## Data model

Two core tables, related by `ticket_id`:

- `tickets` — one row per support ticket. `status` always mirrors the latest `ticket_status_history`
  row; this is enforced entirely in `app/services/ticket_service.py` (the only code path allowed to
  write either), not via a DB trigger — see the module docstring for why.
- `ticket_status_history` — append-only log of every status change; powers the tracker's timeline.

Plus `astrologers`, `admins`, and `slack_log` (every mocked Slack notification, real or not).
Migration: `backend/alembic/versions/0001_initial_schema.py` (well, whatever the autogenerated
filename is — check `alembic history`).

## Design system

Palette and type scale are defined once in `packages/shared/src/tailwind-preset.js` and consumed
by both frontends via Tailwind's `presets` field, so the two apps can't visually drift apart.
The palette (`night`, `terracotta`, `cream`, `moss`, `ochre`, `clay`, `ink`) matches the actual
AstroLokal brand — warm cream, terracotta accent, near-black chrome, serif display headings
(Playfair Display) over Inter body text — since the chat webview is opened directly from the
AstroLokal app and should read as a continuation of it, not a visually disconnected tool. `moss`
/`ochre`/`clay` stay as restrained status colors (success/attention/error), distinct enough from
terracotta to read as status rather than brand. See the preset file's header comment for more.

## Known limitation

`GEMINI_API_KEY` is not committed anywhere (as it shouldn't be) — `backend/.env` currently holds
a placeholder value. Until a real key is dropped in, `/api/chat` returns a graceful error and the
astrologer-facing chat UI shows a calm "couldn't send" state on the message — everything else
(tickets, tracker, admin dashboard, Slack log) works without it.
