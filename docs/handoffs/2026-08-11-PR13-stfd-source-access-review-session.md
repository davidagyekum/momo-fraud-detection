# Codex Session Handoff

## Session identity

- Date/time: 2026-08-11, Africa/Lagos
- Phase/sub-phase: Logical PR13 STFD source/access metadata review
- Repository: `davidagyekum/momo-fraud-detection`
- Base branch: `main`
- Base SHA: `000bc65983d242cac8a8806a0cb116373bbcb4c2`
- Work branch: `codex/p13-dataset-acquisition-validation`
- Final implementation head SHA before this handoff: `7b12b9f6a7572bbf569c707ac057ec541ed92b10`
- Pull request: not opened in this session
- Push status: pending final handoff push
- Worktree status: handoff documentation pending its final commit

## Scope completed

- Requirement IDs: NFR-DATA-001, NFR-AUD-001, FR-ML-005, FR-ML-006, logical PR13
- Backlog task IDs: reconciled logical PR13 STFD access/version/layout gate
- Goal: establish STFD's authoritative source, terms, exact version/archive identity and documented layout without assuming access or downloading protected bytes.
- Actual completed work: froze the current Hugging Face revision and archive LFS identity, reconciled the CC BY metadata with the stricter academic/password/no-redistribution notice, documented image/mask pairing, and retained explicit access/grouping blockers.

## Exact metadata evidence

| Field | Verified value |
|---|---|
| Canonical source | `huggingface:Zegkim/STFD` |
| Repository revision | `9edebed2109052a77e9a5581c2ea7ce33d685da0` |
| Repository last modified | `2026-03-18T03:15:17Z` |
| Archive | `STFD_ICASSP2023.zip` |
| Archive size | 2,941,753,426 bytes |
| Hugging Face LFS SHA-256 | `6159a6611caaf71f40acf181b404af5a5dd0547f3d2d8d819bb640e3fb5de18c` |
| Repository state at review | public, ungated; archive encrypted |
| Permission state | `access_request_required` |
| Acquisition state | `not_acquired`; disabled/non-promotable |

The Hugging Face card documents five tampering categories, each with `tamper/` and same-filename `masks/` directories; binary masks use values 0 and 255. It does not document a source/editing/donor lineage key suitable for leakage-safe splitting.

## Decision and safety boundary

- Hugging Face metadata labels STFD CC BY 4.0.
- The current card additionally limits use to academic research, requests an academic/institutional email application for extraction access and asks users not to redistribute images.
- The official STFL-Net repository publicly displays an extraction password, but ADR-029 follows the stricter dataset-card instruction and does not treat that password as project-specific written approval.
- No password, email correspondence, archive, image, mask, filename inventory or sample was committed.
- No acquisition, archive opening, split, locked-test access, fitting, evaluation or promotion occurred.

## Changed files

| Area | Change | Why |
|---|---|---|
| `data/registry.yaml` | Froze exact STFD revision, verified restricted licence scope and retained access-required/not-acquired state | Separate known metadata from missing permission |
| `data/acquisition_specs/stfd.json` | Added exact archive identity, five category names, pairing rule and binary-mask semantics; status now pending access/group mapping | Prepare future identity validation without opening bytes |
| `data/cards/stfd.md` and runbook | Recorded academic/no-redistribution conditions, prohibited uses and unresolved lineage | Give the operator a fail-closed path |
| `docs/evidence/PR13_STFD_SOURCE_ACCESS_REVIEW.md` and ADR-029 | Added authoritative review and compatibility decision | Preserve source/terms evidence |
| Acquisition tests/reports/audit/status/traceability | Added exact metadata assertions and synchronized blockers | Prevent silent access or readiness drift |

## Database/migrations

- Migration revision(s): none
- Upgrade tested from: not applicable
- Downgrade/rollback notes: revert metadata state only; no source bytes exist in repository/private storage from this session
- Data backfill: none
- Schema/ERD update: none

## API/contract

- Endpoints added/changed: none
- OpenAPI/client regenerated: not applicable
- Breaking change: none
- Error/permission behaviour: readiness remains fail-closed until permission is approved and the validation spec becomes ready

## UI

- Screens/components: none
- States covered: not applicable
- Viewports/devices: not applicable
- Screenshot/evidence paths: none
- Accessibility notes: not applicable

## OCR/image/ML/verification

- Pipeline/model/rule/template versions: no model/pipeline change; STFD repository revision is frozen above
- Dataset/split/artifact hashes: archive LFS SHA-256 recorded; no dataset manifest or split hash created
- Metrics actually measured: none
- Limitations: STFD is foreign/non-Ghana-specific and is localization-oriented; public filenames do not prove independent source groups
- No fabricated or unavailable evidence: confirmed; metadata came from current authoritative project/Hugging Face/IEEE sources

## Security/privacy

- Access-control impact: permission remains request-required
- Private-data impact: no protected archive/sample opened; public screenshots may still carry unintended information despite author screening
- Upload/storage impact: none
- Audit events: ADR-029 and metadata-only evidence review
- Security checks: secret/prohibited-artifact scan passed over 496 candidates

## Verification performed

| Command | Result | Counts/summary | Duration |
|---|---|---|---:|
| Hugging Face metadata/tree API queries | PASS | exact revision, archive byte size and LFS object hash; no archive download | metadata-only |
| Targeted acquisition/governance tests | PASS | 112 tests | 23.9s including drift checks |
| `.venv\Scripts\python.exe scripts\verify_ml.py` | PASS | Ruff format/lint, strict mypy, 331 tests, 91.06% branch-aware coverage and all deterministic gates | 105.6s |
| `.venv\Scripts\python.exe scripts\check_secrets.py` | PASS | 496 candidate files | 2.9s |

Skipped/blocked checks and reason: STFD download, archive extraction, image/mask validation and group reconstruction are prohibited until written access and a reviewed lineage rule exist. Hosted GitHub Actions remain unable to allocate jobs under B-CI-001.

## Known defects/blockers

| ID | Severity | Description | Impact | Safe fallback | Owner/input | Next action |
|---|---|---|---|---|---|---|
| PR13-STFD-ACCESS | High | Dataset card requests academic/institutional email access; lineage grouping is undocumented | STFD cannot be downloaded, registered, split or trained | Keep exact metadata only; remain not-acquired/disabled | Project owner and dataset owner/data steward | Request written access and obtain/review a grouping rule |
| PR13-DATA-RIGHTS | High | FSTS and Ghana-private retain separate terms/consent gates | Logical PR13/PR14 incomplete | Keep both disabled/not acquired | Project owner/data steward | Review independently after STFD response or while waiting |
| B-CI-001 | External | GitHub Actions billing lock prevents runner allocation | No hosted reproduction | Preserve exact local evidence | Repository owner | Resolve account lock and rerun workflow |

## Documentation updated

- `IMPLEMENTATION_STATUS.md`: exact STFD metadata, blockers and next owner action
- `requirements_traceability.csv`: authoritative source/access evidence and non-acquisition boundary
- `DECISION_LOG.md`: ADR-029 accepted
- `CHANGELOG.md`: STFD metadata-only review recorded
- Evidence manifest/docs: `docs/evidence/PR13_STFD_SOURCE_ACCESS_REVIEW.md`

## Git evidence

```text
implementation commit: 7b12b9f6a7572bbf569c707ac057ec541ed92b10
push output: pending final handoff commit and push
STFD archive/sample tracked or opened: none
```

## Next exact task

The project owner sends the STFD access request from an academic/institutional email using the details required by the current Hugging Face card: researcher name/affiliation/homepage, supervisor details where applicable, and a brief academic research purpose. Preserve only an opaque approval reference in project governance. In parallel or after the reply, obtain an authoritative or conservatively reviewed source-lineage grouping rule. Do not download/open the archive, create filename-level splits or start Colab training before both gates pass.
