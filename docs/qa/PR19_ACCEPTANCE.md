# PR19 Acceptance Evidence

Date: 2026-08-16. Base: `5fe83763ebae19459bd49c8ddc5e0e35b67c2c03`. Branch: `codex/pr19-release-hardening`.

## Measured gates

| Area | Result |
|---|---|
| Backend | 180 tests passed; 85.17% branch-aware coverage; Ruff, strict mypy, OpenAPI and ER drift passed |
| Administrator portal | 40 tests passed; 92.94% statements, 83.22% branches, 97.26% functions, 95.51% lines; 3 Playwright flows and production build passed |
| Mobile | 65 tests passed; 83.80% statements, 69.07% branches, 85.71% functions, 86.66% lines; 28-route web export and production same-origin API routing passed |
| ML | 714 tests passed; 90.15% branch-aware coverage; formatting, Ruff, strict mypy and governance gates passed |
| Security | 31 backend security scenarios passed with zero skips; web/mobile policy gates and secret scan passed |
| End-to-end | Controlled screenshot upload, OCR confirmation, analysis, private report, fraud report, assignment, review, note, decision, owner case/notification and staff views passed |
| Local release | PostgreSQL, API, administrator and mobile containers healthy; migration `20260816_0005 (head)`; required role reference data, health/readiness, registration and both login pages passed |

The local release project used isolated ports `55435/8002/5176/8083`. Database, storage, and container Tesseract 5.3.0 were ready. Image and structured classifiers remained honestly not activated; complete-model analysis was unavailable. No hosted deployment, provider verification, final model evaluation, or production-readiness claim is made.

## Known acceptance boundaries

- Host Node.js/npm are `24.19.0`/`10.9.8` through the bundled runtime rather than the pinned `24.14.0`/`10.9.0`; the administrator Docker build used the exact pinned versions.
- Host Tesseract is absent; the release container has verified Tesseract 5.3.0.
- Mobile transitive advisory B-SEC-002 remains open because npm proposes only breaking forced downgrades.
- Hosted CI remains an external evidence boundary until a fresh GitHub run starts and completes.
- Native Android/device and multi-browser acceptance, non-local HTTPS, backup restoration, and performance/load targets remain outstanding product gates.
