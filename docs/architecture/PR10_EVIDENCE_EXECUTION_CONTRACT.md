# Logical PR10 Evidence and Execution Contract

## Purpose

This foundation separates evidence availability from fraud-risk policy and prevents expensive model fitting from starting in the wrong environment. It is additive: the implemented API/database taxonomies remain active until a later versioned migration.

The portable contract is `packages/evidence-contracts/evidence-result-v1.schema.json`. The Flask runtime representation and compatibility projections are in `services/api/src/momo_fdvs/contracts/evidence.py`.

## Evidence modes

| Mode | Screenshot-derived evidence | Transaction evidence | Required null behaviour |
|---|---|---|---|
| `screenshot_only` | Image/OCR/semantic signals may be available, degraded or unavailable | Unavailable | Transaction score and label are null |
| `transaction_only` | Unavailable | May be available or degraded | Image, OCR and semantic scores/labels are null |
| `combined` | At least one screenshot-derived pipeline is not unavailable | Transaction pipeline is not unavailable | A missing subsystem stays null; it is never replaced with zero |
| `inconclusive` | May be unavailable | May be unavailable | Policy score is null and the risk band is `inconclusive` |

Every signal includes an explicit state, nullable score, nullable canonical image label and reason codes. An unavailable signal carrying `0`, another score or a label is invalid. This is the executable no-invented-features boundary: missing balance/history/transaction information cannot be represented as numeric zero merely to satisfy a model input.

## Taxonomy and compatibility

New evidence contracts use image-manipulation labels `unaltered` and `tampered`. These describe visible manipulation only; `unaltered` does not mean the transaction occurred or that it is genuine.

New policy contracts use `low_risk`, `medium_risk`, `high_risk` and `inconclusive`. They remain separate from stored/imported transaction verification.

Existing persisted and public values are not rewritten in this phase:

| Existing value | Canonical projection |
|---|---|
| `ORIGINAL` | `unaltered` |
| `CONTROLLED_TAMPERED` | `tampered` |
| `GENUINE` | `low_risk` |
| `SUSPICIOUS` | `medium_risk` |
| `FRAUDULENT` | `high_risk` |

The reverse temporary risk projection maps the three conclusive bands to the existing enum. `inconclusive` maps to null because manufacturing a legacy risk class would be misleading. Existing controlled manifest labels `genuine`/`fraudulent` remain readable only through the explicitly named legacy adapter so the failed P12 artifact and its schema hash are not silently altered. Newly governed image schemas reject those authenticity terms.

Any public API/database/UI migration must be separately versioned, add migrations where needed, regenerate OpenAPI/clients and preserve old clients through an explicit deprecation window.

## Result language

Generated summaries use cautious evidence language, require human review where relevant and state that the result is not provider verification. Contract tests reject the terms `safe`, `verified` and `100%` from these summaries. The existing stored-reference status `VERIFIED` remains valid only in its separate documented non-live verification record.

## Execution profiles

| Profile | Intended use | Existing training CLI behaviour |
|---|---|---|
| `UNIT` | Deterministic tests, schemas, validation and packaging checks | Model fitting blocked |
| `SMOKE` | Future tiny restart-safe PR12 smoke workflow | Current reportable model-fitting commands blocked |
| `FULL` | Reportable structured/image fitting | Allowed only in acknowledged Google Colab outside CI |

`train-structured` and `train-image` require `--profile full` plus the exact non-secret acknowledgement token `I_ACKNOWLEDGE_FULL_COLAB_TRAINING`. The guard then requires both standard Colab runtime markers and rejects every CI environment. The markers and token prevent accidental execution; they are not an authentication boundary and do not replace repository permissions, dataset consent or owner approval.

CI pins `MOMO_FDVS_EXECUTION_PROFILE: unit` and runs the registered ML gate. `scripts/verify_ml.py` fails before tests if a CI environment attempts to select `full`.

The P11/P12 notebooks already committed as historical run evidence continue to check out their original immutable pre-guard SHAs and therefore retain their original commands. They are not templates for another run. Every future training notebook must pin a commit containing this policy and pass the guarded FULL arguments.

## Current limitations and next migration

- No API response or database column has changed in this slice.
- The contract is not yet wired into final P13/P19 analysis orchestration.
- `SMOKE` defines the boundary but the restart-safe smoke notebook/run manifest arrives in logical PR12 reconciliation.
- This guard does not authorise data use and cannot make an ungoverned dataset acceptable.
- No model was trained and no threshold or accuracy result was produced in this phase.
