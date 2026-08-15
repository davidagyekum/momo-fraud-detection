# PR18 evidence-aware screenshot analysis product handoff

## Session identity

- Date/time: 2026-08-15, Africa/Lagos
- Phase/sub-phase: Logical PR18 analysis product
- Repository: `davidagyekum/momo-fraud-detection`
- Base branch: `codex/p17-ocr-benchmark`
- Base SHA: `d9b096af46232530bc47eff96856260d083885e4`
- Work branch: `codex/pr18-analysis-product`
- Implementation head SHA: `756b30fb3371469ea4ff7ad41097ab2dc10cb1ef`
- Final publication head SHA: pending documentation commit
- Pull request: pending publication
- Push status: pending publication
- Worktree status: documentation changes pending final verification

## Scope completed

- Requirement IDs: FR-RISK-001, FR-RISK-004 through FR-RISK-007, FR-HIST-001, FR-HIST-006 and FR-VER-007 complete; FR-RISK-002/003 and FR-HIST-002 intentionally remain in progress.
- Goal: turn the existing private screenshot/OCR/reference foundations into one honest, persisted and mobile-usable analysis journey.
- Actual completed work: hash-bound categorical risk policy; eight-stage immutable orchestration; start/result/evidence/history/detail API projections; typed mobile clients; accessible result/history/detail screens; controlled PostgreSQL vertical slice.

## Changed areas

| Area | Change | Why |
|---|---|---|
| `services/api/src/momo_fdvs/services/risk_policy.py` | Strict categorical/null-score policy | Prevent fabricated probabilities while model artifacts are unavailable |
| `services/api/src/momo_fdvs/services/analysis_orchestrator.py` | Persisted, idempotent eight-stage orchestration | Preserve successful evidence and immutable versions across partial failures |
| `services/api/src/momo_fdvs/api/v1` | Start, poll, evidence, history and detail projections | Provide owner/assigned-investigator-safe product APIs with explicit schemas |
| `services/api/src/momo_fdvs/policies/evidence_access.py` | Central transaction-evidence object policy | Deny unassigned investigators and administrators without leaking object existence |
| `apps/mobile/src` | Typed clients and routed analysis/history/detail UI | Complete the screenshot journey on Expo without conflating risk and verification |
| `services/api/tests/integration/test_analysis_journey.py` | Repeatable fictitious vertical slice | Prove IDs, privacy and persistence across the complete flow |

## Database/migrations

- Migration revision(s): `20260815_0003` adds immutable stage-row and terminal-analysis triggers.
- Upgrade tested from: empty database and previous revision `20260809_0002`; both reached `20260815_0003 (head)`.
- Downgrade/rollback notes: downgrade removes only the two new triggers and terminal-analysis trigger function; no data backfill is present.
- Schema/ERD update: generated ER drift check passes.

## API/contract

- Endpoints added/changed: `POST /api/v1/transactions/{transaction_id}/analyses`, `GET /api/v1/analyses/{analysis_run_id}`, `GET /api/v1/analyses/{analysis_run_id}/evidence`, `GET /api/v1/transactions`, `GET /api/v1/transactions/{transaction_id}`.
- OpenAPI/client regenerated: yes; SHA-256 `183d2f53fe3e5742880f46c44a93bd5274ed4d8df31de87bcf9e59f95b5dedb8`.
- Breaking change: none; legacy risk taxonomy is projected only when categorical evidence supports it.
- Error/permission behaviour: missing OCR confirmation, invalid/reused idempotency, unavailable policy and foreign ownership fail closed with safe errors; only the owner or investigator assigned to an active case may read cross-owner analysis/receipt evidence.

## UI

- Screens/components: OCR confirmation handoff, analysis polling/result, owner history filters/pagination, transaction detail and prior-run navigation.
- States covered: session restore, loading, partial, model unavailable, empty, offline, error, retry and permission redirect.
- Build evidence: Expo web export generated 25 static routes.
- Accessibility notes: status text and labels convey meaning independently of colour; risk and verification are separate headings; confirmed-field/correction counts and the fraud-risk disclaimer are explicit; null scores are omitted.

## OCR/image/ML/verification

- Pipeline/model/rule/template versions: `analysis-result-v1`, `analysis-risk-policy-demo-v1`, stored-reference verifier and existing versioned OCR/forensics evidence.
- Policy SHA-256: `ab45ca650148c13f67894c2867effb026e3c77a95d7448707400a8fd59760859`.
- Metrics actually measured: backend 85.40% branch-aware coverage; mobile 89.60% statement/71.34% branch coverage; ML 90.15% branch-aware coverage. These are code-coverage metrics, not model accuracy.
- Limitations: accepted image classifier/localizer and screenshot-derived structured model are unavailable; P12 macro F1 remains `0.333333` and its artifact is inactive; verification is stored/imported, never live MNO confirmation.
- No fabricated or unavailable evidence: scores are null when categorical/model evidence cannot support them; deterministic image signals are supporting-only.

## Security/privacy

- Access-control impact: history/detail remain owner-scoped; analysis, evidence and receipt bytes permit only the owner or the investigator assigned to an active case. Role alone is insufficient.
- Private-data impact: raw images remain private; result/history/detail/evidence omit filenames, object keys and raw OCR values.
- Upload/storage impact: unchanged hostile-image validation and private generated keys.
- Audit/immutability: stage rows are insert-only and terminal analysis runs reject update/delete at the database; reanalysis creates a new run.
- Security checks: secret/artifact scan passes 588 candidates; controlled journey asserts no private filename/object-key leakage; negative ADMIN/INVESTIGATOR tests assert non-enumerating denial.

## Verification performed

| Command | Result | Counts/summary |
|---|---|---|
| `python scripts/verify_backend.py` | PASS | 172 tests; 85.40% branch-aware coverage; format/Ruff/mypy/OpenAPI/ER pass |
| Mobile format/lint/type/test/export | PASS | 58 tests; 89.60% statements; 71.34% branches; 25 web routes |
| `python scripts/verify_ml.py` | PASS | 714 tests; 90.15% branch-aware coverage; training false |
| `python scripts/check_secrets.py` | PASS | 588 candidate files |
| Controlled journey test | PASS | register/login through immutable result/history/detail/evidence |
| Alembic empty and previous revision upgrades | PASS | both end at `20260815_0003 (head)` |
| `python scripts/verify.py --backend` | HOST BOUNDARY | Secret scan and nested backend gate pass; wrapper exits 1 only because Node/npm do not match the pin and host Tesseract is absent |

Skipped/blocked checks and reason: hosted GitHub Actions cannot allocate runners because of the repository-owner billing lock. The local host is Node 22.23.2/npm 10.9.8 instead of pinned Node 24.14.0/npm 10.9.0; the existing dependency tree was reused without downloads, and all mobile tests/type/lint/export commands passed.

## Known defects/blockers

| ID | Severity | Description | Impact | Safe fallback | Owner/input | Next action |
|---|---|---|---|---|---|---|
| P12-ACCEPTANCE | High | Image classifier failed acceptance at macro F1 0.333333 | No CNN/localizer product evidence | Explicit `UNAVAILABLE`; deterministic checks supporting-only | Data/model owner | Collect governed representative groups and train a new version |
| B-CI-001 | Medium | Hosted Actions billing lock | No independent hosted run | Preserve exact local evidence | Repository owner | Resolve billing and rerun workflows |
| PR18-LIVE-MNO | Boundary | No authorised provider integration | Verification is not live provider confirmation | Stored/imported reference disclaimer | Provider/project owner | Add a separately authorised adapter in a later phase |

## Documentation updated

- `IMPLEMENTATION_STATUS.md`: PR18 state, exact gates, boundaries and next phase.
- `requirements_traceability.csv`: completed/in-progress PR18 requirements.
- `DECISION_LOG.md`: ADR-038 categorical null-score policy.
- `CHANGELOG.md`: PR18 product entry.
- Evidence: `docs/evidence/PR18_ANALYSIS_PRODUCT.json` plus manifest row.

## Next exact task

Review and merge the stacked PR18 branch, then implement logical PR19 reporting/case workflow from the merged analysis contracts. Do not activate the rejected P12 artifact, open locked-test partitions before PR20, or represent stored-reference verification as live MNO confirmation.
