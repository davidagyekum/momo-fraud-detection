# 11 — Deployment and Operations Runbook

## 1. Deployment targets

### Local development

- Docker Compose PostgreSQL;
- local private storage directory outside web root/repository;
- Flask API;
- separate analysis worker;
- React admin dev server;
- Expo mobile dev build;
- Tesseract installed in API/worker image.

### Staging

- containerised API;
- containerised worker from the same source image;
- managed PostgreSQL;
- private S3-compatible object storage;
- deployed React admin site;
- Expo internal Android build;
- HTTPS and environment-specific secrets;
- safe synthetic/demo data only.

### Production-like academic demonstration

May use the same architecture as staging. A full public production release is not required to claim implementation, but the configuration must not expose private receipts or secrets.

## 2. Environment separation

Use separate values for:

- database;
- JWT/session/CSRF secrets;
- storage bucket/prefix;
- allowed origins;
- admin accounts;
- model artifact paths;
- reference data;
- logging/monitoring;
- notification adapters.

Never point local/staging tests at production/private data by default.

## 3. Local bootstrap

Codex implements a cross-platform path:

```bash
cp .env.example .env
python scripts/doctor.py
python scripts/bootstrap.py
docker compose up -d postgres
# install API/ML/Node dependencies through documented commands
# run migrations and seed safe demo accounts/data
docker compose up api worker admin
```

Because Windows may be used, equivalent PowerShell-friendly commands must be documented. Avoid shell-only scripts as the sole path.

### Local services

Recommended compose services:

- `postgres`;
- `api`;
- `worker`;
- optional `admin` for production-like build;
- optional local object-storage emulator only when it does not complicate the MVP.

Mobile runs through Expo on host/device and uses a configured reachable API URL.

## 4. Docker image

Use one Python runtime image for API and worker with different commands.

Requirements:

- pinned Python base;
- system Tesseract packages/language data;
- OpenCV runtime libraries;
- non-root application user;
- dependency installation from lock/pin;
- only required runtime files;
- write access only to designated temp directory;
- health check;
- no source `.env`;
- model artifacts mounted/fetched privately, not baked with secrets;
- build metadata/commit label.

API command example conceptually:

```text
gunicorn "momo_fdvs:create_app()" --bind 0.0.0.0:$PORT --workers <measured>
```

Worker command conceptually:

```text
python -m momo_fdvs.worker run
```

Do not copy development caches, tests/private fixtures or local uploads into the runtime image unnecessarily.

## 5. Required environment variables

The actual contract is in `.env.example`.

Groups:

### Application

- environment;
- app version/build SHA;
- public API base;
- log level;
- trusted proxy setting.

### Database

- PostgreSQL URL;
- pool size/timeout;
- statement timeout where used.

### Auth

- JWT/access secret;
- refresh/session secret;
- CSRF secret;
- access/refresh/reset TTL;
- cookie domain/name/security;
- password hash parameters.

### CORS

- exact admin origins;
- mobile/API development origins where applicable;
- credentials policy.

### Storage

- adapter;
- local root or S3 endpoint/region/bucket/prefix;
- access credentials through secret manager;
- signed URL TTL;
- server-side encryption setting.

### Upload/OCR

- byte/dimension/pixel limits;
- Tesseract executable/language/timeouts;
- OCR confidence threshold.

### Models/risk

- model artifact root/bucket;
- active-model policy;
- worker concurrency;
- stage/retry/heartbeat timeouts;
- risk defaults only when no active database version exists.

### Notifications

- adapter enabled;
- provider credentials;
- sender identity;
- safe message settings.

### Observability

- error-monitoring DSN;
- metrics/log destination;
- PII-redaction mode.

## 6. Database release procedure

1. Verify backup.
2. Record current app and migration revision.
3. Deploy/run migration task once.
4. Check migration output and schema revision.
5. Run database readiness and a safe query.
6. Deploy API/worker compatible with the migration.
7. Run smoke tests.
8. Keep previous app image available.

Do not let every API instance run migrations at startup.

For a destructive migration, use the staged expansion/backfill/contraction policy from the database spec.

## 7. Model release procedure

1. Train/evaluate outside production web process.
2. Produce model card and artifact hash.
3. Upload to private artifact storage.
4. Register as `DRAFT`.
5. Verify hash/framework/schema/smoke inference.
6. Mark `READY`.
7. Administrator activates.
8. Workers reload after successful verification.
9. Monitor error/latency/result distribution.
10. Roll back to previous active version if needed.

No model activation is accomplished by replacing a file at an existing path without a new version record.

## 8. Rule/template release procedure

- create a draft version;
- validate configuration;
- test against safe fixtures/scenarios;
- record diff;
- activate transactionally;
- new analyses snapshot the new version;
- old analyses keep old version;
- rollback activates an earlier valid version and creates audit event.

## 9. Private object storage deployment check

- bucket/container is not public;
- public access block enabled where available;
- application credentials have only required prefix/action rights;
- server-side encryption enabled where available;
- signed URLs expire;
- CORS is narrow;
- lifecycle/retention configured;
- object key contains no PII;
- test unauthenticated URL fails;
- authorised download succeeds and is audited;
- backup/versioning policy documented.

## 10. Admin web deployment

- build with only public configuration such as API origin;
- never inject private secrets into `VITE_*`;
- HTTPS;
- security headers/CSP;
- source-map policy documented;
- correct refresh-cookie domain/SameSite/CSRF configuration;
- SPA route fallback;
- environment indicator on staging;
- error monitoring contains no sensitive data.

## 11. Mobile build

Use Expo EAS or the selected official build path.

Required:

- app identifier/package name;
- staging and release profiles;
- API URL per profile;
- no private API key in bundle;
- permissions limited to camera/gallery/network needed;
- privacy copy;
- version/build number;
- internal Android build for evaluation;
- iOS build only when account/access available;
- secure token storage;
- release notes and tested device matrix.

Do not embed storage/database/model credentials.

## 12. CORS, cookie and domain matrix

Document explicit values:

| Environment | Admin origin | API origin | Secure cookie | SameSite | CSRF |
|---|---|---|---:|---|---|
| Local | localhost dev URL | localhost/LAN API | false only for local | documented | enabled/testable |
| Staging | staging admin HTTPS | staging API HTTPS | true | documented | required |
| Production | production admin HTTPS | production API HTTPS | true | documented | required |

Mobile bearer-token requests do not require browser cookies, but API CORS and token security still apply.

## 13. Health and monitoring

### Health endpoints

- liveness;
- readiness;
- version/build;
- component matrix.

### Monitor

- API error rate/latency;
- database connectivity/pool;
- worker heartbeat;
- queued/stale analyses;
- stage failure/latency;
- storage failures;
- active model readiness;
- report/notification failure;
- disk/temp use;
- security/auth anomalies.

Alerts contain safe IDs, not receipt text or full transaction details.

## 14. Backup and restore

### Database

- managed backups or scheduled encrypted `pg_dump`;
- retention configured;
- restore to isolated environment;
- verify migration and row counts;
- test application against restored data.

### Storage

- versioning/lifecycle where available;
- inventory;
- restore selected test objects;
- reconcile hashes/database references.

### Models/config

- model artifact and cards backed up;
- database versions retain activation history;
- restore verifies SHA.

Document the last rehearsal date/result.

## 15. Staging smoke checklist

- [ ] API health/ready/version;
- [ ] database migration revision;
- [ ] admin login;
- [ ] mobile login;
- [ ] private upload;
- [ ] OCR review;
- [ ] stored reference import;
- [ ] full analysis result;
- [ ] risk/verification separation;
- [ ] history/report;
- [ ] user fraud report;
- [ ] investigator decision;
- [ ] audit entries;
- [ ] unauthorised object access denied;
- [ ] private object not public;
- [ ] worker recovery/heartbeat;
- [ ] no console/server secret leak.

Use only safe test data.

## 16. Release identifiers

Every release records:

- Git commit SHA;
- Git tag;
- API image digest;
- worker image digest;
- admin build ID;
- mobile build/version;
- database migration revision;
- active model IDs/hashes;
- active rule/template versions;
- OpenAPI contract hash;
- deployment timestamp;
- operator.

## 17. Rollback

### Application

Redeploy previous image/build after confirming database compatibility.

### Database

Prefer forward fix. Use downgrade only when migration is explicitly reversible and data safety verified. Document irreversible migrations.

### Model/rule/template

Activate previous verified version. Do not delete the problematic version; mark failed/retired and preserve audit.

### Mobile

Internal testing can install previous build. Public-store rollback constraints must be documented if applicable.

### Storage

Do not delete new originals during application rollback. Preserve evidence and reconcile after service stabilises.

## 18. Deployment blockers

A deployment may be blocked by:

- no GitHub/deployment account access;
- no database/object-storage credentials;
- no mobile signing/build account;
- no production domain;
- no authorised model/reference artifacts.

Codex must still deliver:

- manifests/config templates;
- Docker image build;
- local/staging-like verification;
- exact environment variables;
- exact commands;
- clear blocker/owner/next action.

It must not claim a deployment that did not occur.

## 19. Production-readiness limitations

The final document must state any:

- synthetic-only model evaluation;
- absent live MNO integration;
- unavailable push/email adapter;
- missing iOS build;
- unmeasured availability;
- incomplete legal retention policy;
- limited provider templates;
- performance target miss;
- manually executed rather than automated operation.

## 20. Release checklist

- [ ] P18 test report approved;
- [ ] zero blocker/critical security defects;
- [ ] secrets scan;
- [ ] backup verified;
- [ ] migration reviewed;
- [ ] private storage check;
- [ ] model/rule/template readiness;
- [ ] staging smoke;
- [ ] release identifiers recorded;
- [ ] rollback plan;
- [ ] final handoff updated;
- [ ] exact SHA pushed and CI green.
