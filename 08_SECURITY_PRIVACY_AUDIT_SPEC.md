# 08 — Security, Privacy and Audit Specification

## 1. Security objectives

1. Only authenticated, authorised actors can access protected resources.
2. A normal user can access only their own receipts, analyses, reports, cases and notifications.
3. Private receipt and model artifacts are never public by default.
4. Uploaded files cannot execute code, escape storage paths or exhaust resources unchecked.
5. Authentication secrets and production credentials never enter Git, logs or client bundles.
6. Automated evidence and privileged decisions are traceable.
7. Model/data pipelines do not load untrusted executable artifacts.
8. Security failures degrade safely and are visible to operators.

## 2. Data classification

### Restricted

- original receipt images;
- unmasked phone numbers;
- full transaction references;
- reference-transaction raw rows;
- authentication/session/reset material;
- model/storage/database secrets;
- investigator notes containing personal information;
- private datasets.

### Confidential

- OCR text and field values;
- image evidence;
- fraud probabilities/features;
- verification comparisons;
- user profiles;
- case reports;
- audit metadata.

### Internal

- model/rule/template versions;
- operational metrics;
- non-sensitive logs;
- deployment architecture.

### Public

- generic help text;
- API liveness status with no infrastructure details;
- academic description and anonymised aggregate results.

Every API schema and UI view should be reviewed against this classification.

## 3. Threat model

### 3.1 Account and session threats

- credential stuffing/brute force;
- account enumeration;
- stolen refresh token;
- refresh-token reuse;
- weak password reset;
- session fixation;
- role escalation;
- disabled account retaining access;
- last-admin removal.

### 3.2 Object-access threats

- IDOR by changing transaction/report/case IDs;
- staff opening records outside purpose/role;
- report/signed URL reuse;
- private receipt path guessing;
- over-broad list/search endpoints;
- mass assignment of owner/role/status fields.

### 3.3 Upload and image threats

- renamed executable/non-image;
- polyglot content;
- corrupt parser payload;
- path traversal filename;
- decompression bomb/extreme dimensions;
- excessive CPU/memory image;
- animated/multi-frame abuse;
- malicious metadata;
- duplicate/replay flooding;
- SVG/script content (not accepted);
- storage orphan/inconsistent state.

### 3.4 API/web threats

- SQL injection;
- XSS from OCR text/import data/case notes;
- CSRF in cookie-authenticated portal;
- CORS misconfiguration;
- request smuggling/proxy header misuse;
- denial of service/rate abuse;
- insecure error messages;
- unbounded pagination/export;
- insecure direct file download;
- missing idempotency.

### 3.5 ML/data threats

- untrusted pickle/model deserialisation;
- artifact substitution;
- training-data leakage;
- poisoned labels/data;
- private dataset committed;
- model inversion/excessive raw output;
- fake metrics or stale model activation;
- feature-schema drift;
- adversarial/unsupported image causing unreliable confidence.

### 3.6 Operations/supply-chain threats

- leaked `.env`;
- vulnerable dependency;
- malicious package;
- excessive CI permissions;
- unsigned/unverified deployment;
- database backup exposure;
- public object-storage bucket;
- logs containing tokens/PII;
- production debug mode;
- stale credentials;
- missing rollback.

## 4. Authentication controls

- adaptive password hashing with a project-approved cost/parameters;
- password minimum policy and rejection of obviously invalid values;
- generic login/reset errors;
- per-IP and per-account-aware throttling without exposing account existence;
- short access-token lifetime;
- refresh-token rotation;
- server-side refresh-session revocation;
- refresh-family reuse detection;
- reset token:
  - cryptographically random;
  - stored as hash;
  - single use;
  - short expiry;
  - invalidated after password change;
- revoke sessions on account disable and sensitive role/password changes;
- `token_version` or equivalent invalidation;
- secure web refresh cookie:
  - HTTP-only;
  - Secure in non-local environments;
  - SameSite policy documented;
  - narrow Path/Domain;
- CSRF token/double-submit or equivalent for cookie-authenticated state changes;
- mobile credentials in Expo SecureStore only;
- no API secret embedded in mobile/admin.

Optional MFA is out of the minimum prototype unless time allows, but architecture must not prevent it.

## 5. Authorisation controls

### 5.1 Central policy

Every service method receives a principal and calls a policy/ownership function. Do not trust:

- `user_id` from request body;
- hidden UI routes;
- client role claims not verified by server token/database;
- object IDs as proof of access.

### 5.2 Ownership lookup

Use queries such as:

```text
SELECT ... WHERE id = :id AND user_id = :principal_id
```

or a policy-scoped repository. For normal users, a foreign object should generally appear as not found to avoid enumeration.

### 5.3 Staff access

- ADMIN: configuration, users, imports, audit and operational views.
- INVESTIGATOR: case/evidence needed for review.
- Combined role only when assigned.
- Every full evidence access by staff is audited.
- Default lists mask personal values.
- Bulk export is separately authorised and audited.

### 5.4 State/action authorisation

Permission depends on role, ownership and current state. Example: a user cannot edit OCR after final analysis; an investigator cannot decide a closed case without authorised reopen.

## 6. File-upload controls

Server-side sequence:

1. authenticate and rate limit;
2. enforce content length before reading all bytes where possible;
3. stream to a controlled temporary/private location;
4. ignore user path; generate object key;
5. allowlist extension;
6. inspect magic/decode content;
7. decode with safe library limits;
8. enforce dimensions/pixel count/frame count;
9. reject unsupported format/polyglot indicators;
10. strip or ignore dangerous metadata in derived copies;
11. calculate hash;
12. move/write immutable original to private storage;
13. create database rows transactionally;
14. delete temp file;
15. audit outcome.

Accepted formats: JPEG, PNG, WEBP. Do not accept SVG, PDF, HTML or office documents as receipt images in the MVP.

Suggested configurable defaults:

- max upload: 10 MB;
- max pixel count: 25–40 million, chosen after testing;
- minimum dimensions sufficient for OCR;
- request timeout;
- per-user/day upload rate appropriate to prototype testing.

Values are configuration and must be justified by performance tests.

## 7. Private file delivery

- No permanent public URL.
- API checks role/ownership before stream or signed URL.
- Signed URL expires quickly and is scoped to one object/method.
- `Content-Disposition` uses generated filename.
- Use `X-Content-Type-Options: nosniff`.
- Image response content type comes from validated stored metadata.
- Staff diagnostic variants require staff permission.
- Download/report/image access creates an audit event where required.
- Cache headers prevent unintended shared caching for sensitive files.

## 8. API security

- HTTPS outside localhost.
- Strict CORS allowlist; credentials only with explicit origins.
- Security headers for web portal/API responses where applicable.
- Request/body limits at proxy and Flask.
- Schema validation rejects unknown sensitive fields or uses explicit allowlists.
- ORM parameterisation; raw SQL only with bound parameters.
- Encode/escape all OCR/import/case text in React; never use unsafe HTML.
- CSRF for cookie-authenticated mutations.
- Rate limits:
  - login/reset/register;
  - upload/OCR/analyse;
  - report/export;
  - reference import;
  - case decisions/model activation.
- Pagination maximums and export row limits.
- Idempotency for retry-prone mutations.
- Consistent error messages; no debug mode or trace in production.
- Validate forwarded headers only behind configured trusted proxy.
- Timeouts for Tesseract, model inference, storage and external adapters.

## 9. Input validation

Examples:

- email canonical validation and length;
- password length/maximum to avoid hashing DoS;
- UUID parsing;
- enum allowlists;
- decimal amount range/precision;
- date range and timezone;
- phone canonicalisation;
- transaction-reference allowed length/characters;
- note/description length;
- CSV row/column/total size;
- JSONB configuration schema;
- risk weights non-negative and expected sum;
- thresholds ordered;
- model version/hash format;
- safe sorting/filter fields.

Reject unknown role/status/owner fields in normal requests.

## 10. Output encoding and XSS

OCR text, imported names and investigator notes are untrusted text.

- React renders text, not HTML.
- Never use `dangerouslySetInnerHTML` for evidence/case content.
- Generated PDFs escape content.
- CSV exports defend against formula injection by prefixing dangerous leading characters (`=`, `+`, `-`, `@`) according to export policy.
- Filenames are generated.
- Content Security Policy is set on the web portal where deployment permits.
- No secret values in source maps or build-time public environment variables.

## 11. Model artifact security

- Model upload/registration is ADMIN-only.
- Store artifacts privately.
- Verify SHA-256 before load.
- Restrict supported model types/formats.
- Prefer non-executable/safe serialisation.
- Never load a user-provided pickle/joblib object directly.
- Run smoke inference with bounded resources.
- Record framework versions.
- A corrupt/mismatched artifact becomes unavailable; it does not crash every request.
- Model activation is audited.
- Workers reload active model only after successful readiness verification.

## 12. Secrets management

`.env.example` contains keys, not real values.

Secrets include:

- database URL;
- JWT/session secrets;
- CSRF secret;
- object-storage credentials;
- notification-provider keys;
- email credentials;
- admin bootstrap password;
- error-monitoring DSN where sensitive.

Rules:

- no secrets in Git history;
- no secrets in issue/PR descriptions;
- no secrets in screenshots;
- no `EXPO_PUBLIC_`/`VITE_` variable for private keys;
- rotate a secret immediately if exposure is suspected;
- CI receives least-privilege secrets;
- production and staging secrets differ;
- local developer `.env` excluded.

## 13. Logging and redaction

Never log:

- passwords;
- access/refresh/reset tokens;
- full Authorization/Cookie headers;
- full receipt OCR text by default;
- full phone/reference;
- raw import rows;
- object-storage credentials;
- private signed URLs;
- raw model artifacts/features with identifiers.

Log safe:

- request ID;
- route/method/status/duration;
- actor ID, not email where possible;
- target IDs;
- stable error codes;
- stage timings;
- model/rule/template version IDs;
- safe aggregate counts.

OCR text-fraud logs, stage details and audit metadata may additionally retain
only the assessment/schema/ruleset version, status, categorical class,
allowlisted reason codes and evidence quality. They must not retain the matched
substring, raw OCR text, a phone number, URL, PIN/OTP-like value or other dynamic
message value. Public OCR replay uses the stored allowlisted projection and does
not re-run rules against historical private text.

Implement a logging filter/redaction helper and tests with representative sensitive payloads.

## 14. Audit-event catalogue

At minimum audit:

### Authentication

- login success/failure;
- logout;
- refresh reuse/revocation;
- password reset requested/completed;
- account disabled/enabled;
- session revoke.

### Evidence

- receipt uploaded/rejected/viewed/downloaded;
- OCR confirmed/corrected;
- analysis queued/completed/partial/failed;
- report generated/downloaded;
- user fraud report.

### Privileged

- staff evidence accessed;
- user/role changed;
- reference import uploaded/validated/committed;
- template/rule/model created/activated/retired/rolled back;
- case assigned/note/decision/reopen;
- audit/export accessed;
- configuration changed.

Audit metadata is minimised and append-only.

## 15. Privacy controls

### 15.1 Minimisation

Collect only fields necessary for receipt analysis, verification, user contact and audit. Do not collect wallet PIN, OTP, balance or unrelated SMS content.

### 15.2 Masking

Default display examples:

- phone: `+233 24 *** 0001`;
- reference: `ABC1••••56`;
- email in staff lists: partially masked where full value is unnecessary.

Owners may view confirmed details for their own receipt. Staff full access is role/purpose controlled and audited.

### 15.3 Research data

- consent/licence documented;
- anonymise names, phones and references;
- separate private raw and derived research data;
- do not commit raw data;
- dataset manifest stores permission reference;
- revoke/delete according to policy;
- synthetic samples clearly labelled.

### 15.4 Data subject/account actions

Implement configurable deactivation/deletion workflow. Do not promise legal rights or periods not defined by the institution; provide technical support for export, deactivation, anonymisation and scheduled deletion.

### 15.5 Human decision transparency

Store original automated result, reviewer outcome and reason separately. The user-facing status should indicate whether a human review occurred.

## 16. Availability and abuse controls

- per-route rate limits;
- per-user concurrent analysis cap;
- queue depth and stale worker monitoring;
- bounded image/model/Tesseract resources;
- worker process isolation from web workers;
- database query timeouts/limits where appropriate;
- report/export limits;
- retry with exponential backoff for transient storage/notification failure;
- circuit/degraded state for unavailable model;
- health/readiness and worker heartbeat;
- backup and restore.

Do not endlessly retry invalid input.

## 17. Dependency and CI security

- lock dependency versions;
- automated dependency audit;
- secret scanning;
- static lint/type analysis;
- minimal container image;
- non-root container user;
- no unnecessary compiler/dev tools in runtime image where practical;
- container/image vulnerability scan if available;
- least-privilege GitHub Actions permissions;
- pin third-party actions to trusted versions/commit policy;
- protect `main` with required CI review where repository settings permit.

## 18. Security test catalogue

### Authentication

- brute/rate limit;
- generic unknown-user response;
- expired/altered token;
- refresh reuse;
- reset reuse/expiry;
- disabled user;
- session revoke.

### Authorisation

- cross-user transaction/receipt/report/notification;
- user staff endpoint;
- investigator admin config;
- admin investigator decision when capability absent;
- object ID enumeration;
- last-admin safeguard;
- optimistic case/config conflict.

### Upload

- corrupt;
- renamed executable;
- fake MIME;
- path traversal filename;
- oversized bytes;
- extreme dimensions/decompression bomb;
- animated/multi-frame;
- unsupported SVG/PDF;
- duplicate/replay;
- storage failure cleanup.

### Web/API

- mass assignment;
- SQL/injection payloads;
- XSS strings in OCR/import/note;
- CSRF;
- CORS;
- unbounded page/export;
- CSV formula injection;
- unsafe error;
- request ID/log injection.

### Artifact/data

- corrupt model;
- wrong artifact hash;
- unsupported model format;
- feature schema mismatch;
- private dataset path committed;
- split leakage.

### Operational

- secret scan;
- public storage check;
- production debug disabled;
- HTTPS/security headers;
- backup access;
- stale worker recovery.

## 19. Incident response outline

1. Detect through logs/monitoring/user report.
2. Preserve relevant audit evidence.
3. Revoke affected sessions/credentials.
4. Disable compromised adapter/model/config if needed.
5. Contain private storage/database access.
6. Assess affected users/data.
7. Rotate secrets.
8. Patch and test.
9. Restore/verify service.
10. Document timeline, impact and corrective action.

Codex prepares the runbook; the institution defines notification/legal obligations.

## 20. Security release gate

Release is blocked by:

- public receipt/reference/model storage;
- cross-user access;
- staff role bypass;
- committed real secret;
- arbitrary model deserialisation;
- plaintext password/token;
- production debug trace;
- destructive untested migration;
- unresolved critical dependency vulnerability with reachable impact;
- false live-MNO/verification claim;
- audit absence for reviewer/configuration decisions.

No “temporary” bypass may remain enabled in staging/production.
