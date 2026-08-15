# Governed dataset acquisition and registration runbook

Logical PR13 deliberately separates permission review, byte acquisition and byte registration. The repository contains no network downloader. A dataset may be registered only from an already-authorised local/private path after its registry and validation specification are ready.

## Current source gates

| Source | Evidence required before bytes may be acquired or opened |
|---|---|
| PaySim | Registered from the author-owned Kaggle Version 2 archive after CC BY-SA 4.0/platform review. Exact source, inventory, registration-manifest and safe-profile hashes are recorded; the first quarantine remains preserved. The source stays disabled/non-promotable pending PR14 frozen splits. |
| MoMTSim v1 | Registered from the official DOI version-1 package after exact filename, byte size, SHA-256, UTF-8 header and aggregate validation. It remains disabled/non-promotable pending PR14 frozen splits. |
| MoMTSim v2 | The immutable official source remains quarantined for 20 exact duplicate rows. ADR-028 records a separate content-addressed first-occurrence derivative that removed 20 negative duplicate occurrences and passed full registration with zero duplicates; it remains disabled/non-promotable pending PR14 splits. |
| STFD | Registered from the exact pinned private archive after permission, hash, extraction, decoded image/mask, duplicate and soft-mask checks. All 3,932 pairs form one external-pretraining train-only group because no authoritative source lineage is published. The three antialiased masks remain immutable; only derived training tensors may threshold rendered luminance at 128. |
| FSTS | Decision that the optional source is necessary, exact authoritative source/citation, applicable terms and approved deterministic subset/layout. |
| Ghana-private | Institution/supervisor-approved collection documents, per-participant consent, opaque permission references, withdrawal-aware private index and restricted storage. |

Until those conditions are recorded, the matching registry entry stays disabled. PaySim, MoMTSim v1, the separately versioned MoMTSim v2 derivative and STFD are registered but non-promotable. The official v2 and initial STFD layout quarantines remain preserved; FSTS and Ghana-private remain `not_acquired` behind their separate prerequisites. Project-owner permission does not by itself establish third-party licence or redistribution rights.

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
- Image validation checks extension, decoded content, byte/dimension/pixel caps, deterministic subset IDs, configured mask pairing/dimensions, rendered mask semantics, soft-mask drift and duplicate payloads. Source masks are immutable.
- Identity or validation failure writes a safe `quarantined` manifest; it does not modify the source.
- Registered and quarantined manifests remain `promotable_for_training: false`. A separate reviewed registry update, frozen splits and later training milestone are required.
- Safe profiles contain hashes and aggregates only; never source paths, member names, raw identifiers, images, masks or transcripts.

## Colab boundary

`ml/notebooks/colab/02_dataset_acquisition_validation.ipynb` is pinned to a
PaySim registration-only operation after source-specific rights and identity
review. It does not download bytes, create splits, read locked tests, train or
promote. Run the exact published pin and preserve both registered and quarantined
manifests as audit evidence.
