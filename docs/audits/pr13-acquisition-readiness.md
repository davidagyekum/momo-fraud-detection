# Logical PR13 acquisition-readiness audit

Date: 2026-08-11  
Branch: `codex/p13-dataset-acquisition-validation`  
Base: `000bc65983d242cac8a8806a0cb116373bbcb4c2`

## Outcome

The no-network registration and validation foundation is implemented and locally verified. Real acquisition is not authorised: zero of six registry sources are eligible, and no source bytes were downloaded, opened, registered, copied, extracted or deleted.

| Source | Required | Validation-spec state | Blocking evidence |
|---|---:|---|---|
| PaySim | yes | ready after governance approval | accountable licence/permission review and exact version/archive identity |
| MoMTSim v1 | yes | pending authoritative schema | licence/permission, exact v1 identity and approved raw-field mapping |
| MoMTSim v2 | yes | pending authoritative schema | licence/permission, exact v2 identity and approved raw-field mapping |
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
- no network client and explicit false acquisition/training/promotion fields.

## Verification evidence

`.venv\Scripts\python.exe scripts\verify_ml.py` passed format, lint, strict mypy, 307 tests at 90.50% branch-aware coverage, governance/readiness/report/notebook drift checks and all controlled dataset checks. The secret/prohibited-artifact scan passed over 468 candidates. The outer repository wrapper remained nonzero only for the recorded host Node mismatch; this does not change the passing ML gate.

## Stop decision

ADR-023 requires source-specific accountable evidence before any local/private source registration. Logical PR13 stays In Progress, and logical PR14 split work and all FULL training remain blocked. Project-owner permission to use automation does not replace third-party licence, access or participant-consent review.
