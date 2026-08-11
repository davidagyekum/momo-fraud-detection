# Session handoff — logical PR14 Colab preprocessing completion

## Session identity

- Date/time: 2026-08-11
- Phase/sub-phase: Logical PR14 transaction ETL, causal features and frozen temporal splits — Colab execution and closure
- Repository: `davidagyekum/momo-fraud-detection`
- Base SHA: `3e87dd7d79fdb91863b18a656aa6df735ee88041`
- Work branch: `codex/p14-frozen-splits`
- Executed implementation SHA: `af8cce11d4e3f5644f24019498826899d356b503`
- Pull request: not created in this session
- Push status: pending the final documentation/evidence commit
- Worktree status: verified; pending commit

## Scope completed

- Requirement IDs: FR-ML-005, FR-ML-006, NFR-AUD-001, NFR-DATA-001, NFR-MNT-001
- Backlog task IDs: logical PR14 full structured-source preprocessing
- Goal: transfer the two exact MoMTSim sources to the owner's private Drive, execute all three pinned preprocessing runs and stop before model fitting.
- Actual completed work: verified the existing PaySim archive; uploaded and Drive-verified the exact MoMTSim v1 and registered v2-derivative CSVs; completed PaySim, MoMTSim v1 and MoMTSim v2 frozen feature builds; read back all three Drive reports; recorded safe aggregate evidence; did not train, calibrate, select thresholds or inspect locked tests for decisions.

## Changed files

| Path | Change | Why |
|---|---|---|
| `docs/evidence/PR14_TRANSACTION_PREPROCESSING_COLAB.json` | Added exact transfer metadata and safe aggregate reports for all three sources | Preserve reproducible Colab evidence without committing private shards |
| `ml/notebooks/colab/03_build_transaction_features.ipynb` | Extended the Drive mount timeout and enabled forced remount | Reproduce the setup that recovered from repeated Colab DriveFS timeouts |
| `IMPLEMENTATION_STATUS.md` | Marked logical PR14 complete and removed the resolved source-transfer blocker | Hand off at the required pre-training stop boundary |
| `requirements_traceability.csv` | Linked completed PR14 preprocessing evidence | Replace pending-manifest notes with actual evidence |
| `CHANGELOG.md` | Recorded PR14 Colab completion | Keep phase history honest and reviewable |

## Database/migrations

- Migration revision(s): none
- Upgrade tested from: not applicable
- Downgrade/rollback notes: no product database mutation
- Data backfill: none
- Schema/ERD update: none

## API/contract

- Endpoints added/changed: none
- OpenAPI/client regenerated: not applicable
- Breaking change: none
- Error/permission behaviour: unchanged; pre-PR20 locked-test loading remains rejected by the repository implementation

## UI

- Screens/components: none
- States covered: not applicable
- Viewports/devices: not applicable
- Screenshot/evidence paths: none
- Accessibility notes: not applicable

## OCR/image/ML/verification

- Pipeline/model/rule/template versions: `transaction-temporal-split-v1`, `transaction-core-features-v1`, `transaction-core-preprocessor-v1`, `transaction-etl-report-v1`
- PaySim: 6,362,620 rows; 8,213 positives; split `4cca1058464f47b56a329b0a6b3fdd81d60ad81008b8e75d1a8e062a6b7206e1`; preprocessor `63f67bb24047d8fb28c0ce9102df6938b376bbc5adfb52a8921c87bb0762c574`; elapsed 768.49s; peak memory 2,056,527,872 bytes.
- MoMTSim v1: 1,720,181 rows; 175,518 positives; split `5562350167a75785929235f102fa39c98dc534e555791a03ac3ac0272ae5d72d`; preprocessor `8fc1f53990a4a0b9f97cab17ac0502495904a36f645e3e7aadbac31fabfc9456`; elapsed 265.192s; peak memory 2,056,527,872 bytes.
- MoMTSim v2 derivative: 4,225,938 rows; 2,233,118 positives; split `539bcb4679eb6ed250bc25affeeb38f9a659b4c3f4e2fd0ae724cc7299301bf4`; preprocessor `9a0ed3bdc9518041074b77aa0e95f292c33c7e16119520c0ddcea1eb57634eff`; elapsed 1,443.381s; peak memory 2,259,533,824 bytes.
- Metrics actually measured: preprocessing row/class/partition counts, hashes, elapsed time and peak memory only; no model metric.
- Safety assertions: every locked-test partition is sealed; every report states `locked_test_accessed_for_decisions=false` and `training_executed=false`.
- No fabricated or unavailable evidence: no fitting, model comparison, calibration, threshold selection, promotion or deployment occurred.

## Security/privacy

- Access-control impact: no public storage or sharing change; exact sources and generated bundles remain in the owner's private Drive.
- Private-data impact: no raw dataset, feature shard, label shard or provenance shard entered Git.
- Upload/storage impact: uploaded `synthetic_mobile_money_transaction_dataset.csv` (156,564,413 bytes, SHA-256 `da951eb9…`) and `momtsim-v2-derived-exact-dedup-v1.csv` (366,396,355 bytes, SHA-256 `642fcb2b…`) to `My Drive/momo-fraud/datasets`; Drive displayed 149.3 MB and 349.4 MB respectively.
- Operational recovery: default Drive mounts repeatedly timed out. The owner-controlled notebook copy used `force_remount=True` and a 600,000ms timeout; transaction code stayed pinned at `af8cce11…`.
- Audit events: browser upload completion and notebook aggregate readback were visibly verified; the public evidence contains only safe aggregate metadata.

## Verification performed

| Command/check | Result | Counts/summary |
|---|---|---|
| Chrome Drive upload dialog and folder listing | PASS | Two uploads complete; exact filenames displayed at 149.3 MB and 349.4 MB alongside PaySim at 177.8 MB |
| Colab pinned preflight for each dataset | PASS | Clean `af8cce11…` checkout; `full_training_executed=false` |
| Colab build and aggregate Drive report readback | PASS | Three exact reports; all source/split/preprocessor identities matched; locked tests sealed; training false |
| `.venv\\Scripts\\python.exe scripts\\verify_ml.py` | PASS | Ruff and strict mypy pass; 376 tests pass; 91.04% branch-aware coverage; deterministic governance, acquisition, lock, notebook and data checks pass; no model training |
| `.venv\\Scripts\\python.exe scripts\\check_secrets.py` | PASS | 509 candidate files scanned |

Skipped/blocked checks and reason: GitHub Actions remains externally unavailable under B-CI-001. No training gate was run because the owner explicitly required a stop before PR15 training.

## Known defects/blockers

| ID | Severity | Description | Impact | Safe fallback | Owner/input | Next action |
|---|---|---|---|---|---|---|
| B-CI-001 | External | Hosted runners cannot allocate under the account billing lock | No hosted reproduction | Preserve exact local and Colab evidence | Repository owner | Resolve account lock and rerun |
| P12-ACCEPTANCE | High | Historical controlled image model failed acceptance | Artifact remains inactive | Explicit unavailable state | Data/model owner | New governed version only after later data gates |

Resolved in this session: `PR14-COLAB-SOURCES`.

## Documentation updated

- `docs/evidence/PR14_TRANSACTION_PREPROCESSING_COLAB.json`
- `IMPLEMENTATION_STATUS.md`
- `requirements_traceability.csv`
- `CHANGELOG.md`
- this handoff

## Git evidence

```text
base SHA: 3e87dd7d79fdb91863b18a656aa6df735ee88041
executed code SHA: af8cce11d4e3f5644f24019498826899d356b503
final documentation/evidence commit: pending this handoff commit
push output: pending
```

## Next exact task

Stop and notify the project owner. Logical PR15 is transaction-model training in Google Colab and must not start until the owner explicitly proceeds after reviewing the PR14 evidence. PR16 online fraud-image collection and owner transaction intake remain later, separate consent/governance work.
