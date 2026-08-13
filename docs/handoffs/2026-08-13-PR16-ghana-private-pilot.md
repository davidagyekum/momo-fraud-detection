# Codex Session Handoff

## Session identity

- Date/time: 2026-08-13, Africa/Lagos
- Phase/sub-phase: Logical PR16 private Ghana screenshot dataset — private pilot second review
- Repository: `davidagyekum/momo-fraud-detection`
- Base branch: `codex/p15-transaction-models`
- Base SHA: `9d77ed28fd8de4a92e91a8788ddde0d96305bcd8`
- Work branch: `codex/p16-ghana-screenshot-dataset`
- Final head SHA: reported in the final task handoff after commit
- Pull request: not created in this session
- Push status: reported in the final task response
- Worktree status: reported in the final task response

## Scope completed

- Requirement IDs: NFR-DATA-001, NFR-PRIV-001, NFR-AUD-001; logical PR16 blueprint
- Backlog task IDs: PR16 private consent, de-identification, duplicate, review, withdrawal and group-safe split controls
- Goal: establish a fail-closed private Ghana screenshot pipeline and validate it on the first consent-attested friend batch without leaking data or training a model
- Actual completed work: implemented the private pipeline/contracts/CLI/notebook, indexed and exported the owner's exact 2,654-message iMazing source to raw/de-identified private CSVs, quarantined/reviewed the initial online candidates and admitted ten friend-supplied files to a private internal-only pilot. Ten fraud, two genuine and one suspicious screenshot labels are approved; two ambiguous records are excluded. All 13 approved screenshots have exact private OCR truth and paired raw/de-identified rows. The owner corpus has 230 exact-deduplicated de-identified review rows across 167 template families. De-identification uses typed text placeholders, not image masking, and all image derivatives are excluded from training. No split or training occurred.

## Changed files

| Path | Change | Why |
|---|---|---|
| `ml/src/momo_fdvs_ml/ghana_pipeline.py` | Added private consent/intake, owner-message and OCR text-CSV export, de-identification, duplicate detection, exact OCR truth, online quarantine, review, withdrawal, controlled-edit and split controls | Provide the PR16 fail-closed text data path without training on masked images |
| `ml/src/momo_fdvs_ml/cli.py` | Registered safe private pipeline commands | Make owner/Colab operations reproducible |
| `ml/contracts/ghana-*.schema.json` | Added strict private request/index/split/online contracts | Reject malformed or unsafe private artifacts |
| `ml/notebooks/colab/05_build_ghana_screenshot_dataset.ipynb` | Added output-free bounded PR16 notebook | Prepare a restart-safe Colab handoff without training |
| `ml/tests/test_ghana_pipeline.py`, `ml/tests/test_cli.py`, `ml/tests/test_notebooks.py` | Added hostile input, privacy, duplicate, review, withdrawal, split, CLI and notebook tests | Prove the new controls and regression behaviour |
| `docs/evidence/PR16_GHANA_PRIVATE_PILOT.json` | Added safe aggregate pilot hashes/counts | Preserve evidence without private records |
| `IMPLEMENTATION_STATUS.md`, `requirements_traceability.csv`, `DECISION_LOG.md`, `CHANGELOG.md` | Recorded PR16 state, ADR-033 and remaining gates | Keep scope and evidence honest |

## Database/migrations

- Migration revision(s): none
- Upgrade tested from: not applicable
- Downgrade/rollback notes: not applicable
- Data backfill: none
- Schema/ERD update: none

## API/contract

- Endpoints added/changed: none
- OpenAPI/client regenerated: not applicable
- Breaking change: none; ML-private contracts are additive
- Error/permission behaviour: invalid IDs, paths, images, consent scope, de-identification state, transitions, duplicates and locked-test access fail closed

## UI

- Screens/components: none
- States covered: not applicable
- Viewports/devices: not applicable
- Screenshot/evidence paths: no private screenshot is committed or attached
- Accessibility notes: not applicable

## OCR/image/ML/verification

- Pipeline/model/rule/template versions: `ghana-private-pipeline-v1`; no model version created
- Dataset/split/artifact hashes: safe pilot evidence in `docs/evidence/PR16_GHANA_PRIVATE_PILOT.json`; no split/artifact exists
- Metrics actually measured: 13 label-approved screenshot records have exact private OCR truth and paired text rows with 0 exact sensitive-field leaks. The owner message source produced 2,654 raw rows, 230 deduplicated review rows, 167 template families and 0 residual direct-identifier pattern hits. Two ambiguous screenshots remain excluded, one exact screenshot duplicate remains quarantined and 0 records are training eligible.
- Limitations: permission is project-owner-attested; direct contributor forms are not supplied; online permission covers images 1-5 but not image 6; the 10-group QA set is below the 30 controlled-real/20 synthetic-clean pilot minimum and has weak genuine/suspicious coverage
- No fabricated or unavailable evidence: no split, model fit, accuracy, F1, deployment or promotion claim

## Security/privacy

- Access-control impact: private artifacts stay outside Git under the owner-controlled backup root
- Private-data impact: original screenshots, exact transcripts, field annotations and both CSV layers remain private; consent/permission references are pseudonymous. The de-identified CSV replaces declared values with typed placeholders, and image derivatives are excluded from training.
- Upload/storage impact: private only; all 13 text records remain blocked from training pending independent text review, minimum-group/class sufficiency and split freezing
- Audit events: private review history and withdrawal receipts are supported by the pipeline
- Security checks: hostile path/image validation, filename PII rejection, exact/perceptual duplicate quarantine, secret/prohibited artifact scan and registered ML gate

## Verification performed

| Command | Result | Counts/summary | Duration |
|---|---|---|---|
| `.venv\Scripts\python.exe scripts\verify_ml.py` | PASS | Ruff format/lint; strict mypy; 478 tests; 90.08% branch-aware coverage; governance/lock/notebook/data gates; no training | 106.6 s |
| Private second review and controlled crop pass | PASS | 16 working derivatives including 2 same-group crops; 13 labels approved; 2 ambiguous records excluded; 1 friend duplicate retained; 0 training eligible; 0 splits/training | Deterministic execution plus visual privacy review |
| Private transcription/field/mask QA | PASS WITH EXCLUSION | 13 reviewed; 12 accepted across 10 groups; 1 excluded for low utility; 0 metadata failures; 0 training eligible; 0 splits/training | Deterministic private QA plus repeated visual review |
| Private OCR text-corpus export | PASS, PENDING SECOND REVIEW | 13 raw rows; 13 de-identified rows; matching IDs; 0 exact sensitive-value leaks; 0 training eligible; masked images excluded | Deterministic private export and cross-check |
| Owner iMazing text-corpus export | PASS, PENDING SECOND REVIEW | 2,654 raw rows; 230 deduplicated de-identified rows; 167 template groups; 0 residual direct-identifier pattern hits; 0 training eligible | Deterministic private export and aggregate QA |

Skipped/blocked checks and reason: no model training, split freezing or locked-test evaluation is authorised at this stage. The secret/prohibited-artifact scan passed 526 candidates. Repository `--quick` is environment-blocked because the active Node/npm versions are not the pinned versions; `--security` additionally reports the already-documented unregistered security marker. Hosted GitHub Actions remain blocked by B-CI-001.

## Known defects/blockers

| ID | Severity | Description | Impact | Safe fallback | Owner/input | Next action |
|---|---|---|---|---|---|---|
| PR16-GHANA-PRIVATE | High | QA passed for 12 records across 10 groups, below the enforced 30 controlled-real/20 synthetic-clean pilot minimum; genuine/suspicious coverage is weak | Cannot freeze splits or train | Keep all eligibility false and continue only private preparation | Data steward/project owner | Add at least 20 controlled-real and 20 synthetic-clean groups, improve class coverage and repeat QA |
| PR16-ONLINE-RIGHTS | High | Image 6 remains unpermitted and the two ambiguous records are explicitly excluded | These sources cannot enter training | Preserve their private quarantine/exclusion state | Project owner/data steward | Do not use them unless new rights evidence and a fresh review are recorded |
| B-CI-001 | Medium | GitHub Actions account billing lock prevents runner allocation | Hosted CI unavailable | Preserve passing local gate evidence | Repository owner | Resolve the account lock and rerun CI |

## Documentation updated

- `IMPLEMENTATION_STATUS.md`: logical PR16 in progress and pilot aggregates recorded
- `requirements_traceability.csv`: NFR-DATA-001 linked to the new pipeline/contracts/tests/evidence
- `DECISION_LOG.md`: ADR-033 added
- `CHANGELOG.md`: PR16 foundation and pilot added
- Evidence manifest/docs: `docs/evidence/PR16_GHANA_PRIVATE_PILOT.json`

## Git evidence

```text
git status --short: recorded in final task report
git log --oneline 9d77ed28fd8de4a92e91a8788ddde0d96305bcd8..HEAD: recorded in final task report
push output: recorded in final task report
```

## Next exact task

Expand the QA-approved pilot from 10 to at least 30 controlled-real source groups and add 20 synthetic-clean groups, prioritising independent `GENUINE` and `SUSPICIOUS` coverage. Keep image 6 rights-blocked and the duplicate quarantined. Only after repeated QA should records be explicitly enabled and group-safe splits frozen; stop before Colab training.
