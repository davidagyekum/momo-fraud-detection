# Codex Session Handoff

## Session identity

- Date/time: 2026-08-11, Africa/Lagos
- Phase/sub-phase: Logical PR13 MoMTSim v1/v2 official acquisition and registration
- Repository: `davidagyekum/momo-fraud-detection`
- Base branch: `main`
- Base SHA: `000bc65983d242cac8a8806a0cb116373bbcb4c2`
- Work branch: `codex/p13-dataset-acquisition-validation`
- Final implementation head SHA before this handoff: `91da9dd3841cca880974c5cbfc76bd82acddf07d`
- Pull request: not opened in this session
- Push status: pending final handoff push
- Worktree status: handoff documentation pending its final commit

## Scope completed

- Requirement IDs: NFR-DATA-001, NFR-AUD-001, FR-ML-005, FR-ML-006, logical PR13
- Goal: establish exact official MoMTSim byte identities, validate complete CSVs and preserve fail-closed outcomes without splitting or training.
- Actual result: official DOI packages were downloaded through Chrome into ignored private storage. Version 1 passed complete registration. Version 2 matched its published schema/counts but was quarantined because the strict validator found 20 exact duplicate rows.

## Exact source and validation evidence

| Source | Official CSV SHA-256 | Bytes | Rows | Positives | Distinct steps | Exact duplicates | Status |
|---|---|---:|---:|---:|---:|---:|---|
| MoMTSim v1 | `da951eb95735da96271740a3e66b676b342d3831ce3111cd19dbfa020d3bd0a7` | 156,564,413 | 1,720,181 | 175,518 | 144 | 0 | registered |
| MoMTSim v2 | `99fd07c3a9d3c4bd6d3462240058ca19d0d9e9284683f78bf77542ff7fcc05e7` | 366,397,921 | 4,225,958 | 2,233,118 | 193 | 20 | quarantined |

- v1 package SHA-256: `55504e566f79b9513901a0d1269563df9f4840de15a77417d67bbafb2847550c` (55,998,854 bytes)
- v2 package SHA-256: `e55969cef235cb7f313d4cda8579f453f494843915e880cac92c0b0d657f8cdc` (192,448,698 bytes)
- The smaller CSV retained in the v2 package is byte-identical to v1; it was not treated as another v2 population.
- Both CSVs use the published ten-column UTF-8 header without a BOM.
- No raw paths, identifiers, rows or duplicate values are present in committed evidence.

## Changed files

| Area | Change | Reason |
|---|---|---|
| `data/acquisition_specs/momtsim-v1.json`, `momtsim-v2.json` | Froze official filenames, file IDs, hashes, sizes, encoding and measured step counts | Establish exact byte identity |
| `data/manifests/` and `reports/generated/dataset_profiles/` | Added content-addressed safe v1/v2 registration results | Preserve registered/quarantined evidence without raw data |
| `data/registry.yaml` and generated readiness/governance reports | Set v1 registered and v2 quarantined; both disabled | Keep registry aligned with measured outcomes |
| `docs/evidence/PR13_MOMTSIM_ACQUISITION_REGISTRATION.json` | Added package/file identities, safe aggregates and execution boundaries | Reconstruct acquisition/validation |
| `DECISION_LOG.md` | Added ADR-027 | Prohibit silent v2 deduplication or validator weakening |
| Acquisition implementation/tests | Quarantined registry sources now block readiness; committed safe evidence is tested | Preserve fail-closed state and prevent data leakage |
| Cards, runbook, audit, traceability, changelog and status | Updated source states and next action | Maintain honest handoff |

## Database/API/UI

- Database migrations: none
- API or public contract changes: none
- UI changes: none
- Raw source files committed: none

## Security/privacy

- Official ZIP/CSV bytes remain under ignored `private-storage/` paths.
- Registration requests remain under ignored `data/acquisition-requests/`.
- Browser acquisition occurred, but registration itself executed no network client.
- Source bytes were not mutated, deleted, publicly served or committed.
- Secret/prohibited-artifact scan: PASS over 485 candidate files after this handoff.

## Verification performed

| Command | Result | Evidence | Duration |
|---|---|---|---:|
| Full v1 registration | PASS | `registered`; zero quarantine reasons; complete 1,720,181-row scan | 120.3s |
| Full v2 registration | EXPECTED QUARANTINE | `duplicate_rows_present`; 20 exact duplicates; all other aggregate checks pass | 324.3s |
| `.venv\Scripts\python.exe scripts\verify_ml.py` | PASS | Ruff format/lint, strict mypy, 311 tests, 90.53% branch-aware coverage and all deterministic report gates | 132.3s |
| `py -3.12 scripts\check_secrets.py` | PASS | 485 candidate files; private/raw artifacts ignored | final scan |

Hosted GitHub Actions remain unable to allocate jobs under B-CI-001. No split generation, locked-test access, fitting, metric evaluation, model export or promotion occurred.

## Known blockers

| ID | Impact | Safe fallback | Next action |
|---|---|---|---|
| PR13-MOMTSIM-V2-DUPLICATES | v2 cannot enter splits/training/evaluation | Preserve immutable source and quarantine; keep disabled | Review an explicit content-addressed derived-dataset/deduplication policy, then revalidate a separate candidate |
| PR13-DATA-RIGHTS | STFD, FSTS and Ghana-private remain unavailable | Keep them disabled/not acquired | Review each source's access, terms, consent and layout independently |
| B-CI-001 | No hosted reproduction | Preserve exact local evidence | Repository owner resolves Actions billing lock |

## Next exact task

Design and review the MoMTSim v2 derived-dataset contract before creating any
deduplicated bytes. It must preserve the official source hash, select duplicate
representatives deterministically, record removed-row and duplicate-group counts,
produce a new content hash, and re-run the full validator. Do not create PR14
splits or start Colab training. Continue the independent STFD/FSTS/Ghana-private
rights gates only when authoritative evidence is available.
