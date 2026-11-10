# onboarding-agent

A dynamic **onboarding workflow agent**: give it a new hire's name, role, and tech
stack and it generates a 30/60/90-day onboarding roadmap — then keeps it on track.
External events (laptop delayed, first PR merged, mentor unavailable, access
blocked) arrive via a webhook; the agent re-plans remaining milestones in
response, streaming every tool call to the dashboard over SSE in real time.

```
React/Vite dashboard ──SSE──▶ FastAPI ──tool calls──▶ SQLite (SQLAlchemy 2.0 async)
      ▲                          │
      └────────── REST ──────────┴──▶ webhook ingest (HRIS / GitHub / ITSM / LMS)
```

## Stack

| Layer | Tech |
| --- | --- |
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), SQLite via aiosqlite |
| Agent | Anthropic tool-use loop (`anthropic` SDK) with deterministic mock-mode fallback |
| Real-time | Server-Sent Events (in-process pub/sub bus, per-workflow fan-out) |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, lucide-react |
| Testing | pytest, pytest-asyncio, httpx ASGI transport, planner evals |

## Agent tools

The agent executes these tools against live workflow state; every call is
recorded in `audit_logs` and broadcast over SSE:

| Tool | Behavior |
| --- | --- |
| `generate_roadmap` | Builds the role-specific 30/60/90 milestone plan (replaces outstanding milestones) |
| `get_workflow_state` | Reads the workflow + milestone statuses |
| `update_milestone_status` | Sets a milestone's status |
| `adapt_roadmap` | Re-plans pending work around a disruption/acceleration event |

## API surface

```
POST   /api/workflows                    create workflow
GET    /api/workflows                    list
GET    /api/workflows/{id}               detail (with milestones)
DELETE /api/workflows/{id}
POST   /api/workflows/{id}/run           kick off the agent (202)
GET    /api/workflows/{id}/stream        SSE: tool_call/tool_result/agent_message/…
GET    /api/workflows/{id}/audit         audit trail
PATCH  /api/milestones/{id}              manual status/field updates
POST   /api/webhooks/events              external event ingest → agent adaptation
GET    /api/health
```

## Quickstart

```bash
# Backend  (http://localhost:8000, docs at /docs)
cd backend
python -m venv .venv && .venv/Scripts/activate   # or: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend (http://localhost:5173, /api proxied to :8000)
cd frontend
npm install
npm run dev
```

Create a workflow in the UI — the agent immediately generates the roadmap.
Then hit the **Simulate Events** buttons to fire webhooks and watch the agent
adapt the plan live.

## LLM modes

- **Mock mode (default, no key needed):** a deterministic scripted agent
  exercises the same tools — reproducible demos and evals.
- **Live mode:** set `ANTHROPIC_API_KEY` (see `backend/.env.example`) and the
  Anthropic tool-use loop drives the same harness with Claude deciding calls.

Config env vars: `DATABASE_URL`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`,
`CORS_ORIGINS`.

## Deploy

Split deploy — backend on Render, frontend on Vercel:

1. **Backend → Render:** Dashboard → *New → Blueprint* → select this repo.
   `render.yaml` provisions `onboarding-agent-api` (free tier, health check at
   `/api/health`). When prompted, set `CORS_ORIGINS` to your Vercel frontend
   origin; `ANTHROPIC_API_KEY` is optional (mock mode without it).
   Note: the free tier uses ephemeral disk, so the SQLite DB resets on restart —
   add a persistent disk or swap `DATABASE_URL` for Postgres to keep state.
2. **Frontend → Vercel:** *Add New → Project* → import this repo, set the root
   directory to `frontend`, and add env var
   `VITE_API_URL=https://<your-service>.onrender.com` (origin only — the app
   appends `/api`; see `frontend/.env.example`).
3. Update `CORS_ORIGINS` on Render to your final `https://<app>.vercel.app`
   origin if you didn't know it at step 1.

## Tests & evals

```bash
cd backend
pytest -q
```

- `tests/test_api.py` — async API coverage: CRUD, agent roadmap generation,
  manual milestone updates, webhook-triggered adaptation, SSE event stream.
- `tests/test_evals.py` — synthetic milestone-adaptation evals over the
  deterministic planner: roadmap completeness, dependency-graph integrity,
  role specialization, and per-event adaptation correctness.
