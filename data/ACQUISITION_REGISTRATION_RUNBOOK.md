# Governed dataset acquisition and registration runbook

Logical PR13 deliberately separates permission review, byte acquisition and byte registration. The repository contains no network downloader. A dataset may be registered only from an already-authorised local/private path after its registry and validation specification are ready.

## Current source gates

| Source | Evidence required before bytes may be acquired or opened |
|---|---|
| PaySim | Authoritative citation and Kaggle terms reviewed by a named reviewer; permitted academic purpose; exact version/archive identity; private storage location. |
| MoMTSim v1 | Authoritative Mendeley v1 citation/licence; exact v1 archive identity; approved raw-field mapping for transaction, actor, balance and label roles. |
| MoMTSim v2 | Authoritative Mendeley v2 citation/licence; exact v2 archive identity; approved raw-field mapping kept separate from v1. |
| STFD | Written academic access approval, licence/restrictions, exact archive/version identity, and authoritative image/mask/grouping layout. |
| FSTS | Decision that the optional source is necessary, exact authoritative source/citation, applicable terms and approved deterministic subset/layout. |
| Ghana-private | Institution/supervisor-approved collection documents, per-participant consent, opaque permission references, withdrawal-aware private index and restricted storage. |

Until those conditions are recorded, the matching registry entry stays disabled and `not_acquired`. Project-owner permission does not establish third-party licence or redistribution rights.

## Safe readiness check

```powershell
$env:PYTHONPATH = "ml/src"
.venv\Scripts\python.exe -m momo_fdvs_ml acquisition-readiness `
  --data-root data `
  --recorded-report data/acquisition_readiness_report.json
```

This command reads governance metadata and validation specifications only. It opens no source bytes and performs no network call.

## Private registration request

Create an `acquisition-request-v1` JSON document outside Git. Use only opaque reviewer, permission, licence or consent references. The request must identify an absolute source path under the separately approved private root and its independently obtained SHA-256/size/version. Never store credentials, URLs containing tokens, participant identifiers or completed consent documents in the request.

After a human checks the request and source-specific evidence, registration is local-only:

```powershell
$env:PYTHONPATH = "ml/src"
.venv\Scripts\python.exe -m momo_fdvs_ml register-dataset `
  --data-root data `
  --request C:\approved-private\requests\paysim.json `
  --allowed-source-root C:\approved-private\datasets `
  --manifest-output data\manifests\paysim.manifest.json `
  --profile-output reports\generated\dataset_profiles\paysim-safe-summary.json
```

The example paths are placeholders. Do not copy them into a real request without verifying the resolved root.

## Validation and quarantine semantics

- Registration never downloads, extracts, moves or deletes source bytes.
- The resolved source must remain inside the approved private root and may not be a symbolic link.
- ZIP inventory rejects traversal, symbolic links, duplicate normalised member paths, excessive member counts and excessive expanded size.
- Transaction validation checks exact raw columns, row/positive/step expectations, target values, amounts, nulls and exact duplicate rows using temporary disk-backed hashes.
- Image validation checks extension, decoded content, byte/dimension/pixel caps, deterministic subset IDs and configured mask pairing/dimensions.
- Identity or validation failure writes a safe `quarantined` manifest; it does not modify the source.
- Registered and quarantined manifests remain `promotable_for_training: false`. A separate reviewed registry update, frozen splits and later training milestone are required.
- Safe profiles contain hashes and aggregates only; never source paths, member names, raw identifiers, images, masks or transcripts.

## Colab boundary

`ml/notebooks/colab/02_dataset_acquisition_validation.ipynb` is currently pinned to `readiness_only`. Run it only to reproduce the blocker report. Do not change it to registration/acquisition mode until the source-specific evidence above has been reviewed and the phase branch records that decision.
