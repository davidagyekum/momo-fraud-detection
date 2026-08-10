# Dataset Card — `momo-fdvs-controlled-v1`

## Accountability and permission

- Owner/custodian: MoMo-FDVS project owner
- Approval date: 2026-08-10
- Source type: `synthetic` originals and `controlled_tamper` derivatives
- Consent or licence reference: `SYNTHETIC_GENERATOR_V1`
- Permitted purpose: software, leakage-control and research-pipeline validation
- Prohibited uses: provider impersonation, customer decisions, production-performance or provider-wide accuracy claims
- Retention/review rule: versioned with source code; review when generator/schema changes
- Revocation/deletion: delete the generated fixture version and rebuild manifests/reports

## Content and privacy

- Collection/generation method: deterministic Pillow renderer and declared controlled operations
- Provider/population scope: generic Ghana-style demonstration; no provider branding or customer population
- Personal data present: no
- Anonymisation status: `not_applicable`; generated values are explicitly marked `DEMO` or `XXX`
- Storage: committed small fixtures under this directory
- Label policy: binary image research proxy—synthetic originals are `genuine`; declared controlled edits are `fraudulent`
- Source group: one original plus its controlled derivative

## Reproducibility

- Manifest schema: `receipt-dataset-manifest-v1`
- Generation seed: `20260810`
- Generator: `generic-ghana-receipt-generator-v1`
- Dependency lock: `ml/requirements-runtime.lock`
- Hashes and distributions: `dataset_report.json` and `DATASET_REPORT.md`
- Gate: `.venv\Scripts\python.exe scripts\verify.py --ml`

## Limitations

The labels describe controlled research edits, not confirmed real-world fraud. The dataset is small, generic and deliberately balanced by source group. It excludes provider layouts, real customers, natural fraud prevalence and many capture conditions. No model was trained or evaluated during P10.
