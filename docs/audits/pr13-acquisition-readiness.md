# Logical PR13 acquisition-readiness audit

Date: 2026-08-11  
Branch: `codex/p13-dataset-acquisition-validation`  
Base: `000bc65983d242cac8a8806a0cb116373bbcb4c2`

## Outcome

The no-network registration and validation foundation is implemented and locally verified. Official browser acquisition established exact MoMTSim v1/v2 and STFD byte identities in ignored private storage. PaySim, MoMTSim v1, the separately versioned MoMTSim v2 derivative and STFD are registered. The official MoMTSim v2 source remains quarantined for 20 exact duplicate rows, and STFD's initial directory-role ambiguity quarantine is preserved. All sources remain disabled and non-promotable.

| Source | Required | Validation-spec state | Blocking evidence |
|---|---:|---|---|
| PaySim | yes | ready; registered | disabled/non-promotable pending governed splits |
| MoMTSim v1 | yes | ready; registered | disabled/non-promotable pending governed splits |
| MoMTSim v2 | yes | derived version registered; official source quarantine preserved | disabled/non-promotable pending governed source-group-first splits |
| STFD | yes | ready; registered; one external-pretraining train-only group | disabled/non-promotable pending PR14 train-only split manifest |
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
- parallel-category image/mask pairing, rendered-mask semantics, soft-mask identity and single-group train-only enforcement;
- non-mutating quarantine and aggregate-only profiles;
- strict local-only deduplication request/manifest contracts, first-occurrence source-order retention and atomic private output;
- independent full validation of the 4,225,938-row v2 derivative with all 2,233,118 positive rows retained and zero exact duplicates;
- output-free Colab `readiness_only` notebook;
- no repository network client and explicit registration-network/training/promotion false fields.

## Verification evidence

`.venv\Scripts\python.exe scripts\verify_ml.py` passed format, lint, strict mypy, 334 tests at 90.11% branch-aware coverage, governance/readiness/report/notebook drift checks and all controlled dataset checks. The secret/prohibited-artifact scan passed over 498 candidates. Raw packages, official/derived CSVs and private requests remain ignored; only aggregate manifests/profiles and content hashes are committed.

## Stop decision

ADR-023 requires source-specific accountable evidence before any local/private source registration. ADR-027 preserves the official v2 quarantine, ADR-028 records the separate derivative, ADR-029 governs STFD access, and ADR-030 records its soft-mask and single-corpus grouping policy. Logical PR13 is complete: FSTS is optional/deferred and Ghana-private collection belongs to logical PR16. Logical PR14 may now freeze source-group-first structured partitions and STFD's train-only external group. FULL training remains blocked until PR14 evidence passes and the user is notified at the PR15 Colab checkpoint.
