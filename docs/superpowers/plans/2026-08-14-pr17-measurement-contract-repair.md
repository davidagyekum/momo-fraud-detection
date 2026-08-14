# PR17 Measurement Contract Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make parser exact scoring, availability classification, warning attribution, and recipient subtype reporting use one explicit name-or-wallet comparison contract without changing parser behavior.

**Architecture:** Add an immutable in-memory `FieldComparison` at the OCR benchmark boundary. Build each scored field comparison once, retain `score_parser_result()` as a compatibility projection, and make the aggregate-only parser-ceiling diagnostic consume the same comparison for outcomes and warnings. Advance only the parser-ceiling report schema to v3; do not change the OCR parser, benchmark selector, preprocessing, private split, or release gates.

**Tech Stack:** Python 3.12, frozen dataclasses, pytest, Ruff, strict mypy, repository ML verification scripts.

## Global Constraints

- Work only on `codex/p17-ocr-benchmark` from baseline `af51ed05794bf300c58441684d87b5f5b9eabdf2`.
- Do not access the five locked-test records, alter source-group splits, initialize OCR engines, train a model, or change parser regex behavior.
- Do not persist transcripts, normalized truth/observed values, record IDs, names, wallets, references, or amounts.
- Preserve name-first scoring when both recipient truth fields exist, but expose the secondary-truth condition as an aggregate count.
- Recipient subtype totals must equal the recipient truth-scored denominator; unexpected denominator drift is a stop condition.
- Owner-operated validation on the 33 private validation transcripts occurs only after the code commit and is outside this implementation pass.

---

### Task 1: Add failing measurement-contract regressions

**Files:**
- Modify: `ml/tests/test_ocr_benchmark.py`
- Test: `ml/tests/test_ocr_benchmark.py`

**Interfaces:**
- Consumes: existing `ParserResult`, `ParsedField`, `score_parser_result()`, and `run_ocr_parser_ceiling_diagnostic()`.
- Produces: expectations for `compare_parser_result(parser, truth) -> dict[str, FieldComparison | None]` and v3 aggregate report fields.

- [ ] **Step 1: Add direct comparison tests with fictional values**

  Add synthetic parser-result fixtures covering wallet exact, wallet mismatch with unavailable name, name truth, both truth fields, absent truth, and conflicting duplicate truth. Assert literal aggregate/truth/observed field names, availability, warnings, match state, subtype, and name-first secondary-truth behavior.

- [ ] **Step 2: Add diagnostic regression tests**

  Patch only the deterministic parser boundary with complete `ParserResult` objects so a wallet-truth record proves that outcome and warning aggregation use `recipient_wallet`. Assert the v3 schema, subtype counts, secondary-truth count, observed-field warning map, denominator equality, privacy flags, and absence of all fictional values and record IDs from serialized output.

- [ ] **Step 3: Run the focused tests and capture RED**

  Run:

  ```powershell
  .\.venv\Scripts\python.exe -m pytest ml/tests/test_ocr_benchmark.py -q --no-cov
  ```

  Expected: failures because `compare_parser_result` and v3 report fields do not exist and the current diagnostic classifies wallet truth through `parser.fields["recipient"]`.

### Task 2: Implement one comparison contract

**Files:**
- Modify: `ml/src/momo_fdvs_ml/ocr_benchmark.py`
- Test: `ml/tests/test_ocr_benchmark.py`

**Interfaces:**
- Produces: frozen `FieldComparison` with `aggregate_field`, `truth_field`, `observed_field`, private normalized values, `matched`, `available`, `warnings`, optional safe `truth_subtype`, and `secondary_truth_present`.
- Produces: `compare_parser_result(parser: ParserResult, truth: Mapping[str, object]) -> dict[str, FieldComparison | None]`.
- Preserves: `score_parser_result(parser, truth) -> dict[str, bool | None]`.

- [ ] **Step 1: Fail closed on conflicting duplicate truth**

  Change `_truth_fields()` so repeated identical normalized values remain accepted while conflicting non-empty normalized values raise `OCRBenchmarkError` without embedding the private value in the exception.

- [ ] **Step 2: Add the immutable comparison object and builder**

  Build ordinary fields against their same-named parser output. Build aggregate recipient against `recipient` for name truth or `recipient_wallet` for wallet truth. Raise `OCRBenchmarkError` with a bounded observed-field name if the required parser field is absent.

- [ ] **Step 3: Preserve the scoring API as a projection**

  Implement `score_parser_result()` solely from `compare_parser_result()` so no caller observes a score-contract change.

- [ ] **Step 4: Run direct focused tests and capture GREEN**

  Run the smallest new test selection, then the full benchmark test file. Expected: all tests pass with no parser behavior change.

### Task 3: Upgrade the redacted parser-ceiling aggregate to v3

**Files:**
- Modify: `ml/src/momo_fdvs_ml/ocr_benchmark.py`
- Modify: `ml/tests/test_ocr_benchmark.py`

**Interfaces:**
- Produces report schema `ghana-ocr-parser-ceiling-report-v3`.
- Adds `recipient_truth_subtype_counts`, `recipient_secondary_truth_present_count`, and `parser_warning_counts_by_observed_field`.
- Preserves the flat `parser_warning_counts` compatibility aggregate unless repository tests or consumers prove it unsafe.

- [ ] **Step 1: Consume comparisons in the diagnostic loop**

  Derive exact/mismatch/unavailable from `matched` and `available`; derive warnings from `comparison.warnings`; aggregate only allowlisted field/subtype names and canonical warning codes.

- [ ] **Step 2: Enforce aggregate invariants before writing**

  Verify each field outcome total equals its scored count and recipient subtype totals equal the recipient scored count. Raise a bounded `OCRBenchmarkError` before `_write_json()` on invariant failure.

- [ ] **Step 3: Emit only safe v3 aggregate fields**

  Keep all comparison values in memory. Serialize counts, versions, hashes, rates, and the five explicit false privacy/training/locked-test flags only.

- [ ] **Step 4: Run focused and full tests**

  Run:

  ```powershell
  .\.venv\Scripts\python.exe -m pytest ml/tests/test_ocr_benchmark.py -q --no-cov
  .\.venv\Scripts\python.exe -m pytest ml/tests/test_ocr_parser.py -q --no-cov
  ```

  Expected: pass, including literal denominator and leakage assertions.

### Task 4: Verify, document, commit, and push Stage 1

**Files:**
- Modify: `IMPLEMENTATION_STATUS.md`
- Modify: `requirements_traceability.csv` only if an existing PR17 row requires status/evidence refresh.
- Modify: `CHANGELOG.md`
- Modify: `DECISION_LOG.md` only if implementation requires a source-of-truth deviation.
- Create: `docs/handoffs/2026-08-14-PR17-measurement-contract-repair.md`

**Interfaces:**
- Produces: a coherent Stage 1 commit and exact handoff for the owner-operated parser-ceiling v3 run.

- [ ] **Step 1: Run the phase quality gates**

  Run:

  ```powershell
  .\.venv\Scripts\python.exe -m ruff format --check ml/src ml/tests
  .\.venv\Scripts\python.exe -m ruff check ml/src ml/tests
  .\.venv\Scripts\python.exe -m mypy ml/src/momo_fdvs_ml
  .\.venv\Scripts\python.exe scripts/verify_ml.py
  .\.venv\Scripts\python.exe scripts/check_secrets.py
  ```

  Record exact outputs, counts, durations, branch, baseline SHA, and privacy boundaries. Do not claim the private denominator of 32 is verified until the owner-operated run occurs.

- [ ] **Step 2: Inspect repository and migration state**

  Run `git diff --check`, `git diff`, `git status --short --branch`, and the repository's migration-state check if it is part of `scripts/verify_ml.py`. Confirm no private artifact or package extraction entered the worktree.

- [ ] **Step 3: Update handoff documentation**

  Record RED and GREEN evidence, changed files, no database/API/parser behavior change, no training, no locked-test access, and the exact next owner-operated v3 validation command/runbook boundary.

- [ ] **Step 4: Commit and push**

  Commit as `fix(ocr): align recipient comparison contract`, push `codex/p17-ocr-benchmark`, and report the exact base SHA, head SHA, branch, commands, results, and any blocked hosted CI state.

