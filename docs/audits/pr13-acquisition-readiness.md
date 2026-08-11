# Logical PR13 acquisition-readiness audit

Date: 2026-08-11  
Branch: `codex/p13-dataset-acquisition-validation`  
Base: `000bc65983d242cac8a8806a0cb116373bbcb4c2`

## Outcome

The no-network registration and validation foundation is implemented and locally verified. Official browser acquisition established exact MoMTSim v1/v2 byte identities in ignored private storage. PaySim and MoMTSim v1 are registered; MoMTSim v2 is quarantined for 20 exact duplicate rows. All sources remain disabled and non-promotable.

| Source | Required | Validation-spec state | Blocking evidence |
|---|---:|---|---|
| PaySim | yes | ready; registered | disabled/non-promotable pending governed splits |
| MoMTSim v1 | yes | ready; registered | disabled/non-promotable pending governed splits |
| MoMTSim v2 | yes | ready; quarantined | 20 exact duplicate rows require a reviewed deterministic derived-dataset policy |
| STFD | yes | pending written access and layout | written access, terms/version and authoritative image/mask/group layout |
| FSTS | no | optional; pending terms and layout | necessity decision, authoritative source/terms/version and subset/layout |
| Ghana-private | yes | pending consent and private index | institutional/supervisor approval, participant consent, withdrawal index and restricted path |

## Implemented safe foundation

- strict acquisition-request and registration-manifest JSON contracts;
- deterministic metadata-only readiness inventory and drift check;
- registry eligibility enforcement before source-path resolution or byte access;
- approved-root and symlink confinement;
- content-addressed file, directory and hostile-ZIP inventory;
- PaySim transaction shape/count/label/null/amount/step and exact-duplicate checks;
- bounded image decode, dimension, pairing and deterministic-subset checks;
- non-mutating quarantine and aggregate-only profiles;
- output-free Colab `readiness_only` notebook;
- no repository network client and explicit registration-network/training/promotion false fields.

## Verification evidence

`.venv\Scripts\python.exe scripts\verify_ml.py` passed format, lint, strict mypy, 311 tests at 90.53% branch-aware coverage, governance/readiness/report/notebook drift checks and all controlled dataset checks. The secret/prohibited-artifact scan passed over 484 candidates. Raw packages, CSVs and acquisition requests remain ignored; only aggregate manifests/profiles and content hashes are committed.

## Stop decision

ADR-023 requires source-specific accountable evidence before any local/private source registration, and ADR-027 preserves the v2 quarantine. Logical PR13 stays In Progress because STFD, FSTS and Ghana-private retain separate gates and v2 needs an approved derivation policy. Logical PR14 split work and all FULL training remain blocked.
