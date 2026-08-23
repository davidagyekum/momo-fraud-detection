# Codex Session Handoff

## Session identity

- Date/time: 2026-08-23, Africa/Lagos
- Phase/sub-phase: final PR #18 hybrid accuracy and presentation pass
- Repository: MoMo-FDVS
- Base branch: `main`
- Base SHA: `eab389e2a8dff5d1a29dcce289bd036994757cd7`
- Work branch: `codex/final-mtn-format-hybrid-accuracy`
- Final implementation SHA: `4f9a30ad588e3edb9c053e210e799e20ad6d4357`
- Pull request: #18
- Push status: pending final documentation commit and remote-equality check
- Worktree status: expected documentation, generated OpenAPI and formatter changes before final commit

## Scope completed

- Requirement IDs: `FR-HYBRID-005` through `FR-HYBRID-008`, `FR-P1-UI-005`, `NFR-BUILD-001`, `NFR-HYBRID-PRIV-001`
- Backlog task IDs: final PR #18 correctness, UI and verification override
- Goal: preserve the current hybrid implementation while completing its final test-first correctness and presentation pass.
- Actual completed work: reason-aware safe risk copy across all public surfaces; provider-specific MTN-profile isolation; independent OCR region-group voting; honest raw-fallback provenance; shared risk tones; simplified owner flow and terminology; progressive technical evidence; combined quality warnings; safe build metadata; narrower OCR banner; public-object/log privacy regression.

## Changed files

The exact changed-file list is represented by `git diff --name-status eab389e2a8dff5d1a29dcce289bd036994757cd7..HEAD`. Principal modules are:

| Path | Change | Why |
|---|---|---|
| `services/api/src/momo_fdvs/services/risk_presentation.py` | Added centralized reason-aware safe copy | Keep preview, persistence, reports, notifications and administrator projections consistent. |
| `services/api/src/momo_fdvs/services/hybrid_text_risk.py` | Gated the MTN profile by explicit provider | Prevent MTN-format evidence from contaminating Telecel/AirtelTigo results. |
| `services/api/src/momo_fdvs/services/ocr_evidence_consensus.py` | Counted one vote per reason and independent region group | Stop crop variants/PSM modes from acting as independent evidence. |
| `services/api/src/momo_fdvs/services/ocr.py` | Preserved raw fallback provenance/confidence | Avoid false header evidence and confidence promotion. |
| `apps/mobile/src/lib/risk-tone.ts` | Added shared semantic tone | Apply one accessible risk mapping across owner surfaces. |
| `apps/mobile/src/components/analysis-result.tsx` | Simplified check result and disclosure | Keep decisions clear while preserving compact evidence and technical access. |
| `apps/mobile/src/app/(app)/profile.tsx` | Added About this build | Expose safe reproducibility identifiers without secrets/paths. |
| `apps/admin/src/lib/risk-presentation.ts` | Shared administrator risk presentation | Match owner/report semantics. |
| `packages/api-client/openapi.json` | Regenerated contract snapshot | Record version metadata fields without a breaking endpoint. |

## Database/migrations

- Migration revision(s): none added; head remains `20260817_0006`.
- Upgrade tested from: empty database and representative previous revision `20260816_0005`.
- Downgrade/rollback notes: no schema rollback is needed for this pass.
- Data backfill: none.
- Schema/ERD update: no schema change; ER drift passed.

## API/contract

- Endpoints added/changed: existing `GET /api/v1/version` now returns OCR pipeline, fraud ruleset and risk-policy identifiers; public risk projections use centralized safe reason-aware presentation.
- OpenAPI/client regenerated: yes.
- Breaking change: no; fields are additive and the strict client was updated.
- Error/permission behaviour: unchanged; server ownership/RBAC remains authoritative.

## UI

- Screens/components: OCR preview, analysis, history, transaction detail, notifications, reports, Profile and administrator projections.
- States covered: low, medium, high, inconclusive, loading, error, degraded component availability and screenshot-only verification not attempted.
- Viewports/devices: controlled Expo-web checks at 360, 390, 768 and 1440 pixels; cache-cold LAN context.
- Screenshot/evidence paths: controlled generated artifacts were placed under ignored `output/playwright/final-pr18/`; aggregate safe evidence is `docs/evidence/FINAL_HYBRID_ACCURACY_PRESENTATION.md`.
- Accessibility notes: labels remain alongside tone; the detailed disclosure has an accessible expanded state; compact evidence remains visible.

## OCR/image/ML/verification

- Pipeline/model/rule/template versions: `ocr-pipeline-v1`, `ghana-momo-hybrid-text-risk-v3`, `analysis-risk-policy-demo-v4`, hash-verified `mtn-genuine-format-profile-v1`.
- Dataset/split/artifact hashes: no dataset or model artifact changed; profile checksum validation remains active.
- Metrics actually measured: seven controlled real-Tesseract boundary cases passed in 77.42 seconds; full gate counts appear below.
- Limitations: controlled fixtures are not provider-wide accuracy or performance evidence; image model remains unavailable; training was disabled.
- No fabricated or unavailable evidence: degraded model availability remains explicit and screenshot-only verification remains `NOT_ATTEMPTED`.

## Security/privacy

- Access-control impact: none; existing ownership and RBAC are preserved.
- Private-data impact: public projections/logs are regression-tested to exclude raw OCR, phone, amount, reference, URL and matched phrase.
- Upload/storage impact: none; private storage remains unchanged.
- Audit events: existing immutable analysis/audit behavior is preserved.
- Security checks: 31 PostgreSQL scenarios passed with zero skips plus web/mobile policy and 722-file secret/prohibited-artifact scan.

## Verification performed

| Command | Result | Counts/summary | Duration |
|---|---|---|---|
| `python scripts/verify_backend.py` | PASS | 292 passed; 7 expected host Tesseract skips; 85.72% coverage; Ruff, mypy, OpenAPI, ER | recorded by verifier |
| Real-Tesseract Docker selection | PASS | 7 passed | 77.42 s |
| `python scripts/verify_mobile.py` | PASS | 22 suites / 118 tests; 83.78% statements; export and policy gates | recorded by verifier |
| `python scripts/verify_admin.py` | PASS | 47 tests; 3 Playwright; production build | recorded by verifier |
| `python scripts/verify_ml.py` | PASS | 714 tests; 90.15%; training disabled | recorded by verifier |
| `python scripts/verify_security.py` | PASS | 31 passed; zero skips; 722-file scan | recorded by verifier |
| `python scripts/verify_e2e.py` | PASS | API journey; 8 mobile; export; 3 administrator Playwright | recorded by verifier |
| Empty and previous migration upgrades | PASS | both reached `20260817_0006`; no drift | controlled disposable databases |
| `python scripts/verify_release.py` | PASS | db, api, admin, mobile healthy; explicit image-model degradation | controlled four-service Docker release |
| Controlled responsive/cache-cold browser script | PASS | 360/390/768/1440 no overflow; fresh LAN context; no unexpected console/request failures | controlled local Edge/Playwright |

Skipped/blocked checks and reason: GitHub-hosted CI did not allocate runners because B-CI-001 remains unresolved. No green hosted-CI claim is made. Native iOS/Android acceptance, hosted deployment and live MNO verification remain outside this local pass.

## Known defects/blockers

| ID | Severity | Description | Impact | Safe fallback | Owner/input | Next action |
|---|---|---|---|---|---|---|
| B-CI-001 | External | GitHub Actions billing/account lock prevents hosted runner allocation. | Hosted CI cannot reproduce local gates. | Preserve exact local evidence and pinned workflows; do not claim hosted green. | Repository owner | Resolve account lock and rerun workflow. |
| Image model unavailable | Known limitation | Accepted image classifier artifact is not active. | Full analysis reports degraded component availability. | Deterministic image evidence remains supporting only. | Future governed model work | Activate only after accepted artifact/evaluation. |

## Documentation updated

- `IMPLEMENTATION_STATUS.md`: final implementation SHA, exact gates, browser/release state and next task.
- `requirements_traceability.csv`: seven final-pass requirements and evidence.
- `DECISION_LOG.md`: unchanged; no stack, scope, taxonomy, API or database deviation was introduced.
- `CHANGELOG.md`: final pass and exact local acceptance summary.
- Evidence manifest/docs: final evidence record and Chapter Four index updated.

## Git evidence

```text
implementation commits:
b311c5e fix(risk): make high-risk copy reason-aware
32fac93 fix(ocr): gate MTN profile by provider
1a93faa fix(ocr): count independent region evidence
dfdd0be fix(ocr): preserve sender fallback provenance
8050488 refactor(ui): share fraud risk presentation
4f9a30a feat(ui): simplify screenshot checks and build details

push output and final remote-equal SHA are added to PR #18 after the final documentation commit.
```

## Next exact task

Resolve B-CI-001 and rerun the pinned hosted workflow. Do not reopen the completed hybrid accuracy phase unless a reproducible defect or new approved requirement is supplied.
