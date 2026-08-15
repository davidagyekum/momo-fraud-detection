# Session handoff — logical PR14 preprocessing foundation

## Session identity

- Date/time: 2026-08-11
- Phase/sub-phase: Logical PR14 transaction ETL, causal features and frozen temporal splits — pre-Colab foundation
- Repository: `davidagyekum/momo-fraud-detection`
- Base branch: logical PR13 pushed head
- Base SHA: `8276a94d64803afab65d9b3113f89617ebab32e4`
- Work branch: `codex/p14-frozen-splits`
- Final implementation SHA: `af8cce11d4e3f5644f24019498826899d356b503`
- Pinned-notebook head before this handoff: `e40f4ad52af6a19985908935aa698a2c3948a614`
- Pull request: not created in this session
- Push status: implementation and notebook-pin commits pushed to `origin/codex/p14-frozen-splits`
- Worktree status: this handoff pending its final commit

## Scope completed

- Requirement IDs: FR-ML-005, FR-ML-006, NFR-AUD-001, NFR-DATA-001, NFR-MNT-001
- Backlog task IDs: logical PR14 transaction ETL/features/splits foundation
- Goal: create leakage-safe, source-specific, reproducible preprocessing before any transaction model selection.
- Actual completed work: implemented exact source mappings, opaque row IDs, chronological 70/10/10/10 split planning, minimum-positive adjustment, same-step-safe causal history, train-only preprocessing, atomic Parquet feature/label/provenance shards, locked-test loading refusal, STFD's one-corpus train-only manifest and a clean pinned Colab notebook.

## Changed files

| Path | Change | Why |
|---|---|---|
| `ml/src/momo_fdvs_ml/transaction_pipeline.py` | Added canonical mapping, temporal split and causal-history contracts | Prevent chronological, same-step, identity and forbidden-field leakage |
| `ml/src/momo_fdvs_ml/transaction_etl.py` | Added exact source scan, train-only preprocessing and atomic Parquet build/load controls | Produce restart-safe private PR14 artifacts without model training |
| `ml/notebooks/colab/03_build_transaction_features.ipynb` | Added output-free preprocessing wrapper pinned to `af8cce11…` | Run full structured preprocessing in owner-operated Colab |
| `data/splits/stfd-external-pretraining-v1.json` | Froze all 3,932 pairs as one train-only group | Enforce ADR-030 without internal STFD evaluation |
| tests, locks, ADR-031, plan, README, status, traceability and changelog | Added verification and operating evidence | Keep the phase reproducible and bounded |

## Database/migrations

- Migration revision(s): none
- Upgrade tested from: not applicable
- Downgrade/rollback notes: no product data/schema mutation
- Data backfill: none
- Schema/ERD update: none

## API/contract

- Endpoints added/changed: none
- OpenAPI/client regenerated: not applicable
- Breaking change: none
- Error/permission behaviour: source/hash/count/header/order drift, unsafe ZIP entrypoints, forbidden features, missing shards and pre-PR20 locked-test loading fail closed

## UI

- Screens/components: none
- States covered: not applicable
- Viewports/devices: not applicable
- Screenshot/evidence paths: none
- Accessibility notes: not applicable

## OCR/image/ML/verification

- Pipeline/model/rule/template versions: `transaction-temporal-split-v1`, `transaction-core-features-v1`, `transaction-core-preprocessor-v1`, `transaction-etl-report-v1`, `external-pretraining-split-v1`
- Dataset/split/artifact hashes: STFD split manifest `1ebd79ad359edf4456c9fb31881b5fd228b3c3189e6707c41abc583fb2e1f71b`; structured full-run manifests pending Colab execution
- Metrics actually measured: fixture pipeline only; 376 repository tests and no model metric
- Limitations: full PaySim/MoMTSim feature bundles, runtime and Linux peak-memory evidence are pending the pinned Colab runs
- No fabricated or unavailable evidence: no model fitting, calibration, threshold selection, locked-test decision access, promotion or deployment occurred

## Security/privacy

- Access-control impact: locked-test loader refuses access before PR20
- Private-data impact: raw actor IDs remain transient and are absent from feature shards/public reports; opaque row hashes remain private provenance
- Upload/storage impact: the existing PaySim archive is already in the owner's private Drive. The connector rejected both requested MoMTSim uploads before sending bytes because exact payload/destination authorization was not explicit in the transcript.
- Audit events: no Drive upload succeeded; no external state changed during the rejected write
- Security checks: secret/prohibited-artifact scan passed over 507 candidate files after adding this handoff

## Verification performed

| Command | Result | Counts/summary | Duration |
|---|---|---|---|
| `.venv\Scripts\python.exe scripts\verify_ml.py` | PASS | Ruff, strict mypy, 376 tests at 91.04% branch-aware coverage, governance/lock/notebook/data drift gates | 109.6s combined run |
| `.venv\Scripts\python.exe scripts\check_secrets.py` | PASS | 507 candidate files in the final post-handoff scan | 3.2s final scan |
| focused transaction/CLI/notebook suites | PASS | 51 transaction/CLI tests; 29 notebook/CLI pin tests | 13.9s and 11.4s |
| `git diff --check` and traceability CSV shape | PASS | no whitespace errors; all 99 CSV rows have 12 columns | under 5s |

Skipped/blocked checks and reason: full structured-source Colab preprocessing requires the exact MoMTSim source files in the owner's private Drive. The Google Drive connector rejected the attempted transfer before upload pending explicit authorization for the two named payloads and destination. GitHub Actions remains externally unavailable under B-CI-001.

## Known defects/blockers

| ID | Severity | Description | Impact | Safe fallback | Owner/input | Next action |
|---|---|---|---|---|---|---|
| PR14-COLAB-SOURCES | Blocking | Exact v1 and v2-derivative CSV upload was rejected before transfer | MoMTSim Colab preprocessing cannot start | Preserve local restricted files and hashes | Project owner explicitly authorizes those two files to the existing private Drive datasets folder | Upload, metadata-verify and run each PR14 job |
| B-CI-001 | External | Hosted runners cannot allocate under the account billing lock | No hosted reproduction | Preserve exact local evidence | Repository owner | Resolve account lock and rerun |
| P12-ACCEPTANCE | High | Historical controlled image model failed acceptance | Artifact remains inactive | Explicit unavailable state | Data/model owner | New governed version only after later data gates |

## Documentation updated

- `IMPLEMENTATION_STATUS.md`: PR14 foundation state, exact SHA, gate and upload blocker
- `requirements_traceability.csv`: PR14 split/privacy/reproducibility controls
- `DECISION_LOG.md`: ADR-031
- `CHANGELOG.md`: PR14 foundation
- Evidence manifest/docs: STFD frozen assignment and PR14 implementation plan

## Git evidence

```text
git status --short: handoff documentation pending its final commit
git log --oneline 8276a94d64803afab65d9b3113f89617ebab32e4..HEAD:
e40f4ad docs(colab): pin PR14 preprocessing notebook
af8cce1 feat(ml): build leakage-safe transaction splits
push output: both commits pushed to origin/codex/p14-frozen-splits
```

## Next exact task

Obtain explicit project-owner authorization to upload these exact local private files to the owner's existing private `momo-fraud/datasets` Google Drive folder: `synthetic_mobile_money_transaction_dataset.csv` (SHA-256 `da951eb95735da96271740a3e66b676b342d3831ce3111cd19dbfa020d3bd0a7`) and `momtsim-v2-derived-exact-dedup-v1.csv` (SHA-256 `642fcb2ba7c9cbfffb933729d118f426fefddcbaabbf002793807be169fe80cd`). After upload metadata verification, run the pinned notebook separately for PaySim, MoMTSim v1 and MoMTSim v2. Review safe summaries and close PR14. Stop and notify the owner before any PR15 transaction-training run.
