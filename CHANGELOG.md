# CHANGELOG.md

All notable project changes are recorded here. Use semantic sections and link each entry to the phase/PR/commit when available.

## Unreleased

### Added

- Initial implementation package, scope, requirements, architecture, database, API, UI, analytical, security, test, GitHub, deployment and inspection specifications.
- P00 repository policy files, root project/security documentation and version pins.
- P00 gap analysis and a local milestone index derived from the 222-task backlog.
- Cross-platform bootstrap, toolchain doctor, prohibited-artifact/secret scan and honest verification orchestration scripts.
- Published the initial P00 foundation to `davidagyekum/momo-fraud-detection` on `main` and `codex/p00-preflight-foundation`.
- P01 monorepo boundaries for mobile, admin, shared contract, API, ML, infrastructure and documentation.
- Flask application factory with environment validation, versioned system endpoints, request IDs and standard JSON errors.
- Schema-generated OpenAPI snapshot and deterministic contract drift check.
- SQLAlchemy/Flask-Migrate lifecycle, PostgreSQL readiness probe and empty Alembic baseline.
- Structured JSON logging with sensitive-field redaction and strict explicit-origin CORS.
- PostgreSQL/API Docker Compose services, named volumes, health checks and a non-root Tesseract API image definition.
- Pinned runtime/development dependency locks and backend Ruff, mypy, pytest and coverage gates.
- Windows, macOS/Linux and Docker local-development documentation.
- P01 GitHub Actions checks for repository policy, backend quality/tests, clean PostgreSQL migrations, OpenAPI drift and a full Docker Compose smoke test.
- Verified the P01 non-root API image, PostgreSQL service, named private-storage/database volumes, clean Alembic upgrade and live system endpoints in Docker Desktop.
- P02 complete 30-table SQLAlchemy evidence model with deterministic constraints, indexes, relationships and engineering ER generation.
- Alembic revision `20260809_0002` with CITEXT support, circular analysis linkage and database-enforced immutable evidence tables.
- Configured local-private and S3-compatible storage adapters with generated keys, SHA-256 metadata, encryption settings and retention-guarded deletion.
- Idempotent controlled-development seeds, cross-domain database factories and PostgreSQL schema-integrity tests.
- P02 backup/retention/consistency runbook and CI migration rollback/schema gates.
- P03 Argon2id password handling, signed short-lived access tokens and atomic rotated refresh-token families with hashed persistence and reuse detection.
- Registration, login, refresh, logout, generic password-reset, current-profile and change-password API endpoints.
- Central USER/ADMIN/INVESTIGATOR policies, transaction ownership hiding and ADMIN-only user/role/session management with optimistic concurrency, self-lockout and last-admin safeguards.
- Cryptographically bound double-submit CSRF protection for HTTP-only browser refresh cookies and a documented Expo SecureStore mobile token contract.
- Append-only authentication/privileged audit events, configurable endpoint rate limits and generated P03 OpenAPI contract coverage.
- P04 Expo SDK 57 mobile application with session restoration, login, registration, password reset, profile update and confirmed logout flows.
- P04 semantic design tokens, reusable accessible UI states, native five-tab navigation and a responsive web fallback.
- Memory-only mobile access tokens, rotating refresh-token SecureStore isolation, coordinated refresh and explicit partial-session handling.
- TanStack Query server state, network awareness, global error recovery and honest inactive states for features owned by later phases.
- Mobile formatting, linting, strict typing, Jest coverage, token-storage policy, static export and GitHub Actions verification gates.
- Safe Chapter Four mobile screenshots and an evidence manifest linked to the P04 implementation SHA.
- P05 React 19/TypeScript/Vite administrator and investigator portal with secure staff sign-in, session restoration, logout confirmation and role-aware routing.
- P05 evergreen/gold responsive shell, desktop sidebar, tablet drawer and reusable form, feedback, overlay, table/list, filter, pagination, chart-frame and secure-download components.
- Honest dashboard shell that presents fraud risk, transaction verification, case status and processing state as four independent concepts without inventing later-phase aggregates.
- No-access, not-found, global-error, session-expired, loading, empty, filtered-empty, degraded and retry-ready portal states.
- Portal security/quality verification covering browser token persistence, unsafe HTML injection, formatting, linting, strict typing, 34 Vitest tests, coverage thresholds, 3 Playwright smoke flows and the production bundle.
- P05 GitHub Actions admin-quality job and safe desktop/tablet/narrow Chapter Four screenshot evidence linked to functional implementation SHA `63c62a1`.
- P06 Expo camera/gallery receipt selection with runtime permissions, preview replacement/removal, upload/retry feedback, quality and duplicate notices, and authenticated private-preview reopening.
- P06 multipart transaction creation with required idempotency, strict JPEG/PNG/WebP validation, immutable originals, EXIF-normalised thumbnails, SHA-256/dHash evidence, atomic rollback and private owner/staff streaming.
- P06 hostile-upload and privacy regressions for corrupt/disguised/polyglot/oversized/multi-frame inputs, path traversal, replay/conflict, duplicate privacy, cross-owner denial and cleanup.
- P07 versioned OpenCV preprocessing and bounded Tesseract recognition with raw text, token boxes/confidence, candidate summaries, quality evidence and immutable private derivatives.
- P07 provider-aware field parsing and canonical Ghanaian phone, currency, reference and UTC date/time normalization with explicit generic-template and degraded-engine behavior.
- P07 owner-only OCR run/review/confirmation APIs with idempotent replay, correction reasons, immutable confirmation evidence, audit events and analysis-readiness enforcement.
- P07 Expo OCR review experience with a private zoomable receipt, editable fields, understandable confidence guidance and complete loading/offline/error/partial/confirmation states.
- Deterministic controlled OCR evaluation covering clean, rotated, low-contrast, noisy and cropped receipts; all 20 declared required-field checks passed without claiming production generalisation.
- P08 private reference CSV upload with generated storage keys, SHA-256 evidence, strict UTF-8/header/row validation, formula-safe invalid-row reports and explicit preview-before-commit confirmation.
- P08 deterministic stored-reference verifier with ambiguity-safe candidate lookup, configured field comparisons, masked evidence, immutable version snapshots and duplicate/reuse warning codes.
- P08 immutable `PARTIAL` analysis results that preserve transaction verification while explicitly leaving fraud risk unavailable and null until later model phases.
- P08 administrator reference-import workspace with private upload, validation preview, confirmed commit, masked list/detail views and permission-denied/error/empty states.
- P08 mobile result presentation with separate transaction-verification and fraud-risk cards and explicit stored/imported-record—not live MNO—wording.
- Controlled reference CSV template and import contract documentation containing demonstration data only.
- P09 versioned deterministic image-forensics service covering safe metadata, exact/near duplicates, controlled recompression/ELA, regional noise residuals, OCR box alignment, crop proximity, aspect ratio and quality context.
- P09 per-signal immutable evidence with observed values, thresholds, severity, confidence, reason codes, limitations, extractor/feature versions and explicit not-applicable states.
- P09 private ELA and noise-map derivatives with generated keys, staff-only protected streaming and audited success/denial.
- Owner/staff immutable analysis-evidence API that keeps verification, image evidence and unavailable fraud risk as separate projections and never exposes another user's identity or a storage key.
- Mobile image-evidence card that explains deterministic signals as supporting evidence only and continues to show fraud risk as unavailable.
- Controlled seeded manipulation, tiny-image, metadata, alignment, persistence, integrity, immutability and diagnostic-access regressions plus a P09 evidence catalogue.

### Changed

- Repository verification now executes the implemented P01 backend suite for `--backend`.
- P00 PR #1 was merged to `main` at `41741877cce2a2efd69240c77707c55a7961bd0f`.
- Model-training execution is reserved for Google Colab; local phases prepare reproducible code, manifests and notebooks, then pause before the first training run for project-owner handoff.
- Repository backend verification now checks the generated engineering ER reference.
- Controlled development seed accounts now use the same Argon2id password policy as runtime accounts.
- JavaScript work now uses Node.js 24.14.0 because Expo SDK 57 / React Native 0.86 does not support the workstation's older Node.js 22.11.0 runtime.
- The browser-readable CSRF cookie uses the application root path while the HTTP-only refresh cookie remains restricted to `/api/v1/auth`, enabling the staff SPA to echo the cryptographically bound CSRF value after reload.
- Repository verification now executes the complete P05 administrator portal suite for `--admin`.
- The generated OpenAPI contract now documents receipt multipart fields, `Idempotency-Key`, private media variants and upload error states.
- The generated OpenAPI contract now documents the P07 OCR run, review, immutable confirmation and analysis-readiness lifecycle.
- The generated OpenAPI contract now documents P08 reference-import, masked reference-record and verification-analysis endpoints and error states.
- The generated OpenAPI contract now documents P09 immutable analysis evidence and staff-only `ela`/`noise-map` receipt variants.
- The transitional partial-analysis response now includes deterministic image evidence when available and removes `IMAGE_ANALYSIS` from the unavailable-stage list without simulating model/risk completion.

### Fixed

- None.

### Security

- Initial secure-development requirements established.
- Added repository ignore policy and a scanner that rejects environment files, common credential patterns, private-data directories and model artifacts.
- Added correlation headers, generic public 500 responses, credential redaction, CORS allowlisting and dependency responses that omit infrastructure details.
- Added database append-only triggers for audit and evidential rows, private storage path-containment checks and safe bootstrap password rotation flags.
- Added fail-closed production auth secrets, secure cookie/SameSite validation, access-token role/version checks, reset/session revocation and cross-user object-hiding tests.
- Added a mobile token-storage policy that rejects unencrypted persistence and isolates SecureStore access to refresh tokens only.
- Extended secret-scanner syntax handling and added regression tests for TypeScript declarations versus hard-coded tokens.
- Kept reference originals and invalid-row reports in private storage, enforced ADMIN/INVESTIGATOR permissions, masked sensitive values and audited evidential reads and privileged import actions.
- Kept forensic diagnostics outside public/static paths, enforced staff roles server-side, returned owner-safe evidence without diagnostic URLs and verified the immutable original remains byte-identical.
- Added an administrator browser-security policy that rejects local/session/IndexedDB token persistence and `dangerouslySetInnerHTML`; access tokens remain memory-only and refresh credentials remain HTTP-only.
- Verified the P05 production dependency graph with `npm audit --omit=dev`: zero known vulnerabilities at the recorded run.
- P06 originals remain byte-identical private evidence; only derived thumbnails receive EXIF orientation and metadata stripping. Protected streams enforce owner/staff policy, generated filenames, `nosniff` and private no-store caching.
- P07 verifies the original receipt hash before deriving OCR candidates; automated OCR rows remain immutable while owner corrections are stored separately with old/new values and reasons.

### Known limitations

- GitHub-hosted P01 workflow jobs cannot start while the repository owner's GitHub Actions account is locked by a billing issue; equivalent P01 gates pass locally.
- Real model training remains pending and no metric or model artifact is claimed; execution will occur in Google Colab after the P10 data-governance phase.
- `npm audit --omit=dev` reports 8 moderate and 15 high findings in the current Expo SDK 57/React Native/Metro dependency graph. Its proposed automatic fixes downgrade Expo to 53 or React Native to 0.72, so no incompatible force-fix was applied; monitor supported SDK 57 patches under B-SEC-002.

## Release entry template

## [version] — YYYY-MM-DD

### Added
### Changed
### Fixed
### Security
### Known limitations

**Repository SHA:**  
**Migration revision:**  
**Active model/rule/template versions:**  
**Deployment/build IDs:**
