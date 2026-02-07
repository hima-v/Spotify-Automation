# Production deployment notes (Cloud Run + Vercel)

This repo is set up for:

- Backend API: Cloud Run (container)
- Database: managed Postgres (recommended: Cloud SQL)
- Redis/Celery: optional (separate service); not required for basic API serving
- Frontend: Vercel (recommended)

## 1) Backend: Cloud Run

### Build locally (sanity check)

```bash
docker build -f backend/Dockerfile -t spotify-backend:local backend
docker run --rm -p 8080:8080 ^
  -e ENVIRONMENT=production ^
  -e DATABASE_URL="postgresql://..." ^
  -e SPOTIFY_CLIENT_ID="..." ^
  -e SPOTIFY_CLIENT_SECRET="..." ^
  -e APP_SECRET="..." ^
  -e BASE_URL="https://api.example.com" ^
  -e ALLOWED_ORIGINS="https://app.example.com" ^
  spotify-backend:local
```

### Required environment variables (Cloud Run service)

- `ENVIRONMENT=production` (disables Swagger/ReDoc in `app/main.py`)
- `DEBUG=false`
- `BASE_URL`: public URL of the backend (used for OAuth callback URL composition)
- `ALLOWED_ORIGINS`: comma-separated list of allowed frontend origins (CORS)
- `DATABASE_URL`: Postgres connection string
- `SPOTIFY_CLIENT_ID`
- `SPOTIFY_CLIENT_SECRET` (secret)
- `APP_SECRET` (secret; >= 16 chars)
- `REDIS_URL` (only needed if you run Celery)
- `LOG_LEVEL` / `JSON_LOGS` (optional)

### Secrets (Secret Manager recommended)

Store secrets in Secret Manager and bind them as Cloud Run environment variables:

- `SPOTIFY_CLIENT_SECRET`
- `APP_SECRET`
- (optional) `DATABASE_URL` if it contains credentials

### Postgres on Cloud Run (Cloud SQL recommended)

If using Cloud SQL for Postgres, prefer Cloud Run's Cloud SQL integration and connect via the Unix socket.

Example `DATABASE_URL`:

```text
postgresql://DB_USER:DB_PASS@/DB_NAME?host=/cloudsql/PROJECT:REGION:INSTANCE
```

If you use a direct TCP connection, ensure:

- Private IP / VPC connector (recommended)
- TLS, firewall rules, least-privilege DB user

### Cloud Run settings (recommended)

- **Ingress**: internal + Cloud Load Balancing (or all, if you must)
- **Authentication**: allow unauthenticated (typical for public APIs), but keep endpoints protected via session cookie
- **Min instances**: 0 or 1 (cost vs cold starts)
- **Concurrency**: default is fine; tune after observing latency
- **CPU**: "CPU always allocated" only if you need consistent latency

### Secure headers

Cloud Run does not automatically inject security headers.

Recommended: put Cloud Run behind an HTTPS load balancer and configure response headers there:

- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: no-referrer`
- `X-Frame-Options: DENY`
- `Content-Security-Policy: frame-ancestors 'none'`

If you prefer app-level headers, add a small FastAPI middleware (no dependency needed).

### CORS + cookies (important)

This backend uses **HttpOnly cookies** with `SameSite=Lax`. For `fetch()` calls to include cookies:

- **Frontend and backend must be same-site**, e.g. `https://app.example.com` and `https://api.example.com`.
- If you deploy on unrelated domains (`*.vercel.app` + `*.run.app`), browsers will not send `SameSite=Lax` cookies on XHR/fetch and auth will appear broken.

Recommended: configure **custom domains** for both Vercel and Cloud Run under the same eTLD+1.

### CORS restriction checklist

- Set `ALLOWED_ORIGINS` to the exact frontend origins (no wildcards), e.g.:
  - `https://app.example.com`
- Do not use `*` when `allow_credentials=true`.

## 2) Frontend: Vercel

Deploy the `frontend/` directory as a Vercel project.

Environment variables:

- `NEXT_PUBLIC_API_URL`: e.g. `https://api.example.com`

Notes:

- The frontend **never** handles Spotify tokens.
- All calls use `credentials: "include"`; the backend session cookie is HttpOnly.

## 3) Background jobs (Celery) in production

If you deploy Celery:

- Run worker as a separate Cloud Run service (or Cloud Run Job) using the same image.
- Set `REDIS_URL` to a managed Redis instance (e.g., Memorystore) reachable from Cloud Run.
- Keep the API service and worker isolated with least privilege.

## 4) GitHub Actions

The CI workflow does:

- Backend: `ruff format --check`, `ruff check`, `pytest`
- Frontend: `npm ci`, `npm run lint`, `npm run build`
- Docker: builds the backend image (no push)

## 5) Safety notes (non-negotiable)

- Never commit `.env.local` / real secrets.
- Keep `ENVIRONMENT=production` in prod; never enable reload/debug.
- Restrict `ALLOWED_ORIGINS` to known frontend origins only.
- Use Secret Manager bindings for `APP_SECRET` and Spotify client secret.
- Ensure DB credentials are least-privilege; rotate secrets periodically.

