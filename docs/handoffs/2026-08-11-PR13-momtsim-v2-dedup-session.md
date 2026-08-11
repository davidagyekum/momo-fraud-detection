# Codex Session Handoff

## Session identity

- Date/time: 2026-08-11, Africa/Lagos
- Phase/sub-phase: Logical PR13 MoMTSim v2 deterministic derivation and registration
- Repository: `davidagyekum/momo-fraud-detection`
- Base branch: `main`
- Base SHA: `000bc65983d242cac8a8806a0cb116373bbcb4c2`
- Work branch: `codex/p13-dataset-acquisition-validation`
- Final implementation head SHA before this handoff: `58f7955fb7cc9e60f859cf1eb21a93ebd538c3e1`
- Pull request: not opened in this session
- Push status: pending final handoff push
- Worktree status: handoff documentation pending its final commit

## Scope completed

- Requirement IDs: NFR-DATA-001, NFR-AUD-001, FR-ML-005, FR-ML-006, logical PR13
- Backlog task IDs: reconciled logical PR13 MoMTSim v2 data-quality gate
- Goal: resolve the official v2 duplicate finding without mutating the source, weakening validation, creating splits or training.
- Actual completed work: implemented a strict local-only first-occurrence exact-row derivation, generated a private content-addressed derivative, and independently registered the derivative under a new version while preserving the official source and quarantine.

## Exact derivation and registration evidence

| Artifact | SHA-256 | Bytes/rows | Result |
|---|---|---:|---|
| Official v2 CSV | `99fd07c3a9d3c4bd6d3462240058ca19d0d9e9284683f78bf77542ff7fcc05e7` | 366,397,921 bytes / 4,225,958 rows | Immutable; quarantined for 20 exact duplicates |
| First-occurrence derivative | `642fcb2ba7c9cbfffb933729d118f426fefddcbaabbf002793807be169fe80cd` | 366,396,355 bytes / 4,225,938 rows | Registered; zero exact duplicates |
| Derivation manifest | `64c3924fcec35be44fb27e0b0ff356aac349d22c3d981db599790b1af9f305c2` | 20 duplicate groups; maximum group size 2 | Source/output lineage recorded |
| Registration manifest | `d0b4d73106cc28e05b0fc26c8560396870e59008bb271a8fa41f2bce7874a8e5` | 4,225,938 complete rows | `registered`; no quarantine reasons |
| Safe profile | `553ed698b96431e2bd3c7bfe3391713599c357f915f1d2132b6a80abba7058bf` | aggregate-only | no raw rows or paths |

- All 2,233,118 fraud-positive rows were retained; the 20 removed later occurrences were negative-label rows.
- The official v2 registration manifest remains content-addressed under SHA-256 `e65d92387627ef520acbecdd090e7103c361ce2c958e0943dbbe5a37ce070681`.
- The registry identifies the derivative as `2-derived-exact-dedup-v1`, keeps it disabled and does not mark it promotable.

## Changed files

| Area | Change | Why |
|---|---|---|
| `ml/src/momo_fdvs_ml/derivation.py` and CLI | Added strict local-only deterministic deduplication with approved-root confinement, source identity verification, atomic output and aggregate-only manifest | Create a reviewable derivative without touching official bytes |
| Deduplication JSON contracts and tests | Added strict request/manifest schemas and 19 focused tests | Prove fail-closed requests, confinement, determinism, manifest safety and CLI behavior |
| v2 spec, registry, manifests and safe profile | Registered the separately versioned derivative after a full 4.2-million-row validation | Keep official and derived identities distinct |
| ADR-028 and PR13 evidence | Recorded policy, hashes, row/class deltas and execution boundaries | Make the decision reconstructable |
| Readiness/governance reports, card, runbook, audit, traceability, changelog and status | Synchronized the measured state | Prevent stale or misleading project status |

## Database/migrations

- Migration revision(s): none
- Upgrade tested from: not applicable
- Downgrade/rollback notes: registry can revert to the preserved official quarantine; private derived bytes can remain quarantined outside Git
- Data backfill: none
- Schema/ERD update: none

## API/contract

- Endpoints added/changed: none
- OpenAPI/client regenerated: not applicable
- Breaking change: none to product API/database taxonomy
- Error/permission behaviour: derivation fails closed before output on invalid requests, identities, paths or schemas

## UI

- Screens/components: none
- States covered: not applicable
- Viewports/devices: not applicable
- Screenshot/evidence paths: none
- Accessibility notes: not applicable

## OCR/image/ML/verification

- Pipeline/model/rule/template versions: `exact-row-first-occurrence-v1`; derivative version `2-derived-exact-dedup-v1`
- Dataset/split/artifact hashes: source/output/manifest hashes recorded above; no split hash created
- Metrics actually measured: row/class/step/null/invalid/duplicate aggregates only; no model metrics
- Limitations: registration is not split approval, training permission, quality promotion or Ghana/provider representativeness evidence
- No fabricated or unavailable evidence: confirmed; source and derivative were fully scanned locally and raw values are not committed

## Security/privacy

- Access-control impact: CLI requires independently approved source/output roots and absolute confined paths
- Private-data impact: official and derived CSVs plus requests remain ignored under private storage
- Upload/storage impact: atomic private output; official bytes unchanged
- Audit events: derivation and registration manifests plus ADR-028/evidence record
- Security checks: secret/prohibited-artifact scan passed over 494 candidates; ignore rules explicitly matched all private inputs/outputs

## Verification performed

| Command | Result | Counts/summary | Duration |
|---|---|---|---:|
| `derive-deduplicated-transactions` over official v2 | PASS | 4,225,958 source rows; 20 later exact occurrences removed; 0 positives removed | 460.5s |
| Full derived-candidate registration | PASS | 4,225,938 rows; 2,233,118 positives; 193 steps; 0 duplicates/nulls/invalid values | 408.8s |
| `.venv\Scripts\python.exe scripts\verify_ml.py` | PASS | Ruff format/lint, strict mypy, 330 tests, 91.06% branch-aware coverage and all report/governance/notebook gates | 114.2s |
| `.venv\Scripts\python.exe scripts\check_secrets.py` | PASS | 494 candidate files | 3.3s final scan |
| `git check-ignore -v` on derivative/requests | PASS | all three private artifacts matched explicit ignore rules | final audit |

Skipped/blocked checks and reason: hosted GitHub Actions remain unable to allocate jobs under B-CI-001. No split generation, locked-test access, fitting, metric evaluation, model export or promotion was authorized or executed.

## Known defects/blockers

| ID | Severity | Description | Impact | Safe fallback | Owner/input | Next action |
|---|---|---|---|---|---|---|
| PR13-DATA-RIGHTS | High | STFD, FSTS and Ghana-private retain access/terms/consent and layout prerequisites | Logical PR13 and PR14 frozen splits cannot complete | Keep all three disabled/not acquired | Project owner/data steward | Review STFD authoritative access/terms/version/layout first |
| B-CI-001 | External | GitHub Actions account billing lock prevents runner allocation | No hosted reproduction | Preserve exact local evidence | Repository owner | Resolve account lock and rerun workflow |

## Documentation updated

- `IMPLEMENTATION_STATUS.md`: derived v2 registered, official quarantine preserved, measured gates and next image-source task
- `requirements_traceability.csv`: derivation contracts/code/tests and registration evidence added
- `DECISION_LOG.md`: ADR-028 accepted
- `CHANGELOG.md`: deterministic v2 derivative and non-training boundary recorded
- Evidence manifest/docs: `docs/evidence/PR13_MOMTSIM_V2_DEDUP_REGISTRATION.json`

## Git evidence

```text
implementation commit: 58f7955fb7cc9e60f859cf1eb21a93ebd538c3e1
push output: pending final handoff commit and push
private CSVs/requests tracked: none
```

## Next exact task

Review STFD's authoritative access mechanism, terms/licence, exact dataset version and image/mask/source-group layout. Do not acquire STFD until those gates are recorded. Keep FSTS optional, keep Ghana-private behind consent and a private withdrawal-aware index, and do not create PR14 splits or start Colab training yet.
