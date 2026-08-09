# 03 — Architecture and Repository Specification

## 1. Architectural style

MoMo-FDVS uses a layered client-server architecture with an explicit background analysis worker:

1. **Mobile presentation layer:** Expo/React Native user application.
2. **Web presentation layer:** React/Vite administrator and investigator portal.
3. **API/application layer:** Flask REST API handling authentication, validation, policies, orchestration requests and read models.
4. **Analysis worker:** Python process that claims queued analysis runs from PostgreSQL and executes OCR, image, ML, rule and verification services.
5. **Data layer:** PostgreSQL plus private object storage.
6. **AI/verification layer:** Tesseract/OpenCV, TensorFlow/Keras, scikit-learn, rules and reference matching.

The analysis worker is separate from web request workers so CPU-heavy receipt processing does not block login/history/admin traffic. To avoid adding a mandatory Redis dependency, the prototype uses a PostgreSQL-backed queue based on `analysis_runs` and safe row claiming (`FOR UPDATE SKIP LOCKED` or the SQLAlchemy equivalent). An adapter boundary permits later replacement with Celery/RQ without changing domain services.

## 2. Target monorepo

```text
/
├── AGENTS.md
├── README.md
├── README_FIRST.md
├── IMPLEMENTATION_STATUS.md
├── DECISION_LOG.md
├── CHANGELOG.md
├── .editorconfig
├── .gitattributes
├── .gitignore
├── .env.example
├── docker-compose.yml
├── package.json                 # optional root workspace scripts
├── pnpm-workspace.yaml          # or chosen pinned workspace manager
├── apps/
│   ├── mobile/
│   │   ├── app/                 # Expo Router routes
│   │   ├── src/
│   │   │   ├── components/
│   │   │   ├── features/
│   │   │   ├── hooks/
│   │   │   ├── lib/
│   │   │   ├── state/
│   │   │   ├── theme/
│   │   │   └── types/
│   │   ├── assets/
│   │   ├── tests/
│   │   ├── app.config.ts
│   │   └── package.json
│   └── admin/
│       ├── src/
│       │   ├── app/
│       │   ├── components/
│       │   ├── features/
│       │   ├── hooks/
│       │   ├── lib/
│       │   ├── routes/
│       │   ├── theme/
│       │   └── types/
│       ├── tests/
│       ├── playwright/
│       ├── vite.config.ts
│       └── package.json
├── packages/
│   ├── api-client/              # generated TypeScript client/types
│   ├── eslint-config/
│   └── tsconfig/
├── services/
│   └── api/
│       ├── pyproject.toml
│       ├── migrations/
│       ├── src/momo_fdvs/
│       │   ├── __init__.py       # create_app
│       │   ├── config.py
│       │   ├── extensions.py
│       │   ├── errors.py
│       │   ├── logging.py
│       │   ├── cli.py
│       │   ├── api/
│       │   │   └── v1/
│       │   ├── auth/
│       │   ├── domain/
│       │   ├── models/
│       │   ├── schemas/
│       │   ├── repositories/
│       │   ├── services/
│       │   ├── policies/
│       │   ├── storage/
│       │   ├── analysis/
│       │   ├── ocr/
│       │   ├── image_analysis/
│       │   ├── verification/
│       │   ├── risk/
│       │   ├── ml_runtime/
│       │   ├── reports/
│       │   └── worker/
│       └── tests/
│           ├── unit/
│           ├── integration/
│           ├── contract/
│           ├── security/
│           └── fixtures/
├── ml/
│   ├── pyproject.toml
│   ├── configs/
│   ├── data/
│   ├── notebooks/               # exploration only; production logic elsewhere
│   ├── src/momo_ml/
│   │   ├── data/
│   │   ├── features/
│   │   ├── structured/
│   │   ├── image_model/
│   │   ├── evaluation/
│   │   └── registry/
│   ├── tests/
│   └── reports/
├── infra/
│   ├── docker/
│   ├── render/                  # provider-default manifests, if selected
│   ├── nginx/                   # optional
│   └── storage/
├── docs/
│   ├── implementation/
│   ├── architecture/
│   ├── api/
│   ├── diagrams/
│   ├── model-cards/
│   ├── dataset-cards/
│   ├── qa/
│   └── deployment/
├── scripts/
│   ├── bootstrap.py
│   ├── doctor.py
│   ├── verify.py
│   ├── check_secrets.py
│   ├── generate_api_client.py
│   ├── seed_demo.py
│   └── export_diagrams.py
└── samples/
```

The exact workspace manager may be npm, pnpm or another approved tool, but it must be pinned and used consistently. Do not commit two competing lockfiles.

## 3. Backend package responsibilities

### 3.1 `api/v1`

Blueprints/controllers only:

- parse and validate request;
- call a policy check;
- invoke a service;
- serialise the response;
- map known exceptions to the standard error envelope.

Controllers must not contain SQL queries, image-processing code, model loading or business-score calculations.

### 3.2 `schemas`

Flask-Smorest/Marshmallow request and response schemas, or the documented equivalent selected during P01. Schemas define:

- request validation;
- response projection;
- OpenAPI documentation;
- field masking at the response boundary where appropriate.

The generated OpenAPI document is the client contract. Breaking changes require a version or explicit migration.

### 3.3 `services`

Application use cases and transaction boundaries:

- register/login/reset;
- create receipt submission;
- confirm OCR review;
- queue analysis;
- list history;
- create report/case;
- administer versions/imports.

Services may coordinate repositories and domain components but must not depend on Flask global request objects.

### 3.4 `repositories`

Database access only:

- typed query methods;
- ownership-aware lookup helpers;
- pagination;
- aggregate queries;
- row locking/claiming;
- no HTTP concepts.

### 3.5 `domain`

Pure domain enums, value objects, state-transition rules, reason-code catalogue and errors. Domain functions should be testable without Flask or a database where practical.

### 3.6 `policies`

Central server-side authorisation:

- role/capability rules;
- object ownership;
- investigator assignment/queue access;
- sensitive-field projection;
- last-administrator protection.

A controller calling a repository directly and forgetting a policy is not acceptable. Use service methods that require an authenticated principal.

### 3.7 `storage`

Interface:

```python
class PrivateObjectStorage(Protocol):
    def put(self, *, key: str, stream: BinaryIO, content_type: str) -> StoredObject: ...
    def open(self, *, key: str) -> BinaryIO: ...
    def delete(self, *, key: str) -> None: ...
    def exists(self, *, key: str) -> bool: ...
    def stat(self, *, key: str) -> ObjectMetadata: ...
```

Implementations:

- `LocalPrivateStorage` for development/tests;
- `S3PrivateStorage` for staging/production.

Neither implementation returns a permanent public URL. Downloads are streamed through an authorised endpoint or use a short-lived signed URL after policy checks.

### 3.8 `ocr`

Pure or service-style functions for:

- image quality;
- preprocessing variants;
- Tesseract invocation;
- token data;
- template detection;
- field parsing/normalisation;
- confidence/warnings.

Tesseract process failures must be translated to a controlled domain error.

### 3.9 `image_analysis`

Versioned feature extractors. Each extractor returns a common evidence structure rather than directly assigning the final class.

### 3.10 `ml_runtime`

- artifact resolver;
- SHA-256 verification;
- structured model adapter;
- TensorFlow model adapter;
- version/schema compatibility;
- unavailable/corrupt model result.

Loading is lazy and cached per process, but activation changes must invalidate or reload safely.

### 3.11 `verification`

Reference candidate lookup and field comparison. The module knows nothing about MNO claims; its source is an authorised local/import adapter.

### 3.12 `risk`

- rule evaluation;
- component-probability normalisation;
- configurable weighted score;
- threshold mapping;
- top reason selection;
- partial-evidence policy.

### 3.13 `worker`

Worker loop:

1. check database/storage/model readiness;
2. claim one `QUEUED` run atomically;
3. set `PROCESSING`, worker ID and heartbeat;
4. execute orchestrator stages;
5. persist each stage and evidence transactionally;
6. set `COMPLETED`, `PARTIAL` or `FAILED`;
7. create in-app notification;
8. release resources;
9. requeue or fail stale jobs according to retry policy.

Use bounded retries for transient failures and no automatic retry for invalid/corrupt input. Store a stable error code, not an internal stack trace, in user-visible fields.

## 4. Flask and API conventions

- Use an application factory: `create_app(config_name=None)`.
- Initialise extensions in `extensions.py`.
- Register versioned blueprints under `/api/v1`.
- Keep CLI commands available through the app factory.
- Configuration comes from environment variables validated at startup.
- Production startup uses Gunicorn or the selected WSGI server; never Flask's development server.
- Use one database session per request/worker unit of work.
- Always rollback after an exception.
- Return UTC timestamps in ISO 8601 with `Z`/offset.
- Use UUID strings in external APIs.
- Use snake_case JSON consistently unless a documented generated-client policy chooses otherwise.
- Use decimal-safe serialisation for money; do not use binary floating point for persisted amounts.
- Support `Idempotency-Key` on upload, analyse, report and reference-import commit routes.
- Attach `X-Request-ID` to every response and log entry.
- Pagination uses opaque/simple cursor or validated page/limit consistently. The initial contract may use `page`/`page_size` with a maximum of 100.
- Never return ORM objects directly.

## 5. Standard response conventions

### 5.1 Success resource

```json
{
  "data": {
    "id": "uuid",
    "type": "transaction",
    "attributes": {}
  },
  "meta": {
    "request_id": "uuid"
  }
}
```

A simpler `{"data": ..., "meta": ...}` contract is acceptable and is used throughout `05_API_CONTRACT.md`. Do not mix unrelated envelope styles.

### 5.2 Error

```json
{
  "error": {
    "code": "RECEIPT_INVALID_IMAGE",
    "message": "The selected file is not a supported receipt image.",
    "field_errors": {
      "receipt": ["Upload a JPEG, PNG or WEBP image."]
    },
    "request_id": "uuid"
  }
}
```

- 400: malformed request/business validation;
- 401: missing/invalid authentication;
- 403: authenticated but not permitted;
- 404: object not found or deliberately hidden by ownership policy;
- 409: state/idempotency/version conflict;
- 413: payload too large;
- 415: unsupported media;
- 422: schema/semantic validation where chosen consistently;
- 429: rate limit;
- 500: unexpected server error with generic public message;
- 503: required dependency unavailable.

## 6. Generated TypeScript client

- Export the OpenAPI document during backend CI.
- Generate TypeScript types/client into `packages/api-client`.
- Commit generated code only if the project chooses a deterministic generator and CI checks that it is current.
- Mobile and admin must use this client or shared generated types. Hand-written duplicate response types are prohibited for core resources.
- A contract change must update:
  1. backend schema;
  2. OpenAPI snapshot;
  3. generated client;
  4. client code;
  5. contract tests.

## 7. Analysis job architecture

### 7.1 Enqueue

`POST /api/v1/transactions/{id}/analyses`:

- verifies ownership/state;
- resolves idempotency key;
- snapshots active configuration IDs;
- creates `analysis_run` with `QUEUED`;
- returns `202 Accepted` and polling URL.

### 7.2 Claim

Worker query selects the oldest eligible queued row and locks it without blocking other workers. Store:

- `claimed_by`;
- `claimed_at`;
- `heartbeat_at`;
- `attempt_count`.

### 7.3 Recovery

A maintenance command identifies stale `PROCESSING` jobs whose heartbeat exceeded the configured interval:

- requeue transient/infrastructure failures below retry limit;
- mark failed when attempts exhausted;
- never duplicate completed evidence;
- audit recovery.

### 7.4 Progress

Persist named stages:

- `PREPARE_INPUT`;
- `OCR_SNAPSHOT`;
- `REFERENCE_VERIFICATION`;
- `IMAGE_FEATURES`;
- `CNN_INFERENCE`;
- `STRUCTURED_FEATURES`;
- `STRUCTURED_INFERENCE`;
- `RULE_EVALUATION`;
- `RISK_AGGREGATION`;
- `FINALISE`.

The mobile app polls the analysis resource using increasing intervals while active. It displays friendly stage text without exposing internal sensitive details.

## 8. Configuration hierarchy

1. code defaults safe for tests only;
2. environment variables;
3. database versioned configuration for templates/rules/thresholds/models;
4. per-run immutable snapshot.

Do not store secrets in the versioned configuration tables. Secrets remain in environment/secret management.

Important environment groups:

- application identity/build;
- database;
- JWT/session;
- CORS/CSRF;
- private storage;
- upload limits;
- Tesseract path/language;
- model artifact root;
- worker/retry;
- notification adapters;
- masking/retention;
- observability.

## 9. Money, phone and time

- Persist money as `NUMERIC(18,2)` or a documented compatible precision plus currency code.
- Use `Decimal` in Python.
- Store canonical Ghana phone format such as E.164 `+233...` where enough information exists; preserve masked/raw evidence separately when required.
- Store all timestamps as timezone-aware UTC.
- Retain the original OCR date/time string and the normalised timestamp plus a warning when timezone is inferred.

## 10. Logging and audit separation

### Operational logs

For debugging and metrics; may be rotated/deleted. Include request ID and safe context. Exclude receipt text, full phone/reference values, passwords, tokens and raw model features containing identifiers.

### Audit events

Persistent evidence of important actions. Store:

- actor ID and role;
- action code;
- target type/ID;
- request ID;
- outcome;
- safe metadata;
- UTC timestamp;
- source IP/user-agent hash or minimised representation according to privacy policy.

Audit events are append-only. A privileged export of audit data is itself audited.

## 11. Dependency readiness

`/health` proves the process is alive. `/ready` evaluates:

- database query;
- storage read/write/delete probe or configured non-destructive check;
- Tesseract executable/version;
- active structured model artifact;
- active CNN artifact;
- optional notification adapter.

Readiness may return a component matrix. The API itself may remain ready for non-analysis routes while an ML component is degraded; document the policy and expose `analysis_available` separately.

## 12. Engineering diagrams to maintain

Codex must maintain code-aligned engineering diagrams:

- deployment/container diagram;
- analysis data-flow diagram;
- state diagrams;
- implemented ERD;
- sequence diagrams for upload/OCR, analysis and case review.

Use Mermaid for repository maintainability where helpful. For academic submission, reproduce/export standards-based UML/ER diagrams with clear routing, no crossing through boxes/ellipses and correct multiplicities.
