# PR19 Full-Acceptance Release Design

**Date:** 2026-08-15  
**Phase:** Logical PR19 release hardening  
**Branch:** `codex/pr19-release-hardening`  
**Base:** merged logical PR18 at `5fe83763ebae19459bd49c8ddc5e0e35b67c2c03`

## 1. Purpose

PR19 turns the merged PR18 screenshot-analysis journey into a complete, locally demonstrable product for users, investigators, and administrators. It implements real casework, notifications, safe reports, staff operations, security and end-to-end verification, and a reproducible local release.

PR19 is one logical phase delivered as four contract-first vertical slices. Each slice crosses database, service, API, client, tests, and documentation where applicable, and each is independently reviewable before the next slice begins.

## 2. Acceptance boundary

PR19 is complete only when all of the following are true:

1. An owner can analyse a screenshot, understand separate fraud-risk and verification results, receive notifications, download a masked report, and report the transaction for review.
2. An investigator can find the case, inspect authorised evidence, assign or start review, add an append-only note, record a reasoned decision, and generate a case report.
3. An administrator can inspect operational aggregates, masked transactions, audit events, system readiness, and the safe state of rule and model registries.
4. Real security and end-to-end scenarios are registered in `scripts/verify_security.py`, `scripts/verify_e2e.py`, and `scripts/verify.py --all`.
5. PostgreSQL, API, admin portal, and mobile web can be started reproducibly for a local demonstration under the pinned runtimes.
6. Applicable formatting, linting, typing, tests, migrations, contract drift, secret scanning, security, end-to-end, and release checks pass with exact evidence.

The release boundary is local. Deployment configuration may be prepared and verified without secrets, but PR19 will not claim a public or hosted deployment because no deployment account or production credentials are in scope.

## 3. Non-goals and preserved boundaries

PR19 will not:

- train, promote, or activate an image or structured classifier;
- open a locked-test partition or report new final model metrics;
- activate the rejected P12 image artifact;
- claim live mobile-network-operator verification;
- replace stored/imported reference verification with a provider integration;
- mutate an automated analysis after it has been persisted;
- expose private receipts through a static/public path;
- add arbitrary model, rule, or receipt-template mutation merely to make portal pages appear functional;
- force dependency changes through `npm audit fix --force`; or
- claim a hosted deployment without successful deployment evidence.

Unavailable classifiers remain explicit unavailable evidence. Deterministic image evidence, OCR evidence, stored-reference verification, and policy limitations retain the contracts established in PR18.

## 4. Delivery architecture

### 4.1 Vertical slices

The implementation order is:

1. **Casework:** schema hardening, owner case creation/status, staff queue/detail, assignment, review, notes, decisions, audit events, and notifications caused by case events.
2. **Owner evidence:** analysis/high-risk notifications, notification inbox/read state, masked analysis and case reports, secure downloads, and the simplified mobile owner flow.
3. **Staff operations:** real dashboard, masked transaction search/detail, cases, audit log, system status, reports, and read-only model/rule views in the administrator portal.
4. **Release hardening:** real security and end-to-end gates, exact runtime enforcement, local orchestration, QA/security/deployment documentation, traceability, and handoff evidence.

All slices live on the one PR19 branch and use coherent conventional commits. A slice is not considered complete when only its UI or only its happy-path API exists.

### 4.2 Backend boundaries

The existing Flask layering is preserved:

- Blueprints perform authentication, role checks, input validation, pagination, rate limiting, and response serialization.
- Domain services own case state, notification creation/delivery, safe report rendering, operational projections, and transaction boundaries.
- SQLAlchemy models and repositories provide persistence without leaking ORM records into public responses.
- Private object storage stores report bytes and existing receipt artifacts.
- Audit writing remains append-only and is invoked for protected, denied, and evidential actions.

Case status changes may occur only through the casework service. Report templates may consume only explicit masked projections. Notification deep links are built from allowlisted target types, never from arbitrary stored URLs.

## 5. Persistence design

A new Alembic revision, `20260815_0004_pr19_release_hardening.py`, will extend the existing PR18 schema without rewriting historical evidence.

### 5.1 Fraud cases

`fraud_cases` gains an integer `version`, non-null with initial value `1`. Every successful assignment, review start, note, or decision checks `expected_case_version` and increments the version exactly once.

The existing partial uniqueness rule on `(transaction_id, source)` is replaced with a partial unique index on `transaction_id` for active statuses `OPEN`, `ASSIGNED`, `IN_REVIEW`, and `REOPENED`. This prevents parallel active investigations of the same transaction even when user and automated triggers race. A completed case does not prevent a later case from being opened when the product eventually supports that transition.

The existing `case_events` and `case_decisions` tables remain append-only. Notes use `CaseEvent(event_type="NOTE")`; assignments and transitions record both prior and next state. Decisions create a `CaseDecision` and a `CaseEvent(event_type="DECISION")` in the same transaction. Automated analysis rows are never updated by a human decision.

### 5.2 Notifications

`notifications` gains a non-secret `dedupe_key`. A unique `(user_id, dedupe_key)` constraint guarantees at-most-one in-app notification for one domain event. Delivery metadata contains adapter name, state, safe provider identifier when available, attempt count, and safe error code; it never contains credentials, full receipt values, or message bodies copied from private evidence.

### 5.3 Reports

`report_artifacts` continues to hold private artifact identity, exact SHA-256, state, owner, and expiry. It gains an optional `analysis_run_id` for immutable analysis snapshots and an optional `source_version` for case reports. These fields let idempotent generation return the artifact for the same evidence snapshot without returning a stale artifact after a new analysis run or case mutation.

Report bytes remain outside the database in private storage. Only `READY` artifacts are downloadable.

### 5.4 Migration verification

The migration must pass upgrade from an empty database, upgrade from `20260815_0003`, downgrade/upgrade of the new revision, model-versus-migration drift, and index/constraint assertions on PostgreSQL.

## 6. Casework contract

### 6.1 Owner case flow

`POST /api/v1/transactions/{transaction_id}/fraud-reports` requires the authenticated owner, a completed or partial analysis, a category, and an optional bounded description. Supported categories are `PAYMENT_NOT_RECEIVED`, `UNKNOWN_TRANSACTION`, `ALTERED_RECEIPT`, and `OTHER`.

The request accepts an `Idempotency-Key`. A first request creates an `OPEN` case, `OPENED` event, audit event, and case-opened notification. Replaying the same request returns the same resource. If any active case already exists for the transaction, the route returns that case instead of creating another. Database uniqueness is the final concurrency guard.

`GET /api/v1/fraud-reports/{case_id}` returns only a case reported by the current owner for their transaction. The owner projection includes category, status, timestamps, version, and a limited public timeline. It excludes internal notes, investigator identity, diagnostic links, staff-only metadata, and private receipt locations.

### 6.2 Staff case flow

The supported state flow is:

`OPEN -> ASSIGNED -> IN_REVIEW -> DECIDED`

An investigator starting an unassigned `OPEN` case may atomically assign it to themself and move it to `IN_REVIEW`. `REOPENED` remains a recognised historical state but no new reopen endpoint is added in PR19. Closing and reopening are deferred rather than invented outside the supplied API scope.

Staff endpoints are:

- `GET /api/v1/admin/cases`
- `GET /api/v1/admin/cases/{case_id}`
- `POST /api/v1/admin/cases/{case_id}/assign`
- `POST /api/v1/admin/cases/{case_id}/start-review`
- `POST /api/v1/admin/cases/{case_id}/notes`
- `POST /api/v1/admin/cases/{case_id}/decisions`
- `POST /api/v1/admin/cases/{case_id}/reports`
- `GET /api/v1/admin/cases/{case_id}/reports/{report_id}/download`

Case list filters are bounded and allowlisted: status, assignment, risk band, provider, source, and date range. Case detail combines a masked transaction projection, immutable PR18 analysis/evidence projections, protected receipt-view actions, report metadata, and an append-only timeline.

Assignment validates that the target is an active investigator. Notes require non-empty bounded text. Decisions allow `CONFIRMED`, `DISMISSED`, or `ESCALATED`, require a non-empty reason and expected version, and move the case to `DECIDED`. Every mutation is atomic across case state, version, timeline event, audit event, and in-app notification.

## 7. Notification contract

Mandatory in-app notification types are:

- analysis completed;
- analysis completed partially;
- configured high-risk outcome;
- case opened;
- case assigned;
- case review started/status changed; and
- case decision recorded.

Analysis completion integrates with the PR18 orchestrator inside the database transaction that finalises the analysis. A configured high-risk outcome may create or link an `AUTO_HIGH_RISK` case through the same casework service, preserving the one-active-case invariant.

Owner endpoints are:

- `GET /api/v1/notifications`
- `GET /api/v1/notifications/unread-count`
- `POST /api/v1/notifications/{notification_id}/read`
- `POST /api/v1/notifications/read-all`

All notification reads and mutations are scoped by `user_id`. Read operations are idempotent. Targets are returned as safe application target types and IDs; clients map them to allowlisted routes.

External email or push delivery remains optional. In-app notification persistence commits first. External delivery runs after commit through a bounded adapter. Adapter failure updates safe delivery metadata but never deletes or rolls back the notification or originating domain event.

## 8. Report contract

Owner report endpoints are:

- `POST /api/v1/transactions/{transaction_id}/reports`
- `GET /api/v1/reports/{report_id}/download`

Staff case report endpoints are listed in the casework contract. PR19 produces safe HTML reports; PDF and unbounded operational exports are not required for this phase.

Analysis reports include:

- separate fraud-risk and transaction-verification sections;
- plain-language reasons, limitations, and missing-signal states;
- component availability without fabricated probabilities;
- confirmed OCR field counts and safe masked transaction fields;
- deterministic evidence summaries;
- policy, OCR, rule, and model version identities; and
- the stored-reference/no-live-provider disclaimer.

Case reports add case status, timeline timestamps, human outcome, reason, actor role, and a clear statement that the human decision did not alter automated evidence.

Dynamic content is HTML-escaped by a controlled template renderer. Reports exclude raw images, object keys, storage paths, PINs, OTPs, credentials, full phone numbers, full references, private audit metadata, and internal exception text.

Generation follows `GENERATING -> READY` or `FAILED`. The service renders bytes, writes to a generated private object key, reads or verifies the stored bytes, computes their SHA-256, and marks the artifact ready only after the hash and evidence snapshot are recorded. Storage/database failures trigger best-effort deletion of incomplete objects and a failed artifact state. Downloads require ownership or authorised case access and set safe generated filename, `Cache-Control: private, no-store`, `Pragma: no-cache`, `X-Content-Type-Options: nosniff`, and a restrictive content-security policy.

## 9. Operational API and portal

The portal replaces feature-shell placeholders for the following real pages:

- dashboard;
- transactions list and transaction detail;
- cases list and case detail;
- reports;
- audit logs;
- system status;
- model registry; and
- rule sets.

The API surface is:

- `GET /api/v1/admin/dashboard`
- `GET /api/v1/admin/transactions`
- `GET /api/v1/admin/transactions/{transaction_id}`
- `GET /api/v1/admin/audit-logs`
- `GET /api/v1/admin/system-status`
- `GET /api/v1/admin/models`
- `GET /api/v1/admin/models/{model_id}`
- `GET /api/v1/admin/rule-sets`
- `GET /api/v1/admin/rule-sets/{rule_set_id}`

Dashboard aggregates cover risk state, verification state, case state/source, analysis completion state, average and p95 processing duration when present, active versions, and safe recent warnings for a bounded date range. Transaction lists are masked by default; protected evidence access occurs through audited detail and receipt routes. Audit metadata is already redacted before serialization. System status reports database, private storage, OCR/Tesseract, active model state, and optional notification adapter readiness without leaking host paths or credentials.

Model and rule views are read-only in PR19. They accurately show inactive, rejected, unavailable, or active state. The UI must not offer activation of the rejected P12 artifact or represent an unavailable classifier as ready.

## 10. Mobile and portal interaction design

### 10.1 Owner mobile experience

The default analysis result is intentionally concise. It shows:

1. a fraud-risk summary row;
2. a separate verification summary row;
3. one primary `View analysis details` action;
4. a report download action; and
5. a contextual `Report suspicious transaction` action.

Technical reasons, component availability, missing signals, evidence versions, and the no-live-provider disclaimer move to the details screen. A case card appears only after a case exists. Notifications use the existing tab and display unread state plus safe deep links. This progressive-disclosure design replaces the initially rejected cluttered single-screen concept.

### 10.2 Staff portal experience

The investigator case workspace is intentionally denser. It presents case state/version, masked transaction and OCR data, separate risk and verification blocks, component availability, protected evidence actions, an append-only timeline, notes, and a confirmed decision action. Reviewer decisions require confirmation and a reason.

Every user and staff page implements loading, empty, retryable error, offline where relevant, permission-denied, and stale-version states. Statuses include text and icons; colour is never the only signal.

## 11. Error, concurrency, and security behavior

- Missing authentication returns `401`.
- Authenticated callers lacking the required role return `403`.
- Foreign or unauthorised object identifiers return `404` to prevent enumeration.
- Invalid input returns the standard structured validation envelope.
- Stale versions and illegal case transitions return `409` without partial domain writes.
- Storage or required dependency failures return a safe `503`; internal paths and causes are logged only through redacted structured events.
- Every list uses bounded pagination, allowlisted sort fields, allowlisted filters, and bounded date ranges.
- Case descriptions, notes, and reasons have explicit size limits and are escaped in reports and UIs.
- Protected mutations retain the existing server-side role, object-ownership, CSRF/session, and rate-limit policies appropriate to mobile bearer tokens and portal sessions.
- Every denied or successful evidential access is audited without full receipt values, tokens, report content, object keys, or full identifiers.

## 12. Verification design

### 12.1 Automated coverage

Backend tests cover service state machines, transaction atomicity, optimistic locking, active-case races, notification deduplication, report hashing, safe projection, storage compensation, filters, pagination, audit events, and every endpoint's authentication/role/ownership matrix.

Mobile tests cover the concise result screen, details disclosure, report generation/download, case creation/existing-case behavior, case status, notifications, unread/read-all, safe deep links, offline/retry states, and foreign-object denial.

Admin tests cover all real pages, staff role differences, case mutation conflicts, dashboard aggregate parity, masked transaction detail, audit filtering, system dependency states, unavailable model/rule presentation, accessibility, responsive layouts, and error states.

### 12.2 Real security gate

`scripts/verify_security.py` exercises:

- cross-owner identifier substitution;
- USER/ADMIN/INVESTIGATOR route matrix;
- stale case updates and duplicate case races;
- report HTML/script injection and escaping;
- report download ownership and headers;
- private object key, path, receipt value, and audit metadata leakage;
- notification ownership and deep-link allowlisting;
- pagination, input, and rate-limit boundaries; and
- the repository secret/prohibited-artifact scan.

The script exits non-zero if a required scenario is skipped or cannot run.

### 12.3 Real end-to-end gate

`scripts/verify_e2e.py` provisions or targets the controlled local stack and proves this workflow:

1. owner authentication;
2. controlled screenshot upload, OCR confirmation, and PR18 analysis;
3. separate risk/verification presentation;
4. notification receipt;
5. masked report creation/download;
6. fraud case creation;
7. investigator queue, assignment/review, note, and decision;
8. owner case-status/notification update; and
9. administrator aggregate, audit, readiness, model, and rule visibility.

The gate uses only controlled fictitious fixtures and validates API plus browser/mobile-web behavior. It cannot claim success when it used placeholder routes or omitted the staff decision path.

### 12.4 Repository gate

`scripts/verify.py --all` registers backend, mobile, admin, ML regression, OpenAPI, ER, migrations, security, end-to-end, secret scanning, and release readiness. Applicable failures remain non-zero. Exact pass counts and coverage are recorded only from fresh final commands.

## 13. Runtime and local release

Frontend work and final release verification use exactly Node `24.14.0` and npm `10.9.0`. An isolated pinned runtime or supported version manager may be used when the host default remains Node 22; generated runtime binaries and caches are never committed. The doctor and documentation must agree on the exact versions.

No `npm audit fix --force` is permitted. Project-owned critical or high security findings block PR19. Supported Expo/React Native transitive advisories that lack a compatible upstream fix remain explicitly tracked under `B-SEC-002`; they are not hidden by incompatible downgrades.

The local release starts PostgreSQL, the Flask API, the Vite administrator portal, and Expo mobile web with documented commands, migrations, controlled seeds, health/readiness probes, restart behavior, and rollback instructions. Secrets are supplied only through local environment configuration based on `.env.example`. Private receipts and reports remain mounted outside public frontend roots.

## 14. Documentation and evidence

PR19 updates:

- `IMPLEMENTATION_STATUS.md`;
- `requirements_traceability.csv`;
- `CHANGELOG.md`;
- `DECISION_LOG.md` for compatibility/runtime decisions;
- API/OpenAPI documentation;
- QA, security, local deployment, rollback, and demonstration runbooks; and
- a session handoff based on `templates/SESSION_HANDOFF.md`.

The final handoff records the exact base SHA, head SHA, branch, migration revision, commands, pass/fail output, coverage, local runtime identities, secret scan count, local release probes, known external blockers, push result, and pull-request state. Hosted CI remains reported accurately if the GitHub Actions billing lock still prevents runner allocation.

## 15. Completion rule

PR19 is not complete because screens exist or because individual package tests pass. It is complete only when the controlled owner-to-investigator-to-administrator workflow works end to end, all applicable local gates are green under the pinned runtime, no unresolved project-owned critical/high finding remains, documentation matches the implementation, the branch is committed and pushed, and the pull request reports exact evidence without overstating deployment, classifier readiness, or provider verification.
