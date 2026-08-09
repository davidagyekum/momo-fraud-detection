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

### Changed

- Repository verification now executes the implemented P01 backend suite for `--backend`.
- P00 PR #1 was merged to `main` at `41741877cce2a2efd69240c77707c55a7961bd0f`.
- Model-training execution is reserved for Google Colab; local phases prepare reproducible code, manifests and notebooks, then pause before the first training run for project-owner handoff.
- Repository backend verification now checks the generated engineering ER reference.

### Fixed

- None.

### Security

- Initial secure-development requirements established.
- Added repository ignore policy and a scanner that rejects environment files, common credential patterns, private-data directories and model artifacts.
- Added correlation headers, generic public 500 responses, credential redaction, CORS allowlisting and dependency responses that omit infrastructure details.
- Added database append-only triggers for audit and evidential rows, private storage path-containment checks and safe bootstrap password rotation flags.

### Known limitations

- GitHub-hosted P01 workflow jobs cannot start while the repository owner's GitHub Actions account is locked by a billing issue; equivalent P01 gates pass locally.
- Real model training remains pending and no metric or model artifact is claimed; execution will occur in Google Colab after the P10 data-governance phase.

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
