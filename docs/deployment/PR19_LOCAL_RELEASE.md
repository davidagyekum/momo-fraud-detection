# PR19 Local Release Runbook

PR19 delivers a verified local four-service release. It is not a public or production deployment.

## Prerequisites

- Docker Desktop with Compose v2.
- Node.js `24.14.0` and npm `10.9.0` as pinned by the repository.
- Python `3.12` for host-side verification.
- Local environment values copied from `.env.example`; never commit real credentials.

## Start

From the repository root:

```powershell
npm run infra:up
```

The command first creates the Expo web export used by the mobile Nginx image, then builds and starts PostgreSQL, Flask API, administrator portal, and mobile web release. The API applies Alembic migrations before serving.

Default local addresses:

- API health: `http://127.0.0.1:8000/api/v1/health`
- API readiness: `http://127.0.0.1:8000/api/v1/ready`
- Administrator portal: `http://127.0.0.1:5173/login`
- Mobile web release: `http://127.0.0.1:8081/login`

Run the release probe after startup:

```powershell
python scripts/verify_release.py
```

Readiness may honestly report optional image or structured models as degraded/not activated. That is an explicit partial-analysis boundary, not a successful model result. Tesseract, storage, and the database must be ready.

## Controlled acceptance configuration

The PR19 acceptance run used an isolated Compose project and ports `55435`, `8002`, `5176`, and `8083`. Override Compose variables only with local placeholder credentials. Do not expose the database or private receipt volume publicly.

## Stop and inspect

```powershell
npm run infra:logs
npm run infra:down
```

`infra:down` preserves named database and private-storage volumes. Never add `--volumes` during routine shutdown. Raw receipts remain private and are served only through authorised API routes.

## Seeded users

Development identities are created only through the controlled seed path and environment-provided passwords. Do not put passwords in this runbook, shell history, screenshots, or Git.

