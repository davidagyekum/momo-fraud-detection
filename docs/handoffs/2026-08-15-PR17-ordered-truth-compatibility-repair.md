# Codex Session Handoff

## Session identity

- Date/time: `2026-08-15T00:23:31+01:00`
- Phase/sub-phase: Logical PR17 parser-ceiling v3 owner-run compatibility repair
- Repository: `davidagyekum/momo-fraud-detection`
- Base branch: `main`
- Base SHA: `b1284e37f8b4e6a38587fee68a44ed8a74203323`
- Work branch: `codex/p17-ocr-benchmark`
- Follow-up starting SHA: `4eb0702ca8f858fdf6bfc6b267445e515a1560ab`
- Immutable repair SHA: `a4dc60d0d4ada44c7c5bad4fe3103f0964ead4eb`
- Final head SHA: documentation closure commit at pushed branch head
- Pull request: not created in this session
- Push status: pending at handoff authoring time
- Worktree status: pending documentation closure at handoff authoring time

## Scope completed

- Requirement IDs: `NFR-ACC-001`, `NFR-PRIV-001`, logical PR17 measurement contract
- Backlog task IDs: PR17 parser-ceiling v3 owner validation follow-up
- Goal: unblock the owner-operated aggregate v3 diagnostic without changing parser output, private-data boundaries, OCR engines, training or locked-test access
- Actual completed work: traced the reported Colab exception to a compatibility regression introduced by the conflicting-duplicate truth guard; confirmed the PR16 private OCR truth contract stores an ordered list and permits repeated field annotations; confirmed the historical scorer selected the first non-empty occurrence; reproduced the owner error with a RED test; restored the established ordered primary-occurrence rule; retained the recipient comparison, warning, parser-schema and availability repairs; pinned the output-free notebook to the immutable repair commit; and recorded the stopped run without a metric claim.

## Changed files

| Path | Change | Why |
|---|---|---|
| `ml/src/momo_fdvs_ml/ocr_benchmark.py` | Restored first-non-empty occurrence selection for ordered truth fields | Preserve the governed archive and historical scoring contract when a screenshot contains repeated field annotations |
| `ml/tests/test_ocr_benchmark.py` | Replaced the incompatible conflict rejection with an ordered-primary regression | Reproduce the owner failure and prevent recurrence |
| `ml/notebooks/colab/06_benchmark_ocr.ipynb` | Pinned `TARGET_COMMIT` to `a4dc60d0…` | Make the corrected owner rerun immutable |
| `ml/notebooks/colab/notebook_report.json` | Refreshed the clean notebook hash | Keep notebook policy evidence canonical |
| `IMPLEMENTATION_STATUS.md`, `requirements_traceability.csv`, `CHANGELOG.md` | Recorded the failed attempt, correction and pending rerun | Avoid a false v3 metric or obsolete commit instruction |
| `docs/superpowers/plans/2026-08-14-pr17-measurement-contract-repair.md` | Added an owner-run correction note | Reconcile the implementation plan with the actual governed truth schema |
| `docs/handoffs/2026-08-15-PR17-ordered-truth-compatibility-repair.md` | Added this handoff | Preserve exact scope, evidence and rerun boundary |

## Database/migrations

- Migration revision(s): none
- Upgrade tested from: not applicable
- Downgrade/rollback notes: revert `a4dc60d0…` only if the ordered truth schema is migrated to an explicit primary-field contract and the private archive is rebuilt and reverified
- Data backfill: none
- Schema/ERD update: none

## API/contract

- Endpoints added/changed: none
- OpenAPI/client regenerated: not applicable
- Breaking change: none; this repair restores prior scoring compatibility
- Error/permission behaviour: missing parser fields, inconsistent parser availability states, invalid warning codes, invalid bundle identity and locked-test requests still fail closed

## UI

- Screens/components: none
- States covered: not applicable
- Viewports/devices: not applicable
- Screenshot/evidence paths: none
- Accessibility notes: not applicable

## OCR/image/ML/verification

- Pipeline/model/rule/template versions: parser ceiling remains `ghana-ocr-parser-ceiling-report-v3`; parser remains `ghana-momo-parser-v1`; field schema remains `ghana-momo-ocr-fields-v1`; benchmark remains v2
- Dataset/split/artifact hashes: verified private development archive remains `8a7f4b58e20569775dc237e5e4fefba78e2bc5aa8c40d5ee41dd893d495ea9b9`; development manifest remains `1ba8c58e1c29b77a46ba3cc54da7843dd84f090fdb2e731704091162d556d644`; split remains `3c2bd2e3727b62f0a61f01a7eebcbe49da7ed0ac124a8f765d471533d867d941`; notebook hash is `ef1339e70d3acb94eec188798c31496c968f27c17641c741513dc5637a6a7ef0`
- Metrics actually measured: no new metric. The first v3 attempt stopped before report writing with the bounded safe error category `conflicting OCR truth for amount`.
- Limitations: the corrected v3 report has not yet been produced; no outcome denominator, subtype count or accuracy change is claimed
- No fabricated or unavailable evidence: no OCR engine was rerun, no recognizer/model was trained, no locked-test record was accessed and no private value or record identifier was committed

## Security/privacy

- Access-control impact: none
- Private-data impact: private validation transcripts were read only in the authorized owner-operated Colab diagnostic; the exception exposed only a canonical field name and no value or identifier
- Upload/storage impact: no repository private artifact; no valid v3 report was written by the failed attempt
- Audit events: immutable repair commit, notebook hash and failed-run boundary recorded in repository documentation
- Security checks: aggregate report redaction tests remain green; notebook remains output-free; secret/prohibited-artifact scan passes 556 candidate files

## Verification performed

| Command | Result | Counts/summary | Duration |
|---|---|---|---|
| `.venv\\Scripts\\python.exe -m pytest ml\\tests\\test_ocr_benchmark.py -q -k first_ordered_truth_occurrence` | RED as expected | Failed on `OCRBenchmarkError: conflicting OCR truth for amount`; focused-run coverage gate also failed because only one test ran | 1.92 s |
| `.venv\\Scripts\\python.exe -m pytest ml\\tests\\test_ocr_benchmark.py -q -k first_ordered_truth_occurrence --no-cov` | PASS | 1 passed, 38 deselected | 0.28 s |
| `.venv\\Scripts\\python.exe -m pytest ml\\tests\\test_ocr_benchmark.py ml\\tests\\test_ocr_parser.py -q --no-cov` | PASS | 73 passed | 1.86 s |
| `.venv\\Scripts\\python.exe -m ruff check ml\\src\\momo_fdvs_ml\\ocr_benchmark.py ml\\tests\\test_ocr_benchmark.py` | PASS | no issues | focused |
| `.venv\\Scripts\\python.exe -m mypy ml\\src\\momo_fdvs_ml\\ocr_benchmark.py` | PASS | no issues in one source file | focused |
| `.venv\\Scripts\\python.exe scripts\\verify_ml.py` | PASS | 626 passed, 90.08% branch-aware coverage; format, Ruff, strict mypy, governance, acquisition readiness, lock, notebook and controlled-data gates passed | 61.13 s tests plus gates |
| `.venv\\Scripts\\python.exe scripts\\check_secrets.py` | PASS | 556 candidate files scanned | 2.0 s |
| `.venv\\Scripts\\python.exe scripts\\verify.py --ml` | PARTIAL / expected host-doctor failure | ML verification and 556-file secret scan pass; wrapper is non-zero because host Node/npm are not pinned and host Tesseract is absent | 94.59 s ML section |

Skipped/blocked checks and reason:

- Owner-operated parser-ceiling v3 rerun is pending against `a4dc60d0…`; it requires the existing signed-in Colab/private Drive context.
- OCR engine benchmark, recognizer training and the five-record locked test were deliberately not run.
- Repository wrapper remains non-zero because Node is `22.23.2` instead of `24.14.0`, npm is `10.9.8` instead of `10.9.0`, and host Tesseract is absent. The registered ML gate itself passes and Colab performs the exact Tesseract 5 bootstrap when needed.

## Known defects/blockers

| ID | Severity | Description | Impact | Safe fallback | Owner/input | Next action |
|---|---|---|---|---|---|---|
| PR17-V3-RERUN | Required evidence | No valid parser-ceiling v3 report exists after the compatibility stop | Corrected recipient and field outcome aggregates remain unavailable | Preserve v2 as historical evidence and make no corrected metric claim | Project owner/model steward | Run cells 1–4 only at `a4dc60d0…` and return the aggregate JSON/hash |
| PR17-TAMPERED-SLICE | Required evidence | No approved tampered-image validation slice exists | Robustness selection remains blocked | Keep the selected bundle experimental | Project owner/data steward | Govern suitable controlled edits before any robustness benchmark |

## Documentation updated

- `IMPLEMENTATION_STATUS.md`: corrected current state and immutable rerun SHA
- `requirements_traceability.csv`: recorded stopped v3 attempt and compatibility repair
- `DECISION_LOG.md`: unchanged; restoring the established ordered schema/scorer contract requires no product deviation
- `CHANGELOG.md`: recorded the compatibility regression and repair without a metric claim
- Evidence manifest/docs: no aggregate evidence JSON added because the failed run produced no valid report; this handoff records the safe failure boundary

## Git evidence

```text
follow-up starting SHA: 4eb0702ca8f858fdf6bfc6b267445e515a1560ab
immutable repair SHA: a4dc60d0d4ada44c7c5bad4fe3103f0964ead4eb
branch: codex/p17-ocr-benchmark
push output: pending at handoff authoring time
```

## Next exact task

Open `ml/notebooks/colab/06_benchmark_ocr.ipynb` from the pushed branch revision, confirm `TARGET_COMMIT` is `a4dc60d0d4ada44c7c5bad4fe3103f0964ead4eb`, and run cells 1–4 only against the unchanged private development archive. Do not run cells 5–7. Return only the aggregate cell-4 JSON/hash. Confirm record count 33, each field outcome total equals its scored denominator, recipient subtype totals equal the recipient denominator, all privacy/training/locked-test flags are false and the report self-hash verifies. Stop on any new exception, denominator drift or value/identifier leakage; do not start Stage 2 line reconstruction yet.
