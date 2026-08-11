# Session handoff — logical PR13 STFD registration and close

## Session identity

- Date/time: 2026-08-11
- Phase/sub-phase: Logical PR13 dataset acquisition and validation — STFD decoded validation, registration and phase close
- Repository: `davidagyekum/momo-fraud-detection`
- Base branch: `main`
- Base SHA: `000bc65983d242cac8a8806a0cb116373bbcb4c2`
- Work branch: `codex/p13-dataset-acquisition-validation`
- Session-start head: `9b0375a4dca67f692cbbcc521be17d7b211ac1f0`
- Final implementation head before this handoff: `bc9c0b4ae833bb9bcd2c2d145957967d466635c0`
- Pull request: not created in this session
- Push status: pending final handoff commit and push
- Worktree status: handoff documentation pending its final commit

## Scope completed

- Requirement IDs: NFR-DATA-001, NFR-AUD-001, FR-ML-005, FR-ML-006
- Backlog task IDs: logical PR13 STFD validation/registration and acquisition-readiness close
- Goal: validate the authorised exact STFD archive without exposing private access material, register only a fully decoded fail-closed corpus, and establish a leakage-safe split rule before PR14.
- Actual completed work: privately extracted the pinned archive; decoded and paired all 3,932 image/mask pairs; verified dimensions, masks and exact duplicates; preserved the first validator quarantine; fixed and tested role-aware category discovery; registered sanitized aggregate evidence; closed logical PR13 with all datasets disabled/non-promotable.

## Changed files

| Path | Change | Why |
|---|---|---|
| `ml/src/momo_fdvs_ml/acquisition.py` | Added complete parallel-category image/mask validation and corpus-level grouping | Enforce decoded integrity and fail closed before registration |
| `ml/tests/test_acquisition.py`, `ml/tests/test_governance.py` | Added registration, layout-ambiguity and soft-mask-drift coverage | Prevent unsafe grouping or source drift |
| `data/acquisition_specs/stfd.json`, `data/registry.yaml`, cards/reports | Frozen exact pair counts, soft-mask contract, train-only grouping and registered state | Make PR14 consume a deterministic governed source |
| `docs/evidence/PR13_STFD_REGISTRATION.json` | Added aggregate content-addressed evidence | Preserve reproducible proof without private members or paths |
| ADR, audit, threat model, traceability, changelog and status | Recorded ADR-030, phase outcome, boundaries and next task | Keep the repository handoff auditable and honest |

## Database/migrations

- Migration revision(s): none
- Upgrade tested from: not applicable
- Downgrade/rollback notes: registry remains disabled; registration can be withdrawn without altering product data
- Data backfill: none
- Schema/ERD update: none

## API/contract

- Endpoints added/changed: none
- OpenAPI/client regenerated: not applicable
- Breaking change: none
- Error/permission behaviour: acquisition validation quarantines structural, decoded, count, duplicate and soft-mask-contract drift

## UI

- Screens/components: none
- States covered: not applicable
- Viewports/devices: not applicable
- Screenshot/evidence paths: none
- Accessibility notes: not applicable

## OCR/image/ML/verification

- Pipeline/model/rule/template versions: dataset acquisition foundation v1; STFD `hf-revision-9edebed2109052a77e9a5581c2ea7ce33d685da0-private-v1`; ADR-030
- Dataset/split/artifact hashes: archive SHA-256 `6159a6611caaf71f40acf181b404af5a5dd0547f3d2d8d819bb640e3fb5de18c`; private extracted inventory `1087bbc4ba2cd349f08e2a0a4c4ebbc78c209d603d625c2a5344c0ff50f220dc`; private registration manifest `e2a12c8a1c2ddf3324d775486ba0ea69550e9c3688fa7e44fba8c655df7b5945`; registry `5c0df60dcde83a38c92a2c5f3dde325d3b7dc7e2a58338b291317d92ce1bb208`
- Metrics actually measured: 3,932 complete pairs; zero decode, dimension, blank-mask or exact-duplicate failures; three masks with 12,860 antialiased rendered pixels
- Limitations: STFD publishes no independent source-lineage key; the entire corpus is one external-pretraining train-only group and cannot supply internal validation/test metrics. Source masks remain unchanged; threshold 128 is allowed only for derived tensors.
- No fabricated or unavailable evidence: no split, training, locked-test, model metric, artifact promotion or deployment occurred

## Security/privacy

- Access-control impact: none to product roles; private extraction stayed under the restricted external data root
- Private-data impact: no password, source path, member name, screenshot, image, mask or raw archive byte entered Git or command output
- Upload/storage impact: exact encrypted archive and extracted payload remain outside Git; only aggregate hashes/counts are committed
- Audit events: the initial `category_directory_layout_mismatch` quarantine is preserved with content hashes
- Security checks: password persistence check false; secret/prohibited-artifact scan passed over 499 candidate files

## Verification performed

| Command | Result | Counts/summary | Duration |
|---|---|---|---|
| `.venv\Scripts\python.exe -m pytest ml/tests/test_acquisition.py ml/tests/test_governance.py` | PASS | 115 targeted tests | 9.09s |
| `.venv\Scripts\python.exe scripts\verify_ml.py` | PASS | Ruff format/lint, strict mypy, 334 tests, 90.11% branch-aware coverage, governance/readiness/notebook and controlled-dataset checks | included in 118.3s combined run |
| `.venv\Scripts\python.exe scripts\check_secrets.py` | PASS | 499 candidate files in the final post-handoff scan | 3.2s |
| `git diff --check` | PASS | no whitespace errors | under 2s |

Skipped/blocked checks and reason: hosted GitHub Actions remain unable to allocate runners under B-CI-001. No model training was authorised in PR13.

## Known defects/blockers

| ID | Severity | Description | Impact | Safe fallback | Owner/input | Next action |
|---|---|---|---|---|---|---|
| B-CI-001 | External | GitHub Actions account billing lock prevents runner allocation | Hosted reproduction unavailable | Preserve exact local evidence | Repository owner | Resolve account lock and rerun |
| P12-ACCEPTANCE | High | Historical controlled image model failed its macro-F1 gate | Artifact remains inactive | Explicit unavailable state | Data/model owner | Train only after governed data/splits |
| PR16-GHANA-PRIVATE | Planned | Owner transactions and public fraud-message candidates are not yet ingested | Ghana adaptation cannot start | Keep source disabled | Project owner and data steward | Perform governed private intake in PR16 |

## Documentation updated

- `IMPLEMENTATION_STATUS.md`: logical PR13 complete, exact verification and PR14 next task
- `requirements_traceability.csv`: STFD registration evidence and conservative grouping
- `DECISION_LOG.md`: ADR-030
- `CHANGELOG.md`: decoded validation and registration
- Evidence manifest/docs: `docs/evidence/PR13_STFD_REGISTRATION.json`, source review, audit and threat model

## Git evidence

```text
git status --short: handoff documentation pending its final commit
git log --oneline 9b0375a4dca67f692cbbcc521be17d7b211ac1f0..HEAD:
bc9c0b4 feat(data): register validated STFD corpus
push output: pending final handoff commit and push
```

## Next exact task

Push the completed PR13 branch, create `codex/p14-frozen-splits` from its exact head, and implement deterministic source-group-first structured partitions plus STFD's single external-pretraining train-only assignment. Add strict split-manifest validation, leakage tests and aggregate evidence. Do not train a model; stop and notify the project owner before PR15 starts Google Colab training.
