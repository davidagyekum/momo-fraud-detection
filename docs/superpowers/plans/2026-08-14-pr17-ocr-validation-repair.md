# PR17 OCR Validation Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the PR17 Colab OCR benchmark compare only complete, version-compatible validation runs and run PaddleOCR and Tesseract 5 reproducibly on the supported Colab image.

**Architecture:** Keep all raw screenshots and OCR truth in the existing private development bundle. Strengthen the benchmark report contract so coverage and required runtime versions are explicit selection gates, fix PaddleOCR at its supported constructor boundary, and add a standard-library-only Colab bootstrap that builds an exact official Tesseract 5 commit when Ubuntu Jammy provides only Tesseract 4.

**Tech Stack:** Python 3.12, pytest, Pillow/NumPy, pytesseract, EasyOCR 1.7.2, PaddleOCR 3.7.0/PaddlePaddle 3.3.1, Google Colab, CMake, Git.

## Global Constraints

- Do not load or package the five locked-test records.
- Do not persist raw OCR text, truth values, images, exception strings, or private paths in Git or redacted reports.
- Require all validation records for any configuration that competes in screen or full selection.
- Require Tesseract major version 5; version 4 evidence is retained only as a failed-run record.
- Use the official Tesseract repository at exact commit `db0ec62f81b0737fbbe184d8fea40af5738f8eef` (`5.5.3`), not an unverified PPA.
- Keep recognizer training, locked-test evaluation, model promotion, and tampered-slice claims disabled.

---

### Task 1: Complete-coverage and runtime-version selection contract

**Files:**
- Modify: `ml/src/momo_fdvs_ml/ocr_benchmark.py`
- Replace: `ml/configs/ocr_benchmark_v1.json` with `ml/configs/ocr_benchmark_v2.json`
- Test: `ml/tests/test_ocr_benchmark.py`

**Interfaces:**
- Consumes: `run_ocr_validation_benchmark(...)`, `select_engine_finalists(...)`, `select_ocr_configuration(...)`.
- Produces: report configuration fields `record_coverage`, `coverage_complete`; engine status field `required_version_satisfied`; report field `selection_eligible` that is true only for a complete full comparison.

- [x] **Step 1: Write failing coverage tests**

Add tests proving a high-scoring partial configuration cannot become a finalist, a full report with partial coverage cannot produce a selected bundle, and a Tesseract 4 result is categorized as `OCR_ENGINE_VERSION_UNSUPPORTED`.

- [x] **Step 2: Run the focused tests and verify RED**

Run: `.venv\Scripts\python.exe -m pytest ml/tests/test_ocr_benchmark.py -k "coverage or version" -q --no-cov`

Expected: failures show partial candidates remain selectable and Tesseract 4 remains measured.

- [x] **Step 3: Implement the minimal report and selection gates**

Calculate coverage from literal successful/required counts, admit only complete candidates, require each configured engine to have a complete compatible run, and emit only stable reason codes.

- [x] **Step 4: Run the focused tests and verify GREEN**

Run: `.venv\Scripts\python.exe -m pytest ml/tests/test_ocr_benchmark.py -q --no-cov`

Expected: all OCR benchmark tests pass.

### Task 2: PaddleOCR oneDNN compatibility repair

**Files:**
- Modify: `ml/src/momo_fdvs_ml/ocr_benchmark.py`
- Modify: `ml/configs/ocr_benchmark_v2.json`
- Test: `ml/tests/test_ocr_benchmark.py`

**Interfaces:**
- Consumes: `PaddleOCRAdapter(device="cpu")`.
- Produces: a pipeline constructed with `ocr_version="PP-OCRv6"` and `enable_mkldnn=False`, while injected test pipelines keep the same adapter API.

- [x] **Step 1: Write the failing constructor-option test**

Patch the import boundary with a complete fake PaddleOCR module and assert the adapter passes `enable_mkldnn=False` and `ocr_version="PP-OCRv6"`.

- [x] **Step 2: Run the test and verify RED**

Run: `.venv\Scripts\python.exe -m pytest ml/tests/test_ocr_benchmark.py -k "mkldnn" -q --no-cov`

Expected: the fake constructor receives neither required option.

- [x] **Step 3: Implement the supported constructor options and stable adapter failures**

Pass the two options at construction and distinguish unavailable, inference, result-count, result-schema, and token-alignment failures without persisting exception text.

- [x] **Step 4: Run adapter and benchmark tests and verify GREEN**

Run: `.venv\Scripts\python.exe -m pytest ml/tests/test_ocr_benchmark.py -q --no-cov`

Expected: all tests pass.

### Task 3: Reproducible Tesseract 5 Colab bootstrap

**Files:**
- Create: `ml/src/momo_fdvs_ml/colab_ocr.py`
- Create: `ml/tests/test_colab_ocr.py`
- Modify: `ml/notebooks/colab/06_benchmark_ocr.ipynb`

**Interfaces:**
- Produces: `ensure_tesseract5(source_root: Path) -> dict[str, object]`, returning the exact version, source commit, whether a build occurred, and a safe install status.
- Consumes: the notebook VM root; no Drive private-data path.

- [x] **Step 1: Write failing bootstrap tests**

Cover the already-compatible fast path, the Tesseract 4 build path, exact source-commit verification, tessdata discovery, and failure when the installed binary is not major 5.

- [x] **Step 2: Run the tests and verify RED**

Run: `.venv\Scripts\python.exe -m pytest ml/tests/test_colab_ocr.py -q --no-cov`

Expected: import failure because `colab_ocr` does not exist.

- [x] **Step 3: Implement the minimal bootstrap**

Install Jammy build prerequisites, fetch only the exact official commit, configure without training tools/tests, build with two jobs, install under `/usr/local`, set an existing English tessdata directory, and verify `tesseract --version` reports major 5.

- [x] **Step 4: Wire the notebook and verify notebook policy**

Replace the Jammy `apt-get install tesseract-ocr` success boolean with the safe bootstrap report and assert its major version is 5 before adapter construction.

Run: `.venv\Scripts\python.exe -m pytest ml/tests/test_colab_ocr.py ml/tests/test_notebooks.py -q --no-cov`

Expected: all tests pass and the notebook remains output-free.

### Task 4: Failed-run evidence and phase documentation

**Files:**
- Modify: `docs/evidence/PR17_OCR_BENCHMARK_PREPARATION.json`
- Modify: `docs/evidence/EVIDENCE_MANIFEST.csv`
- Modify: `IMPLEMENTATION_STATUS.md`
- Modify: `requirements_traceability.csv`
- Modify: `DECISION_LOG.md`
- Modify: `CHANGELOG.md`
- Create: `docs/handoffs/2026-08-14-PR17-ocr-validation-repair.md`

**Interfaces:**
- Consumes: failed report SHA `1682dae402e5021d32c9f09314abe0ac6e42361a8a347de68abf88430eab329a` and failed selected-bundle SHA `019e8e91d59b8f07302934e7fd61c671da8de06a9c00488e21ff83dd68cff162`.
- Produces: a public redacted audit record that explicitly says the run was experimental, non-promotable, incomplete, and did not access locked test or train a recognizer.

- [x] **Step 1: Record the failed run without accuracy claims**

Document 33 validation records, EasyOCR/Tesseract 8 successes and 25 unavailable field crops, PaddleOCR 0/33, Tesseract 4.1.1, all release gates false, and the confirmed Paddle oneDNN cause.

- [x] **Step 2: Record the compatibility decision**

Version the private PR17 report/selection contract so old partial-coverage bundles cannot be replayed as current evidence.

- [x] **Step 3: Complete the handoff**

State the exact next Colab action: open the notebook at the new immutable repair commit, restart if requested by dependency bootstrap, run validation only, and stop before locked test.

### Task 5: Verification and publication

**Files:**
- Verify all modified files.

**Interfaces:**
- Produces: a pushed `codex/p17-ocr-benchmark` repair commit and exact local evidence.

- [x] **Step 1: Run focused tests**

Run: `.venv\Scripts\python.exe -m pytest ml/tests/test_ocr_benchmark.py ml/tests/test_colab_ocr.py -q --no-cov`

- [x] **Step 2: Run the registered ML gate**

Run: `.venv\Scripts\python.exe scripts/verify_ml.py`

- [x] **Step 3: Run repository verification and secret scan**

Run: `.venv\Scripts\python.exe scripts/verify.py --ml`

Record any already-known doctor-only blocker separately from the ML result.

- [ ] **Step 4: Inspect state and publish**

Run `git diff --check`, inspect `git diff` and `git status`, commit with `fix(ml): repair PR17 OCR validation`, and push `codex/p17-ocr-benchmark` without force.
