# Local development

## Prerequisites

- Git
- Python 3.12
- Docker Desktop or Docker Engine with Compose v2
- Node.js 22 and npm 10 for later frontend phases

The unqualified `python` command on the preflight Windows host is Python 3.11. Use `py -3.12` there.

## Windows PowerShell

```powershell
py -3.12 scripts/bootstrap.py --create-env
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r .\services\api\requirements-dev.lock
.\.venv\Scripts\python.exe -m pip install --no-deps -e .\services\api
.\.venv\Scripts\python.exe scripts\export_openapi.py --check
docker compose up --build -d db api
Invoke-RestMethod http://localhost:8000/api/v1/health
Invoke-RestMethod http://localhost:8000/api/v1/ready
.\.venv\Scripts\python.exe scripts\verify.py --backend
```

## macOS/Linux

```bash
python3.12 scripts/bootstrap.py --create-env
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r services/api/requirements-dev.lock
.venv/bin/python -m pip install --no-deps -e services/api
.venv/bin/python scripts/export_openapi.py --check
docker compose up --build -d db api
curl --fail http://localhost:8000/api/v1/health
curl --fail http://localhost:8000/api/v1/ready
.venv/bin/python scripts/verify.py --backend
```

## Docker lifecycle

`docker compose up --build -d db api` starts PostgreSQL and the API. The API waits for PostgreSQL's health check, stores database and private-object data in named volumes, and runs as a non-root user with Tesseract English data installed.

Inspect with `docker compose ps` and `docker compose logs api db`. Stop services with `docker compose down`. Do not add `--volumes` unless intentionally deleting local development data.

The liveness endpoint proves that the process is running. Readiness is HTTP 503 when PostgreSQL or private storage is unavailable. Missing Tesseract or inactive models are disclosed as degraded analysis components; they do not fabricate success.
