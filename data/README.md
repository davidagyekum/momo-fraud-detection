# Canonical Data Governance Registry

This directory contains metadata, schemas, fictitious fixtures and governance templates only. It must never contain downloaded archives, participant screenshots, completed consent/withdrawal records, credentials, checkpoints or model artifacts.

`registry.yaml` is deliberately JSON-compatible YAML so the pinned Python standard library can validate it without adding a parser dependency. Every source is disabled; acquisition and registration states remain explicit. An entry may be enabled only after its permission/licence and exact bytes are approved and registered outside Git.

Logical PR13 validation specifications live in `acquisition_specs/`. `acquisition_readiness_report.json` and `reports/generated/dataset_inventory.md` prove that PaySim, MoMTSim v1, the separately versioned MoMTSim v2 first-occurrence derivative and STFD are registered but disabled; the readiness command itself opens no source bytes. The immutable official v2 and initial STFD directory-layout quarantines remain preserved. STFD's private extracted inventory passed complete image/mask validation and is conservatively one external-pretraining train-only group with no internal STFD evaluation. Exact identities and derivation/access provenance are recorded under `docs/evidence`, while raw/derived bytes remain in ignored private storage. See `ACQUISITION_REGISTRATION_RUNBOOK.md` before preparing a private request.

Run:

```powershell
$env:PYTHONPATH = "ml/src"
.venv\Scripts\python.exe -m momo_fdvs_ml validate-governance `
  --root data `
  --recorded-report data/governance_report.json
```

The report proves registry/schema/fixture/taxonomy/withdrawal consistency and records hashes. It explicitly states that acquisition and training did not execute. It does not provide legal approval, dataset representativeness or model evidence.
