# Codex Session Handoff

## Session identity

- Date/time: 2026-08-10 (Africa/Lagos)
- Phase/sub-phase: P12 — controlled CNN experiment preservation
- Repository: `davidagyekum/momo-fraud-detection`
- Work branch: `codex/p12-cnn-tampering`
- Training commit: `02d8967136853c5c46eaa0babe44a7327c843a32`
- Pre-evidence head: `fe39556b67ccab26004bda1674593c335d2e35dd`
- Model status: acceptance failed; not registered; not activated

## Outcome

The signed-in Google Colab run completed on the governed twelve-image controlled corpus. Packaging, SHA-256, preprocessing-schema and tensor-shape checks passed, but the model failed its configured macro-F1 acceptance gate. The failed experiment is preserved for audit and must not be represented as production, provider-wide or usable model evidence.

## Measured evidence

| Item | Result |
|---|---|
| Dataset scope | `controlled_synthetic_only` |
| Source groups/images | `6` / `12` |
| Held-out groups/images | `1` / `2` |
| Held-out macro F1 | `0.333333` |
| Acceptance minimum | `0.85` |
| Acceptance passed | `false` |
| Held-out predictions | both `CONTROLLED_TAMPERED` |
| Selected threshold | `0.05` from validation only |
| CPU median/p95 | `110.137 ms` / `171.081 ms` in Colab CPU runtime |
| Artifact format | Keras v3, private and ignored |
| Artifact SHA-256 | `3d074298835a28a9af92fca8b50cc618dc8eb67585e2b312c261121f43a70046` |

The held-out ROC/PR AUC values are not treated as acceptance evidence because they are calculated over only two samples. The controlled corpus cannot estimate provider generalisation or calibration.

## Safe tracked evidence

- `docs/evidence/P12_IMAGE_EVALUATION.json`
- `docs/evidence/P12_IMAGE_CONFUSION_MATRIX.png`
- `docs/evidence/P12_IMAGE_REGISTRY_PAYLOAD.json` (registration-shaped metadata only; no registration occurred)
- `docs/models/IMAGE_MODEL_CARD_CONTROLLED_V1.md`

The binary remains at the ignored private artifact location and is identified only by its hash.

## Verification and privacy

- Repository ML baseline after evidence import: Ruff format/lint pass, strict mypy pass, 99 tests pass, 91.83% total coverage on the P12 branch.
- Secret/artifact scan passed before edits.
- No private model binary, raw dataset, credential or personal data is added to Git.
- Deterministic dataset reports are explicitly labelled preflight-only; external run evidence is separate.

## Required next action

Do not activate this artifact or rerun against the exhausted controlled test group. Reconcile the approved PR10-PR20 blueprint, freeze a new representative authorised dataset and split manifest, then prepare a new versioned Colab run. Stop again before the next full training cell for owner approval.
