# Codex Session Handoff

## Session identity

- Date/time: 2026-08-14, Africa/Lagos
- Phase/sub-phase: Logical PR16 permission-mapped friend OCR text pilot and group-safe split freeze
- Repository: `davidagyekum/momo-fraud-detection`
- Base branch: `codex/p16-ghana-screenshot-dataset`
- Base SHA: `93d3efb9f104ec3f688dc66a93ccf468973fc00e`
- Work branch: `codex/p16-ghana-screenshot-dataset`
- Final head SHA: reported after the session commit
- Pull request: not created in this session
- Push status: reported after the session commit
- Worktree status: reported after the session commit

## Scope completed

- Requirement IDs: `NFR-DATA-001`, logical PR16 Ghana private pilot/split controls
- Backlog task IDs: logical PR16 controlled-real minimum, de-identification, review and frozen group split
- Goal: import the newly source-mapped fraudulent screenshots, rerun readiness, freeze a leakage-safe text split if the gate passes and stop before Colab.
- Actual completed work:
  - verified exactly one JPEG in each of `friend-01` through `friend-21`;
  - visually confirmed fraud indicators and numeric senders across all 21;
  - found zero exact duplicates within the batch or against prior private images;
  - recorded one cross-batch perceptual match at distance six and excluded it from image use while retaining distinct text;
  - wrote private permission/participant/source records with one immutable group per friend;
  - stored 21 exact private transcripts with coarse full-image OCR fields and typed-placeholder de-identification;
  - rebuilt the screenshot OCR corpus to 63 rows and combined review to 418 approvals;
  - passed readiness at 34 controlled-real groups and 30 synthetic groups;
  - implemented deterministic label-stratified text split freezing and a test-excluding development loader;
  - froze authoritative private split v3 after preserving two superseded attempts that exposed avoidable class/record skew;
  - did not start Colab, fit a model, access the locked test or claim a metric.

## Changed files

| Path | Change | Why |
|---|---|---|
| `ml/src/momo_fdvs_ml/ghana_pipeline.py` | Add hash-bound text split freeze and locked development loader | Freeze train/validation/test by immutable source group without exposing test rows |
| `ml/tests/test_ghana_pipeline.py` | Add deterministic, sparse-class, tamper and fail-closed split tests | Prove group safety, minimums, class limits and manifest integrity |
| `docs/evidence/PR16_GHANA_PRIVATE_PILOT.json` | Record safe aggregate intake, review, readiness and split hashes/counts | Keep private values outside Git while making the run reconstructable |
| `DECISION_LOG.md` | Add ADR-034 | Document mapped consent, split policy, superseded attempts and sparse suspicious coverage |
| `IMPLEMENTATION_STATUS.md` | Update PR16 state and next stop point | Prevent accidental training or a false phase-complete claim |
| `requirements_traceability.csv` | Update `NFR-DATA-001` evidence | Trace the governed private split and remaining limitations |
| `CHANGELOG.md` | Record mapped batch and splitter | Maintain release history |

## Database/migrations

- Migration revision(s): none
- Upgrade tested from: not applicable
- Downgrade/rollback notes: private split manifests are immutable; superseding manifests preserve prior hashes rather than overwrite history
- Data backfill: none
- Schema/ERD update: none

## API/contract

- Endpoints added/changed: none
- OpenAPI/client regenerated: not applicable
- Breaking change: none
- Error/permission behaviour: splitter fails closed on weakened minimums, changed hashes, unapproved rows, cross-bucket groups, repository-local private paths and unlocked readiness.

## UI

- Screens/components: none
- States covered: not applicable
- Viewports/devices: not applicable
- Screenshot/evidence paths: raw screenshots remain private outside Git
- Accessibility notes: not applicable

## OCR/image/ML/verification

- Pipeline/model/rule/template versions: `ghana-private-pipeline-v1`, `ghana-private-text-frozen-split-v1`, assignment policy `label_stratified_source_group_hash_v2`
- Dataset/split/artifact hashes:
  - mapped private request: `ffe53019b70210d69fed0e2f0206d3e96d664f0de66d91b22f9998a9e6c83b87`
  - mapped private attestation: `5fb14101e885eea6b44547ab3dc528edf5a9f5318903fa9158862c4f211ed739`
  - mapped private index: `a8fc08f1b462353b93f50ab4c8640eecd8fc297ecc2508bcc91a0f84832271b2`
  - OCR de-identified CSV: `1a9901631eafba5b7cc4bfaffe9b6c77082ce77c94713317d8c9c12fbaaa4b1d`
  - reviewed CSV: `d7581471f55a475793976fed66a9f89c7b8107bfa744f6c92e700a3907f8fd0a`
  - readiness report: `046c715fc5d851f145f11cb6c39aa7a66c616b0109ebeab3f4238011255a831e`
  - authoritative split canonical hash: `3c2bd2e3727b62f0a61f01a7eebcbe49da7ed0ac124a8f765d471533d867d941`
  - authoritative split report: `b0aae3b9191f9d136bbe23c256fd8a3857797b165641b1f031bea2b503720727`
- Metrics actually measured: no model metrics; safe counts only — 418 records, 34 controlled groups, 30 synthetic groups, 362 train, 51 validation, five locked test.
- Limitations: controlled-real support spans 31 fraudulent, three genuine and one suspicious groups. Suspicious controlled-real validation/test evaluation is impossible without leakage. Image training is separately blocked because OCR-first originals have no approved image derivatives.
- No fabricated or unavailable evidence: no accuracy, macro F1, deployment, promotion or training claim.

## Security/privacy

- Access-control impact: private files remain on the restricted `E:` root; no private path or value is committed.
- Private-data impact: 21 consented originals, pseudonymous participant tokens, exact transcripts and full split records remain outside Git.
- Upload/storage impact: no raw image was copied into the repository and no image derivative was generated.
- Audit events: private permission attestation binds every folder to one participant/source group and retains superseded split identities.
- Security checks: exact/perceptual duplicate checks, typed-placeholder residual checks, secret/prohibited-artifact scan and manifest identity validation.

## Verification performed

| Command | Result | Counts/summary | Duration |
|---|---|---|---|
| `.venv\Scripts\python.exe -m ruff check ml/src/momo_fdvs_ml/ghana_pipeline.py ml/tests/test_ghana_pipeline.py` | PASS | no findings | focused run |
| `.venv\Scripts\python.exe -m mypy --strict ml/src/momo_fdvs_ml/ghana_pipeline.py` | PASS | strict typing | focused run |
| `.venv\Scripts\python.exe -m pytest ml/tests/test_ghana_pipeline.py -q --no-cov` | PASS | 146 tests | 5.66 s |
| `.venv\Scripts\python.exe scripts/verify_ml.py` | PASS | 538 tests; 90.09% branch-aware coverage; format, Ruff, strict mypy, governance, locks, notebooks and controlled-data checks pass | 132 s |
| `.venv\Scripts\python.exe scripts/check_secrets.py` | PASS | 532 candidate files scanned | 13.2 s |

Skipped/blocked checks and reason: no Colab execution was permitted; the owner explicitly required a stop before training.

## Known defects/blockers

| ID | Severity | Description | Impact | Safe fallback | Owner/input | Next action |
|---|---|---|---|---|---|---|
| PR16-CONTROLLED-SUSPICIOUS | High | Only one controlled-real suspicious group exists | No leakage-safe suspicious controlled validation/test slice | Declare limitation; use synthetic suspicious validation only as supplementary evidence | Project owner/data steward | Collect at least two more independently mapped suspicious groups before any strong three-class claim |
| PR16-IMAGE-PILOT | High | OCR-first screenshots have no approved image-training derivatives | Does not complete the blueprint image/tamper pilot | Keep all private originals image-ineligible | Project owner/data steward | Design separately consented controlled-clean screenshots and governed edits/masks |
| PR17-COLAB-STOP | Blocking by request | Training/benchmarking requires explicit owner confirmation | No PR17 execution yet | Preserve frozen split and locked test | Project owner | Confirm when ready to open Colab; use train/validation only |

## Documentation updated

- `IMPLEMENTATION_STATUS.md`: yes
- `requirements_traceability.csv`: yes
- `DECISION_LOG.md`: ADR-034
- `CHANGELOG.md`: yes
- Evidence manifest/docs: `docs/evidence/PR16_GHANA_PRIVATE_PILOT.json`

## Git evidence

```text
git status --short: reported after final verification/commit
git log --oneline 93d3efb9f104ec3f688dc66a93ccf468973fc00e..HEAD: reported after commit
push output: reported after push
```

## Next exact task

Stop here. After explicit owner confirmation, prepare PR17's OCR benchmark so it joins authoritative private split v3 assignments to the de-identified OCR corpus and exposes only train/validation through `load_private_text_development_records`. Do not load the five test rows, do not start Colab silently and do not claim controlled-real suspicious validation/test performance.
