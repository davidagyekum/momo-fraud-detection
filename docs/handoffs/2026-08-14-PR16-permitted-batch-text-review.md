# Codex Session Handoff

## Session identity

- Date: 2026-08-14, Africa/Lagos
- Phase: Logical PR16 permission-attested online batch and text-split readiness
- Repository: `momo-fraud-detection`
- Base SHA: `4d0fa9ea365434929a0fc9d4df5baf8a68246968`
- Work branch: `codex/p16-ghana-screenshot-dataset`
- Final head/push state: reported after the session commit

## Scope completed

- Recorded owner permission for exactly 11 private online-image candidates under the internal-model-development scope.
- Performed OCR-first content review without generating masked image derivatives.
- Approved seven Ghana fraudulent-message examples and excluded four candidates as authenticity-ambiguous or outside the Ghana domain.
- Conservatively bound all 11 candidates to one source group because their original independence could not be proven.
- Added independently reviewed, manually verified and de-identified OCR truth for the seven approvals.
- Rejected the first synthetic pilot because duplicate texts crossed groups and a payment template used the wrong preposition; generated and independently reviewed a corrected 90-row, 30-group corpus with 90 unique texts.
- Combined 265 owner rows, 20 screenshot-OCR rows and 90 synthetic rows into a 375-row reviewed, non-training corpus.
- Added an executable readiness assessment. It passes the synthetic 30/20 group gate but blocks split freezing at 12/30 controlled-real groups.
- Did not enable records, freeze a split, train a model, access a locked test or claim a metric.

## Changed files

| Path | Change |
|---|---|
| `ml/src/momo_fdvs_ml/ghana_pipeline.py` | Add OCR-first review, corrected synthetic generation and safe split-readiness assessment. |
| `ml/tests/test_ghana_pipeline.py` | Cover permission, no-derivative, uniqueness, review and readiness invariants. |
| `docs/evidence/PR16_GHANA_PRIVATE_PILOT.json` | Record safe aggregate counts and hashes only. |
| `IMPLEMENTATION_STATUS.md` | Update PR16 state, blocker and next task. |
| `requirements_traceability.csv` | Update the private-data governance evidence. |
| `DECISION_LOG.md`, `CHANGELOG.md` | Record the OCR-first and corrected-synthetic decisions. |

## OCR/image/ML/verification

- Permission-attested batch: 11 candidates; 7 approved; 4 excluded; one conservative source group.
- Screenshot OCR layer: 20 reviewed rows total; raw CSV SHA-256 `8865fb8f07b636a4ab574f7092fc07cfe24d445377f2393cb1cdbbaa369ca7b6`; de-identified CSV SHA-256 `0f93eee9bc4c39d97857b78382d41facba18a3fb5311357a8d9b3feced666bc5`.
- Corrected synthetic corpus: 90 rows, 30 groups, 90 unique texts, balanced 30/30/30; corpus SHA-256 `25a77abe73f1cd008560331f738186ca3cd9388a20296a5bec315730dabec668`.
- Combined review: 375 approvals, zero exclusions; 47 fraudulent, 297 genuine and 31 suspicious; reviewed CSV SHA-256 `2364609c7d370943e750dbdf0050c008bb80c94f54c6a4fb904559b8c8af5e73`.
- Readiness report SHA-256 `5ec04d3d6239e76d5b68bace0ac20b4d4cef6d1ccd092254413ddae66732056f`; `ready_to_freeze=false`.
- No private values or artifacts are committed; repository evidence contains safe aggregates and cryptographic identities only.

## Verification performed

| Command | Result | Counts/summary |
|---|---|---|
| `.venv\\Scripts\\python.exe -m pytest ml/tests/test_ghana_pipeline.py -q --no-cov` | PASS | 120 tests |
| `.venv\\Scripts\\python.exe scripts/verify_ml.py` | PASS | Format, Ruff, strict mypy, 519 tests, 90.11% branch-aware coverage, governance, locks, notebooks and controlled data |
| `.venv\\Scripts\\python.exe scripts/check_secrets.py` | PASS | 530 candidate files scanned |
| JSON/CSV parsing and `git diff --check` | PASS | Evidence JSON and 98-row traceability CSV valid; no whitespace errors |

## Known blocker

| ID | Description | Safe fallback | Next action |
|---|---|---|---|
| PR16-GHANA-PRIVATE | Controlled-real groups are 12 of the required 30. Owner records represent one participant lineage and cannot substitute for independent evaluation groups. | Keep every record non-training and Ghana-private disabled. | Obtain at least 18 additional permission-attested controlled-real groups, especially genuine/suspicious examples; rerun review/readiness, freeze a leakage-safe split only if it passes, then stop for owner confirmation before Colab training. |

## Next exact task

Collect and privately register at least 18 additional independently sourced, permission-attested controlled-real groups with stronger genuine and suspicious coverage. Run OCR-first review, de-identification and independent second review, then rerun `assess_private_text_split_readiness`. Do not freeze a split unless the report passes, and do not begin Google Colab training without notifying the owner.
