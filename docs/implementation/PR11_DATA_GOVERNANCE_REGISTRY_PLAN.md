# Logical PR11 Data Governance and Registry Plan

- Date: 2026-08-10
- Branch: `codex/p11-data-governance-registry`
- Base: `4b0f63f1b34a3b3c57e3f6dc39936594f9f6a6a7`
- Scope: the registry/schema/privacy-governance slice from the ordered PR10–PR12 reconciliation backlog

## In scope

1. Add canonical `data/registry.yaml` entries for PaySim, MoMTSim v1/v2, STFD, optional FSTS and Ghana-private.
2. Fail closed for unknown or unverified licences, consent, access and redistribution terms; registry entries do not download data.
3. Add portable JSON schemas and fictitious fixtures for transactions, screenshots, OCR truth, edit manifests, split manifests and run manifests.
4. Add dataset cards, data dictionary, tamper taxonomy and a controlled-fixture provenance card.
5. Add participant information/consent templates, internal-versus-release scope, withdrawal/deletion process, de-identification standard, access roles, retention schedule, incident process and publication checklist.
6. Add `DATA_ACCESS.md`, a data threat model, ignore rules, registry/schema/taxonomy/withdrawal validators and secret/PII-filename/large-file negative tests.
7. Register governance verification in the existing ML gate and CI job.

## Out of scope

- Dataset download, scraping, participant collection or completed consent/withdrawal records.
- Direct identifiers, real screenshots, credentials, private archive paths or public release approval.
- Model fitting, calibration, thresholds, locked-test access or artifact registration.
- Standard Colab run manifests/checkpoint/resume implementation beyond defining the portable run schema.

## Verification target

- Registered ML gate and backend gate because the repository scanner is shared with backend tests.
- Registry/schema/fixture/taxonomy/withdrawal positive and negative tests.
- Secret/artifact/PII-filename/large-file scan, raw-path ignore checks, CSV/JSON integrity and diff checks.
