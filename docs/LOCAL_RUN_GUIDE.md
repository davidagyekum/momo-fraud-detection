# Running MoMo-FDVS locally

This guide starts the complete local prototype: PostgreSQL, the Flask API, the administrator portal, and the Expo mobile app exported for the web. Docker is the recommended path because it keeps the supported service versions together.

## Prerequisites

- Docker Desktop with Docker Compose v2
- Node.js 24.14 and npm 10.9 (the repository-pinned versions)
- Python 3.12 for verification and maintenance scripts

Run all commands from the repository root:

```powershell
cd C:\Users\David_A\Desktop\CS\momoFraudDetection
```

## First-time setup

Prepare ignored local storage directories. Creating `.env` is optional for the controlled local stack; if you create it, replace every `CHANGE_ME` placeholder and never commit the file.

```powershell
py -3.12 scripts\bootstrap.py
npm.cmd --prefix apps\mobile ci
npm.cmd --prefix apps\admin ci
```

The API dependencies are built inside Docker. A host Python virtual environment is only required when running the backend test suite outside Docker.

## Start the complete Docker stack

The commands below use alternate ports so they do not collide with common local services:

```powershell
$env:POSTGRES_PORT="55436"
$env:API_PORT="8003"
$env:ADMIN_PORT="5177"
$env:MOBILE_WEB_PORT="8084"
$env:CORS_ALLOWED_ORIGINS="http://localhost:5177,http://localhost:8084"

npm.cmd --prefix apps\mobile run build:web
docker compose -p momo-fdvs-text-risk up -d --build db api admin mobile
docker compose -p momo-fdvs-text-risk ps
```

On a new local database, activate the repository's idempotent controlled-development seed. The values below are examples for local testing only; change the passwords if the machine is shared.

```powershell
docker compose -p momo-fdvs-text-risk exec -T `
  -e BOOTSTRAP_ADMIN_EMAIL=admin@example.test `
  -e BOOTSTRAP_ADMIN_FULL_NAME="Local Demo Administrator" `
  -e BOOTSTRAP_ADMIN_PASSWORD=Local-Admin-Only-2026! `
  -e BOOTSTRAP_INVESTIGATOR_EMAIL=investigator@example.test `
  -e BOOTSTRAP_INVESTIGATOR_FULL_NAME="Local Demo Investigator" `
  -e BOOTSTRAP_INVESTIGATOR_PASSWORD=Local-Investigator-Only-2026! `
  api flask --app momo_fdvs.wsgi:app seed-development
```

The seed is safe to rerun. It creates fictitious development users, one controlled rule set, and one controlled reference record. It never runs automatically and is blocked in production.

## Open the services

- Mobile/web app: <http://localhost:8084>
- API health: <http://localhost:8003/api/v1/health>
- API readiness: <http://localhost:8003/api/v1/ready>
- Administrator portal: <http://localhost:5177>
- PostgreSQL host port: `55436`

Normal users can create an account from the mobile/web registration screen. The seeded staff accounts require a password change and are intended only for controlled local administration testing.

## Test the OCR-first journey

1. Open the mobile/web app and create a fictitious test account.
2. Select **Start a receipt check**.
3. Upload a clear JPEG, PNG, or WebP screenshot. Do not use a real private receipt for casual testing.
4. Select **Review extracted details**.
5. Review the message-risk result before any transaction fields.
6. Select **Save screenshot risk result** to persist screenshot-only risk evidence without filling transaction details.
7. Use **Compare with a transaction record (optional)** only when you intentionally want stored/imported reference comparison.
8. Open History and confirm that fraud risk and transaction verification appear as separate statuses.

## Health checks and logs

```powershell
Invoke-RestMethod http://localhost:8003/api/v1/health
Invoke-RestMethod http://localhost:8003/api/v1/ready
docker compose -p momo-fdvs-text-risk ps
docker compose -p momo-fdvs-text-risk logs --follow api admin mobile db
```

If one service is unhealthy, inspect its logs first. Docker Desktop may need restarting if the Docker engine itself is unreachable; a PC restart is not normally required.

## Restart, stop, and reset

Restart the existing containers:

```powershell
docker compose -p momo-fdvs-text-risk restart
```

Stop the stack while preserving PostgreSQL and private-storage volumes:

```powershell
docker compose -p momo-fdvs-text-risk down
```

Do not add `--volumes` unless you intentionally want to delete all local database, receipt, and model-artifact data.

## Expo development mode

Docker serves the mobile application as a static web export. For live Expo development:

```powershell
cd apps\mobile
npm.cmd ci
$env:EXPO_PUBLIC_API_URL="http://localhost:8003"
npm.cmd run web
```

For Expo Go on a physical phone, use the computer's LAN IP instead of `localhost`, for example `http://192.168.1.20:8003`, and ensure the phone and computer are on the same network. Never put secrets in `EXPO_PUBLIC_*` variables; those values are public in the client bundle.

## Verification

From the repository root:

```powershell
.\.venv\Scripts\python.exe scripts\verify_mobile.py
.\.venv\Scripts\python.exe scripts\verify_backend.py
.\.venv\Scripts\python.exe scripts\verify_admin.py
.\.venv\Scripts\python.exe scripts\verify_ml.py
.\.venv\Scripts\python.exe scripts\verify_security.py
```

See `IMPLEMENTATION_STATUS.md` for the currently accepted phase and exact recorded evidence.
