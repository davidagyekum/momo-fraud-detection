# Logical PR12 Reproducible Colab Foundation Plan

- Date: 2026-08-10
- Branch: `codex/p12-colab-foundation`
- Base: `438d2d007496a2d0163cfed75c76da48bbb215ca`
- Scope: the restart-safe Colab foundation from the ordered PR10–PR12 reconciliation backlog

## In scope

1. Define one versioned execution/runtime contract for unit, smoke and full profiles while preserving the existing fail-closed FULL guard.
2. Add configurable Drive and ephemeral-VM layouts without personal paths, plus immutable Git checkout/dirty-state recording.
3. Add runtime inventory, deterministic seeding, run IDs, expanded run manifests, atomic JSON writes, verified checkpoints and resume history.
4. Load optional Colab secrets through a non-printing adapter; never persist secret values in logs, manifests or notebooks.
5. Add clean-session environment preflight, reusable notebook template and tiny restart-safe smoke notebook under `ml/notebooks/colab/`.
6. Add notebook structure/output/secret policy checks and register them in the ML verification gate.
7. Add a bounded smoke orchestrator over fictitious fixtures that exercises transaction preprocessing, lightweight OCR/image contract checks, deterministic fitting, export/reload, inference, checkpoint resume and final manifest emission.
8. Document runtime-loss recovery, Drive synchronization and the exact owner-operated Colab handoff.

## Out of scope

- Dataset acquisition, downloading, scraping, participant collection or registry enablement.
- Access to locked validation/test sets or private screenshots.
- Reportable/full fitting, calibration, threshold selection or model promotion.
- Re-running or activating the historical failed P12 image artifact.
- Personal Drive paths, credentials, tokens, completed consent records or large artifacts.

## Verification target

- Registered ML format/lint/type/test/governance/notebook gates.
- Deterministic smoke outputs within declared tolerance.
- Corrupt checkpoint rejection and valid same-run resume.
- Run-manifest schema/runtime validation and atomic-write recovery.
- Notebook restart/run-all structure, output stripping and secret absence.
- CI/local FULL rejection and unit/smoke resource caps.
- Secret/prohibited-artifact scan and JSON/notebook integrity.

## Stop boundary

Commit and push the prepared foundation, then stop. A real fresh Google Colab smoke execution requires the project owner to open the committed notebook and authorize Google Drive mounting. No data acquisition or full training is permitted in this phase.
