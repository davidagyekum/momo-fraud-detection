# Codex Session Handoff

## Session identity

- Date: 2026-08-14, Africa/Lagos
- Phase: Logical PR16 consented friend screenshots with unrecoverable participant mapping
- Base SHA: `1179fbf7882cb1183d3e7e2509dff20d1daa18fb`
- Work branch: `codex/p16-ghana-screenshot-dataset`
- Final head/push state: reported after the session commit

## Scope completed

- Inspected 24 privately supplied files attributed by the project owner to 19 consenting friends.
- Identified two exact duplicates of previously registered fraudulent screenshots and retained the existing records rather than duplicating them.
- Privately registered the 22 newly unique screenshots as one conservative source group because the participant-to-file mapping cannot be reconstructed.
- Visually and independently reviewed all 22 new screenshots as genuine Ghana mobile-money transaction evidence.
- Added an OCR-first consented-screenshot path that creates no image derivative and never enables training.
- Preserved three near-duplicate image quarantines while allowing their distinct text to enter the de-identified text review layer.
- Stored manually verified transcripts with `coarse_full_image` localization, explicitly not field-localization ground truth.
- Rebuilt the private OCR layer from 20 to 42 rows and the combined reviewed corpus from 375 to 397 rows.
- Reran readiness: controlled-real groups increase only from 12 to 13; the required minimum remains 30.
- Did not enable records, freeze a split, train a model, access a locked test or claim a metric.

## Safe aggregate evidence

| Artifact | Result |
|---|---|
| Submitted friend batch | 24 files; 19 owner-attested consenting friends |
| Deduplication | 2 already registered exact duplicates; 22 newly unique |
| Conservative grouping | 1 partitionable group because friend-to-file mapping is unavailable |
| New label review | 22 genuine approvals; 0 exclusions; 0 training eligible |
| Image duplicate control | 3 near-duplicate templates remain image-quarantined |
| OCR text corpus | 42 rows; raw SHA-256 `4b734eb1a7064ec7d94acb70ab0e8e230b282a2ad316b83d16828e3d74b3cca4`; de-identified SHA-256 `a9298e91c92baf081503eaadf48dcdd55e5b946930f1b75260971dcc4aa67b19` |
| Combined review | 397 approvals; reviewed CSV SHA-256 `e8a3a2472543447d402109ccd5973582dfbc45321babc8f5d039ce9faf2c9eb5` |
| Label counts | 47 fraudulent; 319 genuine; 31 suspicious |
| Readiness | 13/30 controlled-real groups; 30/20 synthetic groups; `ready_to_freeze=false` |
| Readiness report | SHA-256 `38c268d7ba4dbb5430823857e2a3edfad2da630699b6dfa7682826832fd2d62d` |

## Security/privacy

- Raw screenshots, exact transcripts, permission records, private indexes and CSVs remain outside Git.
- The private permission attestation records 19 consenting friends but does not invent a participant-to-file mapping.
- Names, phone numbers, balances, references, timestamps and amounts are replaced by typed placeholders in the reviewed text.
- No image derivative was produced for this batch.
- Three near-duplicate image quarantines remain effective even though their text differs.

## Verification

| Command | Result | Summary |
|---|---|---|
| `.venv\\Scripts\\python.exe -m pytest ml/tests/test_ghana_pipeline.py -q --no-cov` | PASS | 133 tests |
| Ruff format/lint and strict mypy | PASS | Ghana pipeline and tests |
| `.venv\\Scripts\\python.exe scripts/verify_ml.py` | PASS | Format, Ruff, strict mypy, 525 tests, 90.05% branch-aware coverage, governance, locks, notebooks and controlled data |
| JSON/CSV parsing and `git diff --check` | PASS | Evidence and traceability valid |
| `.venv\\Scripts\\python.exe scripts/check_secrets.py` | PASS | 531 candidate files scanned |

## Remaining blocker

The batch adds useful genuine text diversity but only one leakage-safe group. PR16 remains blocked at 13/30 controlled-real groups. At least 17 additional permission-attested groups with preserved participant-to-file mapping are required, with suspicious examples the weakest class. All rows remain non-training and unsplit.

## Next exact task

Collect at least 17 additional controlled-real source groups with the source mapping preserved at intake. OCR-first review and de-identify them, rerun independent text review and readiness, and freeze a split only if the 30-group gate passes. Stop and notify the owner before any Google Colab training.
