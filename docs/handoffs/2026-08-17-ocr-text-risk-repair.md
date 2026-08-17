# Codex Session Handoff

## Session identity

- Date/time: `2026-08-17`, Africa/Lagos
- Phase/sub-phase: audit repair 40 — obvious-scam OCR text risk
- Repository: `davidagyekum/momo-fraud-detection`
- Base branch: `codex/pr19-release-hardening`
- Base SHA: `447e7be6ed355716f007023503f1cfcf5ddd19ac`
- Work branch: `codex/audit-fix-40-ocr-text-risk`
- Final head SHA: reported after the handoff commit
- Pull request: not created in this session
- Push status: pending final commit/push
- Worktree status: pending final commit

## Scope completed

- Requirement IDs: FR-TEXT-RISK-001 through FR-TEXT-RISK-006,
  NFR-TEXT-PRIV-001, NFR-TEXT-AUD-001; strengthens FR-OCR-002/005,
  FR-RISK-001/004/005 and NFR-ACC-001.
- Backlog task IDs: replacement package addendum; no existing backlog row was
  silently repurposed.
- Goal: integrate the replacement obvious-fraud OCR package without regressing
  the current risk, verification, privacy or model-governance contracts.
- Actual completed work: deterministic assessor, persisted OCR preview, existing
  semantic-stage integration, categorical policy v2, mobile warning card,
  schemas/OpenAPI, tests, security basis, ADR, traceability and evidence.

## Changed files

| Path | Change | Why |
|---|---|---|
| `services/api/src/momo_fdvs/services/text_fraud.py` | Added versioned deterministic assessment and safe projections | Detect bounded obvious-scam language without persisting raw matches |
| `services/api/src/momo_fdvs/services/ocr.py` and OCR API/schema | Persisted and replayed `fraud_preview` | Give the owner immediate immutable text-risk evidence |
| analysis orchestrator/API/schema and risk policy JSON/service | Added text signal to existing semantic stage and categorical precedence | Preserve ADR-038 null-score policy and separate verification |
| `apps/mobile/src/components/text-fraud-risk-card.tsx` and OCR/result clients/screens | Added accessible immediate preview and version disclosure | Provide actionable non-colour-only guidance before final analysis |
| backend/mobile tests and OpenAPI snapshot | Added unit, integration, privacy and UI regression coverage | Prove behavior and contract compatibility |
| specs, ADR-040, traceability, changelog, security/evidence docs | Recorded source basis and boundaries | Prevent silent scope/contract drift |

## Database/migrations

- Migration revision(s): none added; no database schema change.
- Upgrade tested from: empty isolated database through `20260816_0005 (head)`.
- Downgrade/rollback notes: code rollback removes the additive API/UI fields;
  stored `_text_fraud` JSON remains harmless versioned evidence.
- Data backfill: none; legacy OCR returns explicit unavailable state and is not
  recomputed.
- Schema/ERD update: no metadata change; ER drift check passes.

## API/contract

- Endpoints added/changed: additive `fraud_preview` on OCR run/review; additive
  text component and schema/ruleset versions on analysis evidence.
- OpenAPI/client regenerated: yes; drift check passes.
- Breaking change: none intended; older stored OCR fails to explicit unavailable.
- Error/permission behaviour: existing owner/object permissions retained; no raw
  match text appears in public, stage or audit projections.

## UI

- Screens/components: mobile OCR review and analysis detail; new
  `TextFraudRiskCard`.
- States covered: fraudulent, suspicious, no decisive signal and unavailable;
  existing loading/error/offline/permission states retained.
- Viewports/devices: static 28-route web export and existing browser flows pass;
  no new native-device claim.
- Screenshot/evidence paths: no screenshot committed; deterministic UI tests and
  Impeccable detector result `[]` are recorded.
- Accessibility notes: explicit status text, live-region label and safety action;
  colour is not the only signal.

## OCR/image/ML/verification

- Pipeline/model/rule/template versions: `ocr-pipeline-v1`,
  `momo-text-fraud-assessment-v1`, `ghana-momo-obvious-scam-rules-v1`,
  `analysis-risk-policy-demo-v2`.
- Dataset/split/artifact hashes: replacement ZIP `9b054500…`; policy
  `1792dc73…`; no dataset/split/model artifact created.
- Metrics actually measured: test/coverage counts only; no model metric.
- Limitations: deterministic high-precision rules are not representative
  accuracy evidence; host Tesseract absent; accepted image/structured models
  remain unavailable.
- No fabricated or unavailable evidence: current-source container demo used real
  Tesseract 5.3.0 and returned `FRAUDULENT`, rule score 95, non-probabilistic.

## Security/privacy

- Access-control impact: none; existing owner/assigned-investigator checks remain.
- Private-data impact: raw OCR stays private; projections use fixed allowlists.
- Upload/storage impact: none beyond safe `_text_fraud` aggregate in existing
  immutable OCR JSON.
- Audit events: retain versions/status/class/reason codes only.
- Security checks: 31 scenarios and 642-file secret/artifact scan pass.

## Verification performed

| Command | Result | Counts/summary | Duration |
|---|---|---|---|
| `scripts/verify_backend.py` with isolated PostgreSQL | PASS | 213 tests; 85.63% coverage; format/lint/type/OpenAPI/ER clean | ~110 s latest standalone |
| `scripts/verify_mobile.py` | PASS | 67 tests; 83.80% statements; 28 routes | 40.93 s in full wrapper |
| `scripts/verify_admin.py` | PASS | 40 tests; 3 Playwright; build | 180.94 s in full wrapper |
| `scripts/verify_ml.py` | PASS | 714 tests; 90.15%; training false | 119.50 s in full wrapper |
| `scripts/verify_e2e.py` | PASS | API, mobile and admin controlled journeys | 29.34 s |
| `scripts/verify_security.py` | PASS | 31 database scenarios and policy scans | 26.31 s |
| `scripts/verify_release.py` on `momo-fdvs-pr19-release` | PASS | four healthy services; migration head; models degraded | 15.7 s |
| current-source container OCR demo | PASS | Tesseract 5.3.0; FRAUDULENT; rule score 95; not probability | ~98 s |

Skipped/blocked checks and reason: hosted CI and native-device/browser matrix were
not available. The all-section wrapper exits non-zero for the known host runtime
doctor mismatch; every registered product section passes. `flask db check`
detects the pre-existing PR19 constraint-name mismatch described below.

## Known defects/blockers

| ID | Severity | Description | Impact | Safe fallback | Owner/input | Next action |
|---|---|---|---|---|---|---|
| B-ENV-003 | Low | Host Node/npm differ from pins; host Tesseract absent | Wrapper doctor non-zero; host real-OCR unavailable | Bundled Node commands pass; real OCR verified in repository container | Environment owner | Activate pinned runtime/install host Tesseract only if host execution is required |
| B-MIG-001 | Medium | Applied PR19 check constraint has duplicated naming-convention prefix versus model metadata | `flask db check` reports one remove/add drift | Database is at head; tests and ER pass; do not rewrite applied migration | Database owner | Decide and test a forward rename migration or metadata compatibility fix in a separate repair |

## Documentation updated

- `IMPLEMENTATION_STATUS.md`: branch, phase, gates, boundary and blocker updated.
- `requirements_traceability.csv`: nine text-risk/privacy/audit/governance rows added.
- `DECISION_LOG.md`: ADR-040 accepted.
- `CHANGELOG.md`: Unreleased entry added.
- Evidence manifest/docs: `docs/evidence/OCR_TEXT_FRAUD_REPAIR.md` and
  `docs/security/OCR_TEXT_FRAUD_RULE_BASIS.md` added.

## Git evidence

```text
git status --short: tracked implementation/docs changes plus seven intended new files before commit
git log --oneline 447e7be6..HEAD: populated after final commit
push output: populated in final session report
```

## Next exact task

Review the additive OCR/analysis schemas and mobile wording on
`codex/audit-fix-40-ocr-text-risk`, merge the repair, then begin PR20 final
documentation/inspection. Handle B-MIG-001 only as a separately scoped forward
migration/metadata compatibility decision.
