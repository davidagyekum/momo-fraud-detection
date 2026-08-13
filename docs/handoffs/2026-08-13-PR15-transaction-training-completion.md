# Session handoff — logical PR15 transaction training completion

## Session identity

- Date/time: 2026-08-13
- Phase/sub-phase: Logical PR15 transaction training, calibration and export — Colab evidence and closure
- Repository: `davidagyekum/momo-fraud-detection`
- Base branch: `codex/p14-frozen-splits`
- Base SHA: `f4862e32756a9b9ebde106a2eaf4993ba875b33a`
- Work branch: `codex/p15-transaction-models`
- Executed implementation SHA: `38e5a8c13ac61483c57501b8745aad3daa88848f`
- Pre-handoff head SHA: `b7fc9ea057e1c457eda951ae6e07ab2055d4efb9`
- Final head SHA: reported from Git after the handoff commit because a commit cannot contain its own SHA
- Pull request: not created at the time this file was written
- Push status: pending final commit and push
- Worktree status: expected clean after the final commit

## Scope completed

- Requirement IDs: FR-ML-005, FR-ML-006, NFR-AUD-001, NFR-DATA-001, NFR-MNT-001
- Backlog task IDs: logical PR15 source-specific transaction training, calibration and trusted export
- Goal: execute the owner-authorised PaySim, MoMTSim v1 and optional MoMTSim v2-derivative training workflows without opening a locked-test partition, then preserve honest reproducibility evidence.
- Actual completed work: completed all 14 configured fits for PaySim and MoMTSim v1; selected, chronologically calibrated and trusted-reload-verified one source-specific model per completed run; preserved exact code/config/source/split/preprocessor and artifact hashes; recorded the optional v2 stress run as deferred after repeated free-Colab backend disconnections. No locked-test, final-evaluation, activation, promotion or real-world probability claim occurred.

## Changed files

| Path | Change | Why |
|---|---|---|
| `docs/evidence/PR15_TRANSACTION_TRAINING_COLAB.json` | Added safe aggregate evidence for two completed runs and one deferred run | Preserve reproducible Colab evidence without committing models, checkpoints or private data |
| `IMPLEMENTATION_STATUS.md` | Marked PR15 complete under the blueprint's explicit v2-deferral allowance and moved the next task to PR16 | Keep phase and blocker state accurate |
| `requirements_traceability.csv` | Linked PaySim/MoMTSim v1 run evidence and the v2 deferral | Replace pending-run language with actual evidence |
| `CHANGELOG.md` | Recorded completed sources and the incomplete v2 boundary | Keep project history honest |
| `docs/handoffs/2026-08-13-PR15-transaction-training-completion.md` | Added this session handoff | Allow PR16 to start without reconstructing the long Colab session |

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
- Error/permission behaviour: unchanged; pre-PR20 locked-test loading remains rejected

## UI

- Screens/components: none
- States covered: not applicable
- Viewports/devices: not applicable
- Screenshot/evidence paths: none
- Accessibility notes: not applicable

## OCR/image/ML/verification

- Pipeline/model/rule/template versions: `transaction-core-training-report-v1`, `transaction-risk-thresholds-v1`, source-specific `transaction-core-*-pr15-v1`
- Shared config SHA-256: `cbfb5a5cccab25f9a8cccc86b8d77105f8215e0dd7e31a8abc0036ea80fda02f`
- PaySim: run `20260812T034848Z_transaction-core_38e5a8c1_seed123`; 14 fit checkpoints; random forest selected; tuning average precision `0.37612244`; three-seed mean/stddev `0.37482429`/`0.00138771`; isotonic thresholds `0.0610687` and `0.4`; artifact SHA-256 `6b16cab3a60aa1fee5527243254beed87680e1d42231335e9423d1f9d0ed991c`; reload parity passed over 128 rows.
- MoMTSim v1: run `20260812T143430Z_transaction-core_38e5a8c1_seed42`; 14 fit checkpoints; XGBoost selected; tuning average precision `0.35126485`; three-seed mean/stddev `0.35126485`/`0.0`; isotonic thresholds `0.30333994` and `0.53468669`; artifact SHA-256 `4f13884cb3496612dc32fe9b283683206279f25162ab0ecd4aec985d0df263b0`; reload parity passed over 128 rows.
- MoMTSim v2 derivative: exactly one dummy-prior checkpoint pair, identity `bb5fba536f418cdb2efb57a7d574220bcd71783d93a9a07eb6b106c374502096`; the first full-data logistic fit never completed before repeated backend disconnections. No completed model bundle or report exists.
- Metrics actually measured: tuning and calibration metrics only on synthetic-source, non-locked partitions. Domain-shift values are research-only.
- Limitations: neither completed artifact is final-evaluated, active, promotable or a real-world probability model. The optional v2 run is incomplete and cannot support any completion or comparison claim.
- No fabricated or unavailable evidence: all locked tests remained sealed; `final_evaluation_executed=false` and `locked_test_accessed_for_decisions=false` throughout.

## Security/privacy

- Access-control impact: no public storage or sharing change; bundles remain in the owner's private Drive.
- Private-data impact: no raw dataset, private message, screenshot, checkpoint or model artifact entered Git.
- Upload/storage impact: none in this closure commit; only safe hashes and aggregate metrics are recorded.
- Audit events: exact immutable code identity and source/split/preprocessor/artifact hashes are preserved.
- Security checks: repository verification and secret/prohibited-artifact scans are recorded below.

## Verification performed

| Command | Result | Counts/summary | Duration |
|---|---|---|---|
| `.venv\\Scripts\\python.exe scripts\\verify_ml.py` | PASS | Format, Ruff and strict mypy pass; 391 tests pass; 90.98% branch-aware coverage; governance, acquisition, lock, notebook and controlled-data checks pass; no training executed | 115.1s |
| `.venv\\Scripts\\python.exe scripts\\check_secrets.py` | PASS | 517 candidate files scanned | 3.8s |
| PowerShell JSON parse and evidence assertions | PASS | 3 source records: 2 completed, 1 explicitly deferred; locked access and final evaluation false | <1s |
| `git diff --check` | PASS | No whitespace errors | <1s |

Skipped/blocked checks and reason: hosted GitHub Actions remains externally unavailable under B-CI-001. MoMTSim v2 full training was deferred under the blueprint after repeated free-Colab runtime failures; no locked-test or final-evaluation check was authorised.

## Known defects/blockers

| ID | Severity | Description | Impact | Safe fallback | Owner/input | Next action |
|---|---|---|---|---|---|---|
| B-CI-001 | External | Hosted runners cannot allocate under the account billing lock | No hosted reproduction | Preserve exact local and Colab evidence | Repository owner | Resolve account lock and rerun |
| P12-ACCEPTANCE | High | Historical controlled image model failed acceptance | Artifact remains inactive | Explicit unavailable state | Data/model owner | New governed version only after later data gates |
| PR15-MOMTSIM-V2-RUNTIME | Optional | Repeated free-Colab disconnections prevented the full-data logistic fit | No completed v2 model bundle | Preserve explicit deferral and use only PaySim/v1 evidence | Project owner | Retry on a durable runtime or approve a separately versioned bounded configuration |

## Documentation updated

- `IMPLEMENTATION_STATUS.md`: PR15 complete, v2 limitation explicit, PR16 next
- `requirements_traceability.csv`: actual completed/deferred evidence linked
- `DECISION_LOG.md`: unchanged; the blueprint already explicitly permits transparent v2 deferral
- `CHANGELOG.md`: PaySim/v1 completion and v2 deferral recorded
- Evidence manifest/docs: `docs/evidence/PR15_TRANSACTION_TRAINING_COLAB.json`

## Git evidence

```text
base SHA: f4862e32756a9b9ebde106a2eaf4993ba875b33a
executed code SHA: 38e5a8c13ac61483c57501b8745aad3daa88848f
pre-handoff head SHA: b7fc9ea057e1c457eda951ae6e07ab2055d4efb9
final documentation/evidence commit: reported after commit
push output: reported after push
```

## Next exact task

Create `codex/p16-ghana-screenshot-dataset` from the intended integration base and implement PR16's private intake pilot: consent-state validation, pseudonymous record IDs, filename/metadata/region de-identification, cryptographic and perceptual duplicate checks, withdrawal/deletion propagation, annotation/review queues and participant/source group-safe split generation. The owner's exported messages and every acquired screenshot remain outside Git and must not be admitted until the pipeline validates their consent, rights and review state.
