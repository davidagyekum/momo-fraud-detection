# Codex Session Handoff

## Session identity

- Date/time: 2026-08-11, Africa/Lagos
- Phase/sub-phase: Logical PR13 MoMTSim v1/v2 rights, schema and acquisition-gate review
- Repository: `davidagyekum/momo-fraud-detection`
- Base branch: `main`
- Base SHA: `000bc65983d242cac8a8806a0cb116373bbcb4c2`
- Work branch: `codex/p13-dataset-acquisition-validation`
- Final implementation head SHA before this handoff: `53f852f99204185ebd11781edcf19b77b98ec982`
- Pull request: not opened in this session
- Push status: pending final handoff push
- Worktree status: handoff documentation pending its final commit

## Scope completed

- Requirement IDs: NFR-DATA-001, FR-ML-005, FR-ML-006, logical PR13
- Backlog task IDs: reconciled logical PR13 MoMTSim source preparation
- Goal: resolve authoritative MoMTSim rights and published-schema prerequisites without opening source bytes.
- Actual completed work: verified official Mendeley DOI versions 1/2 and CC BY 4.0; recorded the two version-2 listed files; mapped the peer-reviewed ten raw columns and exact published row/class counts; approved only official Mendeley acquisition; left both sources disabled and `not_acquired`; retained an exact file-mapping/hash gate.

## Changed files

| Path | Change | Why |
|---|---|---|
| `docs/evidence/PR13_MOMTSIM_SOURCE_RIGHTS_REVIEW.md` | Added authoritative rights/schema/count review | Establish accountable acquisition conditions |
| `DECISION_LOG.md` | Added ADR-026 | Prohibit mirrors, inferred version mapping and silent activation |
| `data/registry.yaml` | Approved permission/licence for v1/v2 only | Resolve rights while retaining disabled/not-acquired state |
| `data/acquisition_specs/momtsim-v1.json`, `momtsim-v2.json` | Added official DOI metadata, columns and published counts | Prepare strict validation without guessing byte identity |
| MoMTSim cards, runbook, readiness/governance reports | Updated remaining exact-file blocker | Keep deterministic evidence synchronized |
| `ml/tests/test_acquisition.py` | Updated fail-closed blocker expectations | Prove source paths remain unopened before specs are ready |
| Status, traceability, changelog and audit | Updated next action and limitations | Preserve exact handoff |

## Database/migrations

- Migration revision(s): none
- Upgrade tested from: not applicable
- Downgrade/rollback notes: revert rights approval if authoritative Mendeley metadata changes or is disproved
- Data backfill: none
- Schema/ERD update: none

## API/contract

- Endpoints added/changed: none
- OpenAPI/client regenerated: not applicable
- Breaking change: none
- Error/permission behaviour: registration fails before source access while `pending_exact_file_identity`

## UI

- Screens/components: none
- States covered: approved rights versus not-acquired/unready registration
- Viewports/devices: not applicable
- Screenshot/evidence paths: none
- Accessibility notes: not applicable

## OCR/image/ML/verification

- Pipeline/model/rule/template versions: `dataset-validation-spec-v1`
- Dataset/split/artifact hashes: registry `3a9b18d9999b697438716af1b5031a9b79e979a002aacc0bfab49a3a5184ced8`; no MoMTSim dataset/split/model hash exists yet
- Metrics actually measured: none; published references are v1 1,720,181/175,518 and v2 4,225,958/2,233,118 rows/positives
- Limitations: displayed file sizes are not byte identity; `nbSteps=720` is not frozen as an observed unique-step count
- No fabricated or unavailable evidence: no acquisition, raw-byte inspection, validation run, split, metric or promotion is claimed

## Security/privacy

- Access-control impact: future bytes must remain in private storage
- Private-data impact: MoMTSim is synthetic; no bytes were opened or committed
- Upload/storage impact: none
- Audit events: ADR-026 and source-rights evidence
- Security checks: secret/prohibited-artifact scan passed 479 candidate files

## Verification performed

| Command | Result | Counts/summary | Duration |
|---|---|---|---|
| Official-source web review | PASS | DOI v1/v2, dates, author, CC BY 4.0, two listed files and article schema/counts grounded | bounded review |
| `.venv\Scripts\python.exe scripts\verify_ml.py` | PASS | Ruff, strict mypy, 308 tests, 90.52% branch-aware coverage and all deterministic reports | 95.6s final run |
| `py -3.12 scripts\check_secrets.py` | PASS | 479 candidate files | 2.4s |

Skipped/blocked checks and reason: no MoMTSim bytes were authorised for opening before exact official file identity is established. Hosted GitHub Actions remain blocked by B-CI-001. No training, split generation or locked-test access occurred.

## Known defects/blockers

| ID | Severity | Description | Impact | Safe fallback | Owner/input | Next action |
|---|---|---|---|---|---|---|
| PR13-MOMTSIM-IDENTITY | High | Exact official file-to-version mapping, bytes, hashes, header/encoding and observed aggregates are not recorded | v1/v2 cannot register | Keep both disabled/not acquired | Project owner/Codex through official Mendeley UI | Download official DOI versions separately and content-address them |
| PR13-DATA-RIGHTS | High | STFD, FSTS and Ghana-private retain separate access/terms/consent gates | Logical PR13 remains incomplete | Keep sources disabled | Project owner/data steward | Review each source separately |
| B-CI-001 | Medium | GitHub Actions billing lock prevents job allocation | No hosted reproduction | Preserve exact local evidence | Repository owner | Resolve account lock |

## Documentation updated

- `IMPLEMENTATION_STATUS.md`: MoMTSim rights/schema complete; exact-file identity next
- `requirements_traceability.csv`: official DOI/licence evidence and remaining gate
- `DECISION_LOG.md`: ADR-026
- `CHANGELOG.md`: source review without acquisition
- Evidence manifest/docs: `docs/evidence/PR13_MOMTSIM_SOURCE_RIGHTS_REVIEW.md`

## Git evidence

```text
53f852f docs(data): approve official MoMTSim sources
final handoff commit/push reported by the session response
```

## Next exact task

Use only the official Mendeley DOI download paths for v1 and v2. Preserve each
download separately in private storage, then record exact filenames, file-to-
version mapping, byte sizes, SHA-256 values and bounded header/encoding evidence.
Only after that evidence is committed may the corresponding validation specs
become ready and an owner-operated Colab registration notebook be prepared.
Do not create PR14 splits or start training.
