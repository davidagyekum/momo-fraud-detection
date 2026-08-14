# Codex Session Handoff

## Session identity

- Date/time: 2026-08-14, Africa/Lagos
- Phase/sub-phase: Logical PR17 OCR validation repair
- Repository: `davidagyekum/momo-fraud-detection`
- Base branch: `main`
- Base SHA: `b1284e37f8b4e6a38587fee68a44ed8a74203323`
- Session starting SHA: `e58a4873b5e58c8345efd77790acc665f26d88e1`
- Work branch: `codex/p17-ocr-benchmark`
- Repair implementation head SHA: `928f0cdae986428b747bd1839bb0a75d7d02404b`; the documentation-only closure head is reported in the final response
- Pull request: existing PR17 branch; no new pull request created in this repair session
- Push status: repair implementation commit pushed successfully to `origin/codex/p17-ocr-benchmark`
- Worktree status: normal repository worktree; preserve for the owner-operated Colab rerun

## Scope completed

- Requirement IDs: FR-OCR-001, FR-OCR-002, FR-OCR-003, FR-ML-005, FR-ML-006, NFR-ACC-001, NFR-AUD-001, NFR-DATA-001, NFR-PRIV-001
- Backlog task IDs: logical PR17 OCR benchmark/parser repair
- Goal: prevent incomplete or incompatible OCR validation results from being selected and make all three required engines reproducible on the supported Colab image.
- Actual completed work: versioned the config/report/selection contracts; required complete record coverage and all required engines; enforced Tesseract major 5; disabled PaddleOCR's failing CPU MKLDNN path; added an exact-source Tesseract 5.5.3 Colab bootstrap; updated the output-free notebook; preserved the failed run as non-promotable evidence; and added regression coverage.

## Changed files

| Path | Change | Why |
|---|---|---|
| `ml/src/momo_fdvs_ml/ocr_benchmark.py` | Added v2 coverage/version gates, stable adapter failures and coverage-bound selection bundles | Prevent partial results from becoming apparent winners or replayable current evidence |
| `ml/src/momo_fdvs_ml/colab_ocr.py` | Added exact official Tesseract 5 bootstrap | Jammy apt provides unsupported Tesseract 4.1.1 |
| `ml/configs/ocr_benchmark_v2.json` | Replaced v1 config and pinned complete-engine policy/Paddle options | Make the repair an explicit contract revision |
| `ml/notebooks/colab/06_benchmark_ocr.ipynb` | Wired safe bootstrap and v2 config | Reproduce the repaired validation run in Colab |
| `ml/tests/test_ocr_benchmark.py`, `ml/tests/test_colab_ocr.py` | Added red/green selection, adapter and bootstrap regressions | Prove fail-closed behavior and maintain the coverage gate |
| `docs/evidence/*`, `IMPLEMENTATION_STATUS.md`, `requirements_traceability.csv`, `DECISION_LOG.md`, `CHANGELOG.md`, `ml/README.md` | Recorded the failed run, compatibility decision, verification and next action | Preserve honest traceability without private data or accuracy claims |

## Database/migrations

- Migration revision(s): none
- Upgrade tested from: not applicable
- Downgrade/rollback notes: not applicable
- Data backfill: none
- Schema/ERD update: none

## API/contract

- Endpoints added/changed: none
- OpenAPI/client regenerated: not applicable
- Breaking change: private PR17 OCR config/report/selected-bundle schemas move to v2; the verified private development-bundle v1 identity remains compatible and unchanged
- Error/permission behaviour: engine/runtime/preprocessing failures use stable reason codes; incomplete comparisons fail closed before selection

## UI

- Screens/components: none
- States covered: not applicable
- Viewports/devices: not applicable
- Screenshot/evidence paths: not applicable
- Accessibility notes: no UI change

## OCR/image/ML/verification

- Pipeline/model/rule/template versions: `ocr-benchmark-config-v2`, `ghana-ocr-benchmark-report-v2`, `ghana-ocr-selected-bundle-v2`; private development bundle remains `ghana-ocr-development-bundle-v1`; Tesseract source 5.5.3 at `db0ec62f81b0737fbbe184d8fea40af5738f8eef`.
- Dataset/split/artifact hashes: development manifest `1ba8c58e1c29b77a46ba3cc54da7843dd84f090fdb2e731704091162d556d644`; portable private archive `8a7f4b58e20569775dc237e5e4fefba78e2bc5aa8c40d5ee41dd893d495ea9b9`; failed report `1682dae402e5021d32c9f09314abe0ac6e42361a8a347de68abf88430eab329a`; historical invalid experimental bundle `019e8e91d59b8f07302934e7fd61c671da8de06a9c00488e21ff83dd68cff162`.
- Metrics actually measured: the historical failed run processed 33 clean validation records but was incomplete—EasyOCR and Tesseract succeeded on only 8/33, PaddleOCR on 0/33, and every release gate was false. These values are failure diagnostics, not accuracy or release evidence.
- Limitations: the repaired notebook has not yet been rerun in Colab; no approved tampered-image validation slice exists; no locked-test evaluation or recognizer training occurred.
- No fabricated or unavailable evidence: no model winner, accuracy, validated bundle, promotion or production-readiness claim is made.

## Security/privacy

- Access-control impact: none
- Private-data impact: no private image, OCR truth, raw text or private path was committed; the synthetic Paddle diagnostic used a generated non-private image
- Upload/storage impact: unchanged restricted Drive archive and model-weight cache boundary
- Audit events: failed validation and repair recorded in the public redacted evidence document and ADR-036
- Security checks: final secret/prohibited-artifact scan passed 550 candidate files

## Verification performed

| Command | Result | Counts/summary | Duration |
|---|---|---|---|
| `.venv\\Scripts\\python.exe -m pytest ml/tests/test_ocr_benchmark.py::test_complete_full_report_creates_coverage_bound_experimental_bundle --no-cov -q` before implementation | Expected RED | 1 failed: selected bundle lacked source report schema binding | 3.5 s |
| Same focused regression after implementation | PASS | 1 passed | 3.7 s |
| `.venv\\Scripts\\python.exe -m pytest ml/tests/test_ocr_benchmark.py ml/tests/test_colab_ocr.py ml/tests/test_notebooks.py --no-cov -q` | PASS | 49 passed | 6.0 s |
| `.venv\\Scripts\\python.exe scripts\\verify_ml.py` | PASS | 614 tests; 90.05% branch-aware coverage; format, Ruff, strict mypy, governance, lock, notebook and controlled-data checks pass | 122.3 s |
| `.venv\\Scripts\\python.exe scripts\\verify.py --ml` | ML/secret PASS; wrapper non-zero at known doctor | 614 tests at 90.05%; 550 candidates at that wrapper run; Node/npm pin mismatch and missing host Tesseract remain | 115.2 s |
| `.venv\\Scripts\\python.exe scripts\\check_secrets.py` | PASS | 550 candidate files on the committed repair tree | 3.9 s |

Skipped/blocked checks and reason: live Colab validation is intentionally pending the pushed immutable commit. Local Tesseract execution is not applicable because the repair targets the controlled Colab bootstrap. Hosted GitHub jobs cannot start while the repository owner's Actions account is locked by billing.

## Known defects/blockers

| ID | Severity | Description | Impact | Safe fallback | Owner/input | Next action |
|---|---|---|---|---|---|---|
| PR17-COLAB-RERUN | Required evidence | Repaired v2 benchmark has not run in Colab | No current comparison or selectable bundle exists | Keep historical bundle invalid/non-promotable | Project owner | Run notebook 06 from the pushed commit, validation only |
| PR17-TAMPERED-SLICE | Medium | No approved governed tampered-image validation slice | Robustness gate cannot pass | Any future bundle remains experimental | Project owner/data steward | Create grouped consented derivatives, then rerun validation |
| TOOLCHAIN-HOST | Low for this ML repair | Host Node/npm differ from pins and local Tesseract is absent | Repository wrapper returns non-zero although ML gate passes | Use pinned frontend runtime separately and Colab Tesseract bootstrap | Environment owner | Activate pinned Node/npm if running full-repo gates |
| CI-BILLING | External | Hosted Actions jobs cannot start | No hosted corroboration | Preserve local evidence | Repository owner | Resolve GitHub Actions billing lock |

## Documentation updated

- `IMPLEMENTATION_STATUS.md`: failed validation, repair, verification and next action
- `requirements_traceability.csv`: PR17 v2 coverage/version/bootstrap evidence
- `DECISION_LOG.md`: ADR-036 compatibility and reproducibility decision
- `CHANGELOG.md`: failed-run diagnosis and repair
- Evidence manifest/docs: v2 public redacted evidence and updated SHA-256

## Git evidence

```text
session starting SHA: e58a4873b5e58c8345efd77790acc665f26d88e1
branch: codex/p17-ocr-benchmark
git status --short before commit: modified/new PR17 repair code, tests and documentation only
push output: e58a487..928f0cd  codex/p17-ocr-benchmark -> codex/p17-ocr-benchmark
```

## Next exact task

Open `ml/notebooks/colab/06_benchmark_ocr.ipynb` at pushed immutable repair commit `928f0cdae986428b747bd1839bb0a75d7d02404b`, set `TARGET_COMMIT` to that SHA, keep `RUN_BENCHMARK=True`, execute from the first cell, obey an explicit runtime-restart gate if shown, and run only the 33 development validation records. Stop before any locked-test or training action and return the safe screen/full report summary.
