# Spotify Playlist Manager

> A production-minded automation service that preserves Spotify Discover Weekly tracks before the playlist changes.

Spotify Playlist Manager connects to a user's Spotify account, finds the current **Discover Weekly** playlist, and copies new tracks into a private **Saved Weekly** playlist. The application is deliberately built as a small distributed system rather than a single script: the API handles authentication and orchestration, PostgreSQL stores durable state and run history, Redis provides the queue and result backend, and a Celery worker performs the Spotify synchronization outside the request path.

This project is a practical demonstration of backend, infrastructure, and operational engineering:

- OAuth 2.0 authorization with server-side token storage and refresh
- Asynchronous job processing with Celery and Redis
- PostgreSQL data modeling with SQLAlchemy and Alembic migrations
- Retry and backoff behavior for transient Spotify API failures and rate limits
- Dockerized, non-root backend deployment suitable for Cloud Run
- Environment-driven configuration with startup validation
- Structured, redacted logging and JSON log support
- CI gates for formatting, linting, tests, frontend builds, and container builds

## What the system does

1. A user selects **Connect Spotify** in the Next.js frontend.
2. The FastAPI backend starts Spotify OAuth and protects the flow with a signed, short-lived state cookie.
3. Spotify redirects back to the backend. The backend exchanges the authorization code, fetches the Spotify user, and stores tokens server-side.
4. The dashboard submits a sync request. The API authenticates the session and enqueues a Celery job.
5. The worker:
   - refreshes the Spotify access token when it is close to expiry;
   - discovers the source and target playlists;
   - creates `Saved Weekly` if needed;
   - paginates through playlist tracks;
   - filters local tracks and tracks already saved;
   - adds new tracks in Spotify's batch size;
   - records a durable run status and track count.
6. The frontend polls the job endpoint and displays recent run history.

The sync is idempotent with respect to tracks already present in `Saved Weekly`, so repeating a run does not intentionally create duplicates.

## Architecture

```text
┌─────────────────────┐       HTTPS / cookies       ┌─────────────────────────┐
│ Next.js frontend    │ ───────────────────────────▶ │ FastAPI API             │
│ Vercel              │                              │ Docker (Cloud Run ready)│
└─────────────────────┘                              └──────────┬──────┬───────┘
                                                            │      │
                                             SQLAlchemy     │      │ Celery
                                                            ▼      ▼
                                                   ┌──────────┐  ┌──────────┐
                                                   │PostgreSQL│  │  Redis   │
                                                   │state/runs│  │broker    │
                                                   └──────────┘  └────┬─────┘
                                                                     │
                                                                     ▼
                                                            ┌────────────────┐
                                                            │ Celery worker  │
                                                            │ Spotify sync   │
                                                            └───────┬────────┘
                                                                    │
                                                                    ▼
                                                              Spotify Web API
```

### Main components

| Area | Implementation | Responsibility |
| --- | --- | --- |
| API | FastAPI + Uvicorn | Health, OAuth, playlist endpoints, job status |
| Web UI | Next.js 14 + React | Connection flow, sync controls, run history |
| Persistence | PostgreSQL + SQLAlchemy | Users, OAuth tokens, playlist configuration, run history |
| Migrations | Alembic | Reproducible database schema changes |
| Background work | Celery + Redis | Queueing and executing playlist synchronization |
| External API | Spotify Web API + `httpx` | OAuth, playlist discovery, track reads/writes |
| Delivery | Docker + GitHub Actions | Reproducible image builds and automated checks |

## Repository layout

```text
backend/
  app/
    auth/          Spotify OAuth routes and token lifecycle
    core/          configuration, security, logging, validation
    db/            SQLAlchemy models and database sessions
    playlists/     API routes and Spotify synchronization service
    schemas/       Pydantic request/response models
    workers/       Celery application and background tasks
  alembic/         database migrations
  tests/           backend unit and integration tests
  Dockerfile       multi-stage, non-root API image
frontend/
  app/             Next.js pages and dashboard components
  lib/             typed API request helper
.github/workflows/
  ci.yml           lint, test, frontend build, Docker build
docker-compose.yml local PostgreSQL and Redis services
deployment.md     Cloud Run, Vercel, secrets, and production guidance
```

The root-level [`spoofy.py`](./spoofy.py) is the original Flask/Spotipy prototype. The maintained application is the FastAPI service under [`backend/app`](./backend/app) and the Next.js application under [`frontend`](./frontend).

## Quick start

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker Desktop with Docker Compose
- A Spotify Developer application

Create a Spotify application in the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard). Add this redirect URI to the application:

```text
http://127.0.0.1:8000/auth/callback
```

### 1. Start local infrastructure

From the repository root:

```bash
docker compose up -d postgres redis
```

The Compose file starts PostgreSQL on `localhost:5432` and Redis on `localhost:6379`, with health checks and named volumes for local persistence.

### 2. Configure and run the backend

```bash
cd backend
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1

pip install -e ".[dev]"
copy .env.example .env
```

Fill in `backend/.env`, then apply the schema and start the API:

```bash
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API is available at `http://localhost:8000`. In development, interactive OpenAPI documentation is available at [`/docs`](http://localhost:8000/docs), and [`/health`](http://localhost:8000/health) provides a lightweight health response.

### 3. Run the Celery worker

In a second terminal:

```bash
cd backend
.venv\Scripts\Activate.ps1
celery -A app.workers.celery_app.celery_app worker --loglevel=INFO
```

### 4. Run the frontend

In a third terminal:

```bash
cd frontend
npm ci
copy .env.example .env.local
npm run dev
```

Open `http://127.0.0.1:3000`, connect Spotify, and run a Discover Weekly sync from the dashboard.

## Configuration

The backend uses Pydantic Settings and fails fast when required values are missing or invalid. Copy [`backend/.env.example`](./backend/.env.example) to `backend/.env`; never commit local environment files.

| Variable | Required | Purpose |
| --- | --- | --- |
| `SPOTIFY_CLIENT_ID` | Yes | Spotify application client ID |
| `SPOTIFY_CLIENT_SECRET` | Yes | Spotify application client secret |
| `APP_SECRET` | Yes | At least 16 characters; signs OAuth state and session cookies |
| `DATABASE_URL` | Yes | PostgreSQL connection URL |
| `BASE_URL` | Yes | Public backend URL used to build the OAuth callback |
| `ALLOWED_ORIGINS` | No | Comma-separated frontend origins; defaults to `http://127.0.0.1:3000` |
| `REDIS_URL` | No | Celery broker/result backend; defaults to local Redis |
| `ENVIRONMENT` | No | `development` by default; `production` disables API docs |
| `DEBUG` | No | SQLAlchemy debug behavior; keep `false` in production |
| `LOG_LEVEL` | No | Logging level; defaults to `INFO` |
| `JSON_LOGS` | No | Emits JSON log lines when set to `true` |
| `AUTH_SUCCESS_REDIRECT` | No | Optional safe post-login redirect within an allowed origin |

The frontend uses [`frontend/.env.example`](./frontend/.env.example):

```text
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

## API surface

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Liveness-style health response |
| `GET` | `/auth/login` | Start Spotify OAuth |
| `GET` | `/auth/callback` | Complete OAuth and establish the session |
| `GET` | `/auth/me` | Return the authenticated Spotify user |
| `POST` | `/auth/logout` | Clear the session cookie |
| `POST` | `/playlists/sync/discover-weekly` | Enqueue a sync job |
| `GET` | `/playlists/runs` | List the current user's recent runs |
| `GET` | `/jobs/{job_id}` | Inspect asynchronous job status |

The sync request supports `dry_run` and `max_tracks` (1–500) for controlled execution. Authentication is cookie-based; Spotify access and refresh tokens are not sent to the browser or returned by API responses.

## Reliability and security design

- **OAuth state validation:** the callback verifies a signed state value stored in an HttpOnly, short-lived cookie.
- **Session integrity:** session cookies contain a user ID plus an HMAC signature and are HttpOnly with `SameSite=Lax`.
- **Safe redirects:** post-authentication redirects are restricted to configured origins.
- **Server-side secrets:** Spotify tokens remain in PostgreSQL and are refreshed by the backend.
- **Token redaction:** application logging redacts bearer tokens, secrets, passwords, and token-shaped values.
- **Transient failure handling:** network failures, Spotify 5xx responses, and rate limits use bounded retries and backoff; Celery retries failed work up to five times.
- **Pagination guards:** playlist reads have explicit page limits to prevent runaway iteration.
- **Least privilege by default:** the container runs as a non-root `app` user, and production secrets are intended to come from a secret manager.
- **Production CORS:** configure exact frontend origins; do not use `*` with credentialed requests.

## Testing and quality gates

Run backend checks from `backend/`:

```bash
ruff format --check .
ruff check app tests
pytest -v
```

Run frontend checks from `frontend/`:

```bash
npm ci
npm run lint
npm run build
```

GitHub Actions runs these checks on pushes and pull requests. CI also provisions PostgreSQL and Redis service containers; backend tests currently use in-memory SQLite and mocked Spotify calls. It also builds the backend Docker image to verify the deployment artifact.

## Deployment

The intended production topology is:

- **Frontend:** Vercel
- **API:** Cloud Run using [`backend/Dockerfile`](./backend/Dockerfile)
- **Database:** managed PostgreSQL, preferably Cloud SQL
- **Worker:** a separate Cloud Run service or job using the same image
- **Queue/result backend:** managed Redis, such as Memorystore
- **Secrets:** Secret Manager bindings for `APP_SECRET`, `SPOTIFY_CLIENT_SECRET`, and database credentials

The Docker image uses a multi-stage build, installs dependencies into a dedicated virtual environment, listens on Cloud Run's `$PORT`, and runs without root privileges. Read [`deployment.md`](./deployment.md) for Cloud Run networking, cookie/CORS requirements, secure headers, and operational recommendations.

For cookie-based authentication to work reliably across deployments, host the frontend and API on custom domains under the same site (for example, `app.example.com` and `api.example.com`) and set `BASE_URL` and `ALLOWED_ORIGINS` accordingly.

## Engineering highlights

This repository is intentionally small, but it exercises the same concerns that appear in larger infrastructure systems:

- separating synchronous request handling from durable background work;
- designing retry boundaries around an unreliable external dependency;
- making state transitions observable through persistent run records;
- treating configuration, secrets, and deployment settings as explicit contracts;
- building locally with the same PostgreSQL, Redis, and container primitives used in the intended deployment;
- keeping CI responsible for reproducibility rather than relying on local machine state.

## License

No license file is currently included. Add an appropriate license before distributing the project publicly.
