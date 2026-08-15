# 01 — Codex Master Implementation Plan

> **Roadmap reconciliation (2026-08-10):** P00-P12 below preserve the actual historical phase record. For new logical PR10-PR20 work, use `docs/plans/MoMo_Fraud_Detection_PR10_PR20_Colab_Blueprint.md` together with `docs/audits/pr10-pr12-gap.md`. Do not duplicate completed GitHub PRs or silently apply breaking taxonomy/API changes.

## 1. Purpose

This is the execution plan Codex must follow from an empty or partially existing repository through final deployment and inspection. It is intentionally organised into bounded phases so that each session produces a pushed, testable increment and a precise handoff. It is not permission to skip detailed specifications in the other files.

## 2. Delivery strategy

The project uses a Scrum-inspired incremental process. One Codex session should normally complete one phase or one clearly declared subset of a phase. Codex must not begin a later phase while a prerequisite phase has unresolved critical defects.

### Critical path

`P00 -> P01 -> P02 -> P03 -> P06 -> P07 -> P08 -> P09 -> P10 -> P11/P12 -> P13 -> P14/P15/P16 -> P17 -> P18 -> P19 -> P20`

`P04` and `P05` may proceed after `P03` and can run in parallel with some backend work, but the API contract remains the source of truth.

## 3. Delivery modes

### Mode A — New repository

Codex creates the monorepo, initial branch structure, local environment and all applications.

### Mode B — Existing partial repository

Codex first inventories what exists, maps it to the requirements, preserves correct work, writes an explicit gap report and then follows the phases. It must not delete working code merely to match a preferred template.

## 4. Repository-level definition of done

The whole project is complete only when all of the following are true:

- every `MUST` requirement in `02_SYSTEM_REQUIREMENTS_SPECIFICATION.md` is implemented or has an explicitly approved exception;
- `requirements_traceability.csv` maps every requirement to code, database/API/UI artefacts and tests;
- all database migrations run from zero and from the previous released revision;
- the mobile application completes the primary user journey;
- the web portal completes the administrator and investigator journeys;
- OCR, image analysis, structured ML, reference verification and risk aggregation are integrated through one persisted analysis run;
- model and dataset claims are reproducible;
- role and ownership tests prevent cross-user access;
- raw receipts are private;
- CI and the root verification command pass;
- deployment instructions are verified on staging or clearly document the one remaining external credential blocker;
- `FINAL_HANDOFF.md` is complete and references an exact pushed SHA.

## 5. Cross-phase engineering rules

1. **Contract first.** Update the OpenAPI/API contract before changing client-visible behaviour.
2. **Migration first.** Add a migration before code begins depending on a new column or table.
3. **Tests with behaviour.** Do not postpone core tests to P18.
4. **No fabricated intelligence.** Until a model is trained, return a declared model-unavailable or baseline-rule result.
5. **Safe defaults.** Unknown provider, missing field, no reference record or insufficient image quality must not silently become `GENUINE`.
6. **Evidence preservation.** Store original evidence and append derived evidence; do not mutate originals.
7. **Traceability.** Every risk result must point to an analysis run, receipt, model version, rule version and verification result.
8. **Idempotency.** Repeating a create/analyse request with the same idempotency key must not create uncontrolled duplicates.
9. **Separation of concerns.** UI, API, service, repository, persistence and ML layers must remain independently testable.
10. **Honest handoff.** A blocker is acceptable; a false completion statement is not.

## 6. Recommended phase branch map

| Phase | Branch |
|---|---|
| P00 | `codex/p00-preflight-foundation` |
| P01 | `codex/p01-api-infrastructure` |
| P02 | `codex/p02-database-storage` |
| P03 | `codex/p03-auth-rbac` |
| P04 | `codex/p04-mobile-shell` |
| P05 | `codex/p05-admin-shell` |
| P06 | `codex/p06-receipt-upload` |
| P07 | `codex/p07-ocr-review` |
| P08 | `codex/p08-reference-verification` |
| P09 | `codex/p09-image-forensics` |
| P10 | `codex/p10-dataset-tooling` |
| P11 | `codex/p11-structured-model` |
| P12 | `codex/p12-cnn-model` |
| P13 | `codex/p13-risk-orchestration` |
| P14 | `codex/p14-history-reports-notifications` |
| P15 | `codex/p15-case-governance` |
| P16 | `codex/p16-dashboard-analytics` |
| P17 | `codex/p17-ui-accessibility` |
| P18 | `codex/p18-hardening-qa` |
| P19 | `codex/p19-deployment-release` |
| P20 | `codex/p20-final-handoff` |

## 7. Phase execution template

For every phase Codex must:

1. confirm prerequisites and current SHA;
2. name the requirement IDs addressed;
3. implement the smallest complete vertical slice;
4. add tests and fixtures;
5. run phase gates;
6. update traceability, status, decision log and changelog;
7. capture requested screenshots/evidence;
8. commit and push;
9. complete the session handoff.

The following sections define the work.


## P00 — Repository preflight, scope lock and execution foundation

**Goal:** Establish an auditable starting point without losing any existing work.

**Prerequisites:** Git installed; repository path available or permission to initialise a new repository.

### Required work

1. Record repository remote, default branch, current branch, HEAD SHA, worktree status, tracked languages, package managers and existing CI.
2. Search for existing mobile, web, API, database, ML, documentation and deployment code. Produce `docs/implementation/P00_GAP_ANALYSIS.md` mapping retained, missing, conflicting and obsolete elements.
3. Copy or preserve this implementation package in the repository. Ensure root `AGENTS.md` applies.
4. Create `IMPLEMENTATION_STATUS.md`, `DECISION_LOG.md`, `CHANGELOG.md` and traceability/backlog files if absent; never reset completed evidence.
5. Create `.gitignore`, `.editorconfig`, `.gitattributes`, root README and a security note. Exclude `.env*` except `.env.example`, private uploads, datasets, model binaries, caches, build output and coverage output.
6. Choose and document Node and Python versions. Use Python 3.12 unless the target machine demonstrates an incompatible dependency; record any change.
7. Create cross-platform scripts: `scripts/bootstrap.py`, `scripts/verify.py`, `scripts/check_secrets.py` and `scripts/doctor.py`. Initially, scripts may report unimplemented project sections but must fail honestly.
8. Create GitHub issue labels/milestones or a local equivalent derived from `backlog.csv`. Do not spend the phase implementing features.
9. Create the phase branch, commit the foundation, push it and record the remote branch.

### Deliverables

1. Gap analysis and repository inventory
2. Root engineering policy and ignore files
3. Status/decision/changelog/traceability baseline
4. Cross-platform project scripts
5. First pushed phase branch

### Phase verification

1. `python scripts/doctor.py` reports toolchain and missing dependencies
2. `python scripts/check_secrets.py` finds no committed secret
3. `git status --short` is clean after commit
4. Repository can be cloned and documentation paths resolve

### Exit criterion

The exact starting SHA and all retained work are documented; the next developer can reproduce the repository state.


## P01 — Monorepo, API skeleton and local infrastructure

**Goal:** Create a runnable architecture with health checks before domain features.

**Prerequisites:** P00 complete.

### Required work

1. Create the monorepo layout defined in `03_ARCHITECTURE_AND_REPOSITORY_SPEC.md`: `apps/mobile`, `apps/admin`, `services/api`, `ml`, `docs`, `infra`, `scripts` and shared contract locations.
2. Create the Python project with Flask application factory, configuration classes, environment validation, blueprints, structured JSON errors, request IDs and `/api/v1/health`, `/ready` and `/version` endpoints.
3. Create initial OpenAPI generation and an API-contract check. API documentation must be generated from the actual request/response schemas.
4. Create PostgreSQL and API services in Docker Compose. Add health checks, named volumes and a Tesseract-equipped API image.
5. Add SQLAlchemy session management, database readiness check and a placeholder initial migration.
6. Add structured application logging with correlation/request IDs and sensitive-field redaction.
7. Add strict development CORS for known local mobile/admin origins; never use wildcard credentials in production.
8. Create backend formatting, linting, typing and test configuration.
9. Create a root command that starts local dependencies and a root verification command that invokes existing checks.
10. Document Windows, macOS/Linux and Docker bootstrap steps.

### Deliverables

1. Runnable Flask API
2. PostgreSQL local service
3. OpenAPI skeleton
4. Backend CI-ready quality configuration
5. Local setup documentation

### Phase verification

1. Health endpoint returns service version and no secret data
2. Ready endpoint fails when PostgreSQL is unavailable and passes when available
3. Unknown route returns standard JSON error envelope
4. Clean Docker build succeeds
5. Backend lint/type/unit smoke tests pass

### Exit criterion

A clean clone can start the API and database and receive healthy responses using documented commands.


## P02 — Relational schema, migrations, seeds and private storage abstraction

**Goal:** Build the persistent evidence model before feature code.

**Prerequisites:** P01 complete.

### Required work

1. Implement all tables, enums, constraints, relationships and indexes specified in `04_DATABASE_AND_STORAGE_SPEC.md`.
2. Use UUID primary keys, timezone-aware UTC timestamps and explicit enum/check constraints. Define creation/update conventions.
3. Implement Alembic/Flask-Migrate revisions with deterministic names and downgrade paths where safe.
4. Create a storage interface with local-private and S3-compatible implementations. The API chooses the adapter by configuration.
5. Implement generated object keys, SHA-256 hashing, content metadata, private retrieval and deletion/retention hooks.
6. Create seed commands for roles, a bootstrap administrator, demo receipt templates, default fraud rules and test reference records. Bootstrap credentials must come from environment variables and must be changed.
7. Create database factories/fixtures for users, transactions, receipts, OCR results, analyses, models, reference records, cases, notifications and audits.
8. Add soft-deactivation where required; do not soft-delete immutable audit/evidence rows.
9. Add migration tests from an empty database and schema-integrity tests.
10. Generate an engineering ER diagram from the implemented schema and note differences from the Chapter Three diagram.

### Deliverables

1. Versioned schema and migrations
2. Storage adapter interface
3. Seed and fixture tooling
4. Implemented-schema ER reference
5. Database tests

### Phase verification

1. Upgrade from zero to head succeeds
2. Downgrade/upgrade smoke path succeeds for reversible migrations
3. Uniqueness, foreign key and check constraints reject invalid rows
4. Private storage does not expose a public path
5. Deletion/retention routines preserve audit requirements

### Exit criterion

Every persistent object required by later phases has a stable schema and test fixture.


## P03 — Authentication, session security, ownership and RBAC

**Goal:** Secure all identities and establish role boundaries before sensitive features.

**Prerequisites:** P02 complete.

### Required work

1. Implement registration, login, refresh, logout/revocation, current-user, forgot-password and reset-password endpoints.
2. Hash passwords using a suitable adaptive password hash. Never log passwords or reset tokens.
3. Implement short-lived access tokens and rotated refresh tokens. Store only a hash/fingerprint of server-tracked refresh tokens where revocation is required.
4. Implement role decorators/policies for `USER`, `ADMIN` and `INVESTIGATOR`, including combined capabilities.
5. Implement object-level ownership policies so a user cannot access another user's transaction by changing an ID.
6. Implement web refresh through a secure HTTP-only cookie and CSRF protection for cookie-authenticated state changes; keep browser access tokens in memory where used.
7. Define mobile secure-token storage contract for Expo SecureStore. No token in AsyncStorage.
8. Rate-limit login, refresh, password reset and registration; make authentication errors non-enumerating.
9. Audit login success/failure, password reset, role changes, account deactivation and refresh-token revocation.
10. Add admin user-management endpoints only after server-side role checks are complete.
11. Create test accounts through seed tooling, not hard-coded production credentials.

### Deliverables

1. Complete authentication API
2. RBAC/ownership policy layer
3. Reset-token workflow
4. Auth audit events
5. OpenAPI/auth test suite

### Phase verification

1. Register/login/refresh/logout/reset happy paths
2. Expired/revoked/altered tokens rejected
3. Wrong role receives 403; unauthenticated receives 401
4. Cross-user ID access receives 404/403 without leaking object existence
5. Rate limit and generic reset response tested
6. Cookie security/CSRF behaviour tested for web portal

### Exit criterion

No receipt or admin feature can be reached without the correct authenticated role and ownership.


## P04 — Mobile application shell, design system and authentication experience

**Goal:** Create the user-facing mobile foundation with production-quality navigation and states.

**Prerequisites:** P03 API contract stable.

### Required work

1. Scaffold Expo React Native TypeScript and Expo Router using the repository's pinned Node/package-manager version.
2. Create theme tokens for spacing, typography, radius, elevation and semantic statuses. Use icons/text in addition to colour.
3. Create reusable components: screen shell, header, button, input, password input, form error, card, status badge, alert, skeleton, empty state, retry state, confirmation sheet and secure image preview.
4. Implement splash/session restoration, login, registration, forgot-password, reset-password, profile and logout flows.
5. Use React Hook Form and Zod (or the documented selected equivalents) with shared validation semantics.
6. Use TanStack Query for server state, a small dedicated auth/session store and Expo SecureStore for tokens.
7. Create bottom-tab/navigation skeleton: Home, History, Notifications and Profile, plus the central Upload/Scan action.
8. Implement offline/network awareness, API error mapping, global error boundary and retry behaviour.
9. Add accessibility labels, focus order, keyboard handling, dynamic-text support and safe-area support.
10. Create component/unit tests and a smoke E2E path through authentication using a test API.

### Deliverables

1. Runnable mobile app
2. Auth screens and secure session
3. Reusable mobile component library
4. Navigation and state handling
5. Mobile test baseline

### Phase verification

1. Type check, lint and tests pass
2. Token is stored only in secure storage
3. Session restoration and logout work
4. Form validation and server errors are accessible
5. Common Android viewport has no overflow or hidden controls

### Exit criterion

A user can securely authenticate and reach a stable application shell.


## P05 — Administrator and investigator web portal shell

**Goal:** Create the role-aware web workspace before dashboard features.

**Prerequisites:** P03 API contract stable.

### Required work

1. Scaffold React + TypeScript + Vite with React Router and a route-level permission guard.
2. Create a responsive design system and reusable data-table, filter, pagination, dialog, drawer, form, badge, chart-container, skeleton and error components.
3. Implement administrator/investigator login, session refresh, logout and permission-aware navigation.
4. Create shell routes for Dashboard, Transactions, Cases, Users, Reference Imports, Templates, Rules, Models, Reports, Audit Logs and System Status.
5. Implement a no-access page, 404 page, global error boundary and session-expired behaviour.
6. Use TanStack Query for server state and React Hook Form/Zod for forms.
7. Create secure download handling for private reports/evidence through authenticated API calls.
8. Add responsive breakpoints for desktop and tablet; tables must have accessible mobile/tablet alternatives where needed.
9. Set up unit/component tests and Playwright smoke tests.
10. Generate a production build in CI.

### Deliverables

1. Runnable web portal shell
2. Role-aware navigation
3. Reusable web component library
4. Auth/session workflow
5. Web test baseline

### Phase verification

1. Admin and investigator see only allowed navigation/actions
2. Refresh/logout/session expiry tested
3. Keyboard navigation and visible focus tested
4. Responsive routes render without horizontal document overflow
5. Production build succeeds

### Exit criterion

Authorised staff can securely enter a complete, role-aware portal shell.


## P06 — Receipt capture, hostile-file validation and private upload

**Goal:** Implement secure receipt acquisition as the first end-to-end user feature.

**Prerequisites:** P02, P03 and P04 complete.

### Required work

1. Implement camera/gallery selection with Expo ImagePicker and runtime permissions.
2. Implement client preview, replace/remove action, accepted-format guidance and quality hints without trusting client validation.
3. Create multipart upload API with authentication, idempotency key and ownership.
4. Allowlist JPEG, PNG and WEBP. Validate extension, magic/decode result, dimensions, animated/multi-frame behaviour, decompression-bomb limits and configured maximum bytes.
5. Apply EXIF orientation only to a derived copy; retain the immutable original.
6. Generate server-side object keys; never use the user's filename as a storage path.
7. Compute SHA-256 and perceptual hash. Record exact duplicate candidates but do not expose other users' data.
8. Create transaction and receipt rows atomically; roll back database/storage consistently on failure.
9. Implement authenticated thumbnail/original retrieval through short-lived signed access or an API stream; enforce ownership/role.
10. Create upload progress, success, invalid-file, too-large, poor-quality, duplicate-warning and retry UI states.
11. Audit upload, rejection and protected file access.

### Deliverables

1. Secure upload API
2. Private storage integration
3. Mobile capture/preview/upload screens
4. Receipt metadata and hashes
5. Upload abuse tests

### Phase verification

1. Valid formats upload and persist
2. Renamed non-image, corrupt file, oversized image and extreme dimensions are rejected
3. Path traversal filename has no effect
4. Cross-user image retrieval is blocked
5. Duplicate hash is detected without leaking owner information
6. Storage/database rollback tested

### Exit criterion

An authenticated user can submit a receipt safely and reopen its private preview.


## P07 — OCR preprocessing, extraction, confidence and correction workflow

**Goal:** Turn uploaded images into reviewable structured transaction fields.

**Prerequisites:** P06 complete; Tesseract available in local/container environment.

### Required work

1. Implement image quality metrics and preprocessing variants: orientation correction, scale normalisation, grayscale/CLAHE, denoise, sharpen, Otsu/adaptive threshold and optional deskew.
2. Run Tesseract `image_to_data` or equivalent to retain token text, bounding boxes and confidence.
3. Score preprocessing variants by OCR confidence and required-field coverage; retain the chosen variant and summary, not only final text.
4. Create provider/template detection with a generic fallback. Store template/parser versions.
5. Implement parsers and normalisers for transaction ID, amount/currency, names, phone numbers, date/time and status text.
6. Store raw OCR text, token data, extracted values, per-field confidence, parser version and warnings.
7. Create API response for OCR review. Mark fields below the configured confidence threshold.
8. Implement mobile OCR Review screen with side-by-side/zoomable receipt, editable fields, confidence/warning indicators and confirmation.
9. Preserve original OCR value and correction audit trail. Do not overwrite raw OCR evidence.
10. Add fixture-based OCR regression tests, including rotated, noisy, low-contrast and cropped receipts.
11. Measure required-field extraction on the controlled evaluation set and report the actual value without inflating it.

### Deliverables

1. Versioned OCR pipeline
2. Field parser and confidence model
3. Mobile OCR review/correction flow
4. OCR fixtures and evaluation report
5. OCR audit evidence

### Phase verification

1. Known fixtures extract expected fields within normalised tolerance
2. Low-confidence fields are flagged
3. Correction creates an audit record and preserves original values
4. Invalid state transition to analysis before OCR review is rejected
5. Tesseract-unavailable path returns explicit partial/failure status

### Exit criterion

A user can review accurate structured fields and correct uncertain values before final analysis.


## P08 — Reference-record import and transaction verification

**Goal:** Implement the prototype's actual verification mechanism without claiming live MNO access.

**Prerequisites:** P07 complete; P05 shell available for import UI.

### Required work

1. Implement reference-import batches with file hash, source label, uploader, row counts, status and audit trail.
2. Define a CSV template and validation: provider, transaction reference, amount, currency, sender/receiver phone/name, timestamp, status and optional source-system ID.
3. Implement preview-before-commit. Invalid rows must be downloadable with reasons; a bad row must not silently corrupt good data.
4. Normalise references, phone numbers, amounts, currency and timestamps consistently with OCR output.
5. Implement exact candidate lookup by provider/reference and safe fallback rules where documented.
6. Compare critical fields using configured amount/timestamp tolerances and normalised exact/fuzzy text comparisons.
7. Return a structured verification result with status, field-level comparisons, matched reference ID, confidence/warnings and rules version.
8. Implement duplicate reference, repeated receipt and transaction-reuse indicators.
9. Create admin import/list/detail UI and user result verification section.
10. Seed safe demonstration reference data and tests.
11. Label all UI and documentation as stored/imported reference verification.

### Deliverables

1. Reference CSV contract
2. Validated import workflow
3. Versioned verification engine
4. Field-level comparison evidence
5. Admin/user verification UI

### Phase verification

1. Matching record returns VERIFIED
2. No record returns UNVERIFIED
3. Critical mismatch returns MISMATCH with exact reasons
4. Duplicate import is idempotent or explicitly rejected
5. Invalid rows and file-level errors are reported
6. Unauthorised import and reference reads are blocked

### Exit criterion

Verification works end to end using authorised stored/imported records and makes no live-MNO claim.


## P09 — Deterministic image-forensics and manipulation evidence

**Goal:** Create explainable visual evidence independent of a trained CNN.

**Prerequisites:** P06 and P07 complete.

### Required work

1. Implement metadata inspection: format, dimensions, EXIF presence, encoder hints and suspicious inconsistencies. Treat absence of metadata as neutral, not fraud.
2. Implement exact/near duplicate checks using SHA-256 and perceptual hash distance.
3. Implement JPEG recompression/error-level analysis on derived images with controlled quality settings and summary statistics.
4. Implement noise/residual inconsistency features across regions, with safeguards for tiny/low-quality images.
5. Implement crop/completeness and aspect/template-layout checks.
6. Use OCR bounding boxes to derive text baseline, spacing, alignment, font-size proxy and overlap features.
7. Create per-signal evidence records with value, threshold, severity, confidence, reason code and version.
8. Optionally create private heatmap/diagnostic derivatives for investigators; never expose them publicly.
9. Create a transparent rule-evaluation layer. No single weak heuristic may set `FRAUDULENT` by itself.
10. Add controlled manipulated fixtures and regression tests.
11. Document limitations of ELA, metadata and template heuristics.

### Deliverables

1. Versioned deterministic image-analysis service
2. Evidence/reason-code catalogue
3. Investigator diagnostic artefacts
4. Manipulated-image test fixtures
5. Limitations documentation

### Phase verification

1. Exact and near duplicates detected
2. Known edits trigger expected evidence without asserting certainty
3. Metadata absence alone does not mark fraud
4. Original image remains byte-identical
5. Private diagnostic derivative access is role/ownership protected

### Exit criterion

Every receipt can produce an explainable, versioned set of image-evidence features even before CNN inference.


## P10 — Dataset governance, controlled sample generation and reproducible splits

**Goal:** Create the data foundation needed for honest model development.

**Prerequisites:** P07 and P09 feature schemas sufficiently stable.

### Required work

1. Create `ml/data/README.md`, dataset card template, consent/licence fields and private-data handling instructions.
2. Implement a manifest-driven dataset loader using the sample columns in `samples/receipt_dataset_manifest.csv`.
3. Create a generic Ghana-style demonstration receipt generator that does not copy protected provider branding unless authorised.
4. Create controlled tampering operations for research fixtures: amount/reference/recipient replacement, crop, clone/paste, misalignment, font mismatch and recompression.
5. Tag every synthetic/controlled sample, parent/source group, manipulation operations and generation seed.
6. Create train/validation/test splits by source/parent group before augmentation. Prevent variants of one receipt appearing in multiple splits.
7. Add data validation for missing files, duplicate hashes, conflicting labels, class distribution, corrupt images and private identifiers.
8. Create anonymisation checks for phone/reference/name fields used in research data.
9. Store manifests and small sanitised fixtures in Git; keep raw private images outside Git.
10. Produce a reproducible dataset report with counts, class distribution, source types, split hashes and known limitations.

### Deliverables

1. Dataset card and governance rules
2. Manifest-driven loader
3. Controlled sample generator
4. Leakage-resistant split files
5. Dataset validation report

### Phase verification

1. No source group crosses splits
2. Augmentation is applied only after split and only to training
3. Dataset loader rejects missing/conflicting records
4. Private-pattern scanner flags unapproved identifiers
5. Regenerating with the same seed reproduces manifest hashes

### Exit criterion

Model training can be reproduced from a documented, leakage-controlled and lawfully usable dataset.


## P11 — Structured-feature fraud classifier

**Goal:** Train and integrate the scikit-learn model for structured evidence.

**Prerequisites:** P08-P10 complete; stable feature schema.

### Required work

1. Define a versioned feature schema covering OCR confidence/coverage, field validity, image heuristics, duplicate indicators, template consistency and verification comparisons.
2. Build an sklearn Pipeline/ColumnTransformer so encoders/imputers/scalers are fit only on training data.
3. Train a RandomForest baseline with class weighting and deterministic seeds. Compare only a small justified set of alternatives if useful; avoid unnecessary model shopping.
4. Use group-aware validation and a held-out test set. Tune on training/validation only.
5. Report confusion matrix, per-class precision/recall/F1, macro F1, balanced accuracy and probability calibration diagnostics.
6. Select and document class thresholds using validation data and project risk priorities.
7. Create a model card with data scope, feature schema, metrics, limitations, intended use and prohibited claims.
8. Persist the model in a trusted artifact format, store SHA-256, library versions, training commit and feature schema hash.
9. Register model metadata in `MODEL_VERSIONS`; never auto-activate a model that failed acceptance gates.
10. Implement deterministic inference service and contract tests.
11. Add a CLI to train, evaluate, register and activate models with explicit confirmation.

### Deliverables

1. Reproducible training pipeline
2. Structured model artifact and card
3. Evaluation report
4. Version registry integration
5. Inference service

### Phase verification

1. Training repeatability within documented tolerance
2. Pipeline rejects schema drift/missing mandatory features
3. Held-out set is never used during fit/tuning
4. Artifact hash verified before load
5. Inference output probabilities are valid and version traceable

### Exit criterion

A registered structured classifier produces reproducible, honest and versioned predictions.


## P12 — CNN receipt-tampering classifier

**Goal:** Train and integrate the TensorFlow/Keras image model.

**Prerequisites:** P10 complete; sufficient authorised/controlled image data.

### Required work

1. Define input resolution, colour handling, normalisation and augmentation policy.
2. Implement a transfer-learning baseline such as MobileNetV3Small with a small classification head; document any architecture change.
3. Freeze/unfreeze in controlled stages and use early stopping/model checkpoints based on validation metrics.
4. Use group-separated splits and training-only augmentation.
5. Address class imbalance through justified class weights or sampling; do not duplicate test data.
6. Report per-class metrics, macro F1, confusion matrix, ROC/PR information where meaningful and calibration.
7. Create a model card and explicit synthetic-only limitation where applicable.
8. Export a `.keras` artifact, compute hash and register preprocessing/model metadata.
9. Implement inference with deterministic preprocessing and safe fallback when the artifact is absent or incompatible.
10. Create optional investigator heatmap/attention diagnostic only as a supporting visual, not proof of manipulation.
11. Add performance measurement for CPU inference in the deployment container.

### Deliverables

1. Reproducible CNN training/evaluation pipeline
2. Versioned image-model artifact and card
3. CNN inference service
4. CPU performance report
5. Safe unavailable-model behaviour

### Phase verification

1. Training/test group separation asserted
2. Preprocessing parity between training and inference
3. Artifact hash/version check
4. Corrupt/unsupported image returns controlled error
5. Inference latency recorded on target container
6. Absent model produces PARTIAL, not fabricated probability

### Exit criterion

The image model is versioned, reproducible and safely integrated or explicitly marked unavailable.


## P13 — End-to-end analysis orchestration, rules and risk aggregation

**Goal:** Combine all evidence into one auditable analysis result.

**Prerequisites:** P07-P09 complete; P11/P12 available or explicit unavailable adapters.

### Required work

1. Implement `AnalysisOrchestrator` with validated state transitions and idempotent analysis requests.
2. Snapshot corrected OCR fields, parser/template versions, feature schema, rule set, model versions and thresholds at analysis start.
3. Run verification, deterministic image analysis, CNN inference and structured-model inference through typed service interfaces.
4. Persist subsystem start/end/error status and timings. A subsystem failure must not destroy successful evidence.
5. Implement the preliminary configurable score `R = 100 * (0.40*p_img + 0.40*p_ml + 0.20*p_rule)` while preserving the raw components.
6. Calibrate and store thresholds; initial defaults may be `GENUINE < 35`, `SUSPICIOUS 35–69.99`, `FRAUDULENT >= 70` only until validated.
7. Define rule probability/severity mapping and ensure no circular feature leakage from the final label.
8. Create top reason-code selection and plain-language explanations.
9. Display verification separately, but allow a critical mismatch/reuse rule to contribute explicitly to fraud risk.
10. Return `PARTIAL` when required components are unavailable. Use conservative messaging for insufficient evidence.
11. Add full analysis API and mobile progress/result screens.
12. Create golden end-to-end fixtures for low-risk, suspicious, fraudulent, verified, unverified, mismatch and partial outcomes.

### Deliverables

1. Analysis orchestrator
2. Versioned risk aggregation
3. Persisted analysis-run evidence
4. Mobile progress/result/evidence views
5. End-to-end golden tests

### Phase verification

1. Idempotent retry does not duplicate a completed result
2. All component versions and timings are persisted
3. Risk and verification fields remain separate
4. Threshold boundaries tested
5. Subsystem failure produces PARTIAL with retained evidence
6. Reason codes match underlying evidence
7. Ownership and role access enforced

### Exit criterion

One user upload can complete the full persisted OCR-to-result journey with explainable outputs.


## P14 — History, search, downloadable reports and notifications

**Goal:** Complete the everyday user workflow after analysis.

**Prerequisites:** P13 complete.

### Required work

1. Implement paginated user transaction history with date, provider, risk, verification and status filters.
2. Implement transaction detail that reconstructs result from persisted evidence rather than rerunning models.
3. Create a server-generated analysis summary PDF or equivalent downloadable report containing masked identifying data, result, reasons, verification comparisons, model/rule versions and disclaimer.
4. Authorise every report download; use a short-lived generated file or streamed response.
5. Implement in-app notification records for analysis completion, high-risk results and case-status changes.
6. Implement notification list, unread count, mark-read and deep link to the relevant transaction/case.
7. Add optional notification-delivery adapter interface; keep external push/email disabled when credentials are absent.
8. Create mobile History, Transaction Detail, Report, Notifications and notification-settings screens.
9. Add retention and regeneration rules for downloadable reports.
10. Audit report generation/download and notification-delivery state changes.

### Deliverables

1. History/search API and UI
2. Persisted detail reconstruction
3. Downloadable analysis summary
4. In-app notifications
5. Audit coverage

### Phase verification

1. Pagination/filter combinations correct
2. Users cannot download another user's report
3. Historical detail remains stable after model activation changes
4. PDF/report masks configured fields
5. Notification read/unread and deep links work
6. External adapter failure does not lose in-app notification

### Exit criterion

Users can find, understand and export their previous analyses and receive lifecycle notifications.


## P15 — Fraud reporting, investigation and governance administration

**Goal:** Complete human review and controlled system configuration.

**Prerequisites:** P13 and P05 complete.

### Required work

1. Implement user suspicious-transaction report creation with category, description and linked transaction.
2. Automatically create or queue cases for configured high-risk outcomes without duplicating a user report.
3. Implement case assignment, status transitions, notes and reasoned confirm/dismiss/escalate decisions.
4. Keep human decision fields separate from automated risk and verification records.
5. Implement investigator Case Queue and Case Detail with private original/derived evidence, OCR comparison, model/rule evidence, verification comparison and timeline.
6. Implement administrator user/role management with last-admin safeguards and audited role changes.
7. Implement receipt-template registry, rule registry and thresholds with draft/active/retired version states.
8. Implement model registry views and controlled activation/rollback; activation requires artefact hash and readiness checks.
9. Implement reference-import administration from P08.
10. Implement case report generation and audit timeline.
11. Apply field masking according to role and purpose.

### Deliverables

1. User report workflow
2. Investigator case queue/detail/decision
3. Admin registries and user management
4. Model/rule activation controls
5. Case reports and timelines

### Phase verification

1. Decision requires reason and valid state
2. Automated result remains unchanged after decision
3. Duplicate case creation prevented
4. Investigator cannot access admin-only configuration
5. Last active administrator cannot be accidentally removed
6. Model/rule rollback produces audited version change

### Exit criterion

Flagged evidence can be reviewed and governed without compromising original automated evidence.


## P16 — Operational dashboard, analytics, audit and system status

**Goal:** Provide useful monitoring without leaking sensitive data or recomputing history.

**Prerequisites:** P13-P15 complete.

### Required work

1. Implement dashboard aggregates: total analyses, processing states, risk-class counts, verification counts, cases by status, average latency and model availability.
2. Implement date/provider filters and safe trend charts.
3. Implement transaction search/list for authorised staff with masked values and role-limited detail.
4. Implement audit-log search by actor, action, target, date and request ID; full sensitive payloads must not be logged.
5. Implement system-status page for database, storage, Tesseract, active models and optional notification adapters.
6. Implement operational reports/export with row limits, authorisation and audit.
7. Use database indexes/aggregations appropriate for 100,000 analysis records; avoid loading all rows into application memory.
8. Add empty, loading, partial-data and unavailable-component states.
9. Add chart/table accessibility and downloadable tabular alternatives.
10. Add analytics correctness and permission tests.

### Deliverables

1. Admin dashboard
2. Operational search and exports
3. Audit-log UI
4. System status UI
5. Analytics tests

### Phase verification

1. Aggregate values match seeded ground truth
2. Date/provider filters correct
3. Export limits and role permissions enforced
4. Dashboard avoids unbounded queries
5. Sensitive values masked in logs/UI
6. Status correctly reports unavailable dependencies

### Exit criterion

Administrators can monitor the platform and investigate operational evidence safely.


## P17 — UI completion, accessibility, responsive and visual QA

**Goal:** Turn all implemented flows into a coherent, polished and defensible interface.

**Prerequisites:** P04-P16 feature-complete.

### Required work

1. Perform a screen inventory against `06_UI_UX_IMPLEMENTATION_SPEC.md`; implement every missing loading, empty, error, retry, offline, permission and destructive-confirmation state.
2. Apply final brand tokens while keeping semantic status accessible through text and icons.
3. Ensure risk and verification presentation is consistent on cards, detail pages, PDFs and dashboards.
4. Improve receipt image zoom/pan, OCR field-to-image highlighting and evidence explanations.
5. Review mobile keyboard, small-screen, safe-area, orientation and dynamic-text behaviour.
6. Review admin at required desktop/tablet widths; eliminate layout overflow and inaccessible table interactions.
7. Add accessibility labels, landmarks, form descriptions, focus management, contrast checks and reduced-motion support.
8. Run visual regression or screenshot comparison for critical screens.
9. Capture final UI screenshots separately from Chapter Three wireframes.
10. Conduct a user-journey review with non-technical copy and remove debug/internal terminology.

### Deliverables

1. Complete final UI
2. Accessibility review
3. Responsive/viewport evidence
4. Visual regression baseline
5. Final screenshots

### Phase verification

1. Critical journeys complete by keyboard/screen-reader-friendly controls
2. No colour-only status
3. No viewport overflow at agreed sizes
4. All forms announce errors
5. Screenshot/visual checks reviewed
6. Mobile primary analysis starts within the specified principal-action target

### Exit criterion

The mobile and web interfaces are complete, consistent, accessible and ready for evaluation.


## P18 — Full hardening, security, performance and regression QA

**Goal:** Prove the system under adverse and end-to-end conditions.

**Prerequisites:** Feature complete through P17.

### Required work

1. Run the complete test matrix in `09_TESTING_QA_RELEASE_PLAN.md` on a clean clone and clean database.
2. Add missing backend unit/integration tests to meet coverage targets, prioritising auth, ownership, upload, verification, risk and case decisions.
3. Complete mobile and admin unit/component tests and critical Playwright/Detox-or-equivalent flows.
4. Run upload abuse, IDOR, role bypass, token, rate-limit, injection, export and private-file tests.
5. Run dependency vulnerability audit, secret scan and static analysis; triage findings rather than hiding them.
6. Run performance tests for login/history/upload/analysis and dashboard queries. Record hardware/environment and actual results.
7. Run 25-concurrent-analysis prototype test or document the measured limit and bottleneck honestly.
8. Verify backup/restore, migration rollback plan and storage/database consistency recovery.
9. Test model artifact corruption, missing Tesseract, database interruption, storage failure and partial-analysis recovery.
10. Review logs for PII/secrets and validate audit completeness.
11. Create `docs/qa/P18_TEST_REPORT.md` with commands, versions, pass counts, failures and accepted risks.

### Deliverables

1. Complete regression suite
2. Security test report
3. Performance report
4. Backup/recovery evidence
5. Defect list and resolutions

### Phase verification

1. Root verification command passes
2. Critical security test suite passes
3. No unresolved critical/high defect
4. Coverage reports meet targets or exception is documented
5. Performance results are measured and reproducible
6. Clean clone verification succeeds

### Exit criterion

The codebase has objective evidence of correctness, security and operational resilience.


## P19 — Staging deployment, release engineering and rollback

**Goal:** Deploy a reproducible release without exposing secrets or private receipts.

**Prerequisites:** P18 gates pass.

### Required work

1. Create production Docker image with pinned dependencies, non-root runtime, Tesseract language data and health checks.
2. Create staging configuration for API, managed PostgreSQL and private S3-compatible storage. Use environment secrets, never committed credentials.
3. Deploy the administrator portal with correct API origin and security headers.
4. Create Expo EAS configuration and an internal Android build; iOS build is conditional on account access.
5. Run database migrations as an explicit release step; do not rely on multiple web workers racing migrations.
6. Create bootstrap-admin process, CORS/CSRF/cookie domain configuration and signed/private storage verification.
7. Configure HTTPS, request/body limits, log retention and backup schedule.
8. Run staging smoke/E2E tests with safe test data.
9. Create release tag, release notes, deployment manifest and exact image/build identifiers.
10. Test rollback of application version and document database rollback limitations.
11. Do not claim deployment when external account access is unavailable; provide ready-to-run manifests and exact blocker.

### Deliverables

1. Staging API/admin/mobile build or deploy-ready manifests
2. Release and rollback runbook
3. Environment/secrets checklist
4. Staging smoke evidence
5. Tagged release candidate

### Phase verification

1. Health/readiness from staging
2. End-to-end safe receipt flow on staging
3. Private image URL not public
4. Migration revision matches application
5. Rollback rehearsal documented
6. No secret exposed in frontend/mobile bundles or repository

### Exit criterion

A reproducible release candidate is deployed or is blocked only by an explicitly identified external credential.


## P20 — Final documentation, evidence, cleanup and inspection handoff

**Goal:** Freeze a reviewable final state and make independent inspection efficient.

**Prerequisites:** P19 complete or approved deployment blocker recorded.

### Required work

1. Resolve remaining TODO/FIXME markers or convert them into documented non-critical issues.
2. Update architecture, implemented ERD, API, state-machine and sequence documentation to match code.
3. Complete requirements traceability with exact code paths and test names.
4. Complete model cards, dataset cards, security report, test report, deployment report and limitations.
5. Capture final Chapter Four evidence listed in `13_DOCUMENTATION_AND_CHAPTER4_EVIDENCE.md`.
6. Verify academic diagrams can be regenerated cleanly with no crossing lines and reflect actual relationships/multiplicities.
7. Run clean-clone bootstrap and full verification one final time.
8. Ensure worktree is clean, branch is pushed and CI is green at the exact final SHA.
9. Complete `templates/FINAL_HANDOFF.md` with branch, base/head SHA, tree status, tests, deployment, accounts, artifacts, known limitations and reproduction commands.
10. Open or update the final pull request; do not merge unless instructed.
11. Provide a concise repair prompt template for any later audit findings.

### Deliverables

1. Final handoff
2. Complete traceability
3. Updated diagrams/docs
4. Final verification evidence
5. Exact pushed review SHA

### Phase verification

1. Clean clone setup passes
2. Full verification and CI pass at final SHA
3. All MUST requirements are implemented or approved exceptions
4. Final handoff links resolve
5. Git status clean and remote contains exact SHA

### Exit criterion

An independent reviewer can inspect, run and assess the system without relying on undocumented context.


## 8. Milestone review points

To preserve review time and tokens, use three optional milestone audits plus the final audit:

- **Milestone A:** after P07 — foundation, security, upload and OCR.
- **Milestone B:** after P13 — complete analytical pipeline.
- **Milestone C:** after P17 — complete user/admin product.
- **Final:** after P20 — repository, CI, deployment and documentation inspection.

For each audit, provide the repository, branch/pull request and exact SHA. Do not ask the reviewer to infer which commit should be checked.

## 9. Project-owner decisions that must not be guessed

Codex should continue with safe defaults where allowed, but it must record these unresolved owner decisions:

- final brand name, logo and colour identity;
- whether end-user self-registration remains open in production;
- authorised provider receipt templates;
- approved real dataset and consent/licence status;
- production reference-record source;
- deployment provider/accounts;
- data-retention period;
- notification provider;
- whether administrators may also act as investigators;
- final risk thresholds after evaluation;
- final password/session policy if the institution sets one.

## 10. Feature prioritisation under deadline pressure

The minimum academically defensible vertical slice, in order, is:

1. secure authentication and private upload;
2. OCR extraction and correction;
3. deterministic image evidence;
4. stored/imported reference verification;
5. one reproducible structured fraud model;
6. risk aggregation with explanations;
7. history and investigator review;
8. automated tests and deployment.

The CNN is important to the declared scope but must not delay delivery of an honest baseline. When an adequate image dataset is unavailable, Codex must complete the training pipeline, controlled dataset tooling and unavailable-model state, then document the limitation rather than inventing performance.

## 11. Final acceptance decision

The final audit classifies findings as:

- **BLOCKER:** cannot run, data/security loss, false core claim or missing primary journey.
- **CRITICAL:** exploitable access/control failure, public private data, invalid model/data methodology or destructive migration.
- **HIGH:** major requirement missing, incorrect result, broken admin/investigator workflow or unreproducible evaluation.
- **MEDIUM:** incomplete edge case, weak UX/accessibility, insufficient test or documentation gap.
- **LOW:** maintainability, wording, minor visual or non-critical optimisation.

Release requires zero open blocker/critical findings and an explicit decision on every high finding.
