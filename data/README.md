# Canonical Data Governance Registry

This directory contains metadata, schemas, fictitious fixtures and governance templates only. It must never contain downloaded archives, participant screenshots, completed consent/withdrawal records, credentials, checkpoints or model artifacts.

`registry.yaml` is deliberately JSON-compatible YAML so the pinned Python standard library can validate it without adding a parser dependency. Every source is disabled and not acquired. An entry may be enabled only after its permission/licence and exact bytes are approved and registered outside Git.

Logical PR13 validation specifications live in `acquisition_specs/`. `acquisition_readiness_report.json` and `reports/generated/dataset_inventory.md` prove that PaySim, MoMTSim v1 and the separately versioned MoMTSim v2 first-occurrence derivative are registered but disabled, while the three image sources retain separate gates; the readiness command itself opens no source bytes. The immutable official v2 quarantine remains preserved. Exact identities and derivation provenance are recorded under `docs/evidence`, while raw/derived bytes remain in ignored private storage. See `ACQUISITION_REGISTRATION_RUNBOOK.md` before preparing a private request.

Run:

```powershell
$env:PYTHONPATH = "ml/src"
.venv\Scripts\python.exe -m momo_fdvs_ml validate-governance `
  --root data `
  --recorded-report data/governance_report.json
```

The report proves registry/schema/fixture/taxonomy/withdrawal consistency and records hashes. It explicitly states that acquisition and training did not execute. It does not provide legal approval, dataset representativeness or model evidence.
