# PR11 Data Threat Model

## Assets and trust boundaries

Protected assets include raw screenshots, OCR text, participant/contact and consent records, withdrawal keys, external archives/credentials, de-identified derivatives, split manifests, checkpoints and model artifacts. Trust boundaries exist between participants, browsers/devices, private storage, Colab VM/Drive, repository/CI, annotators/researchers and public release.

## Threats and controls

| Threat | Impact | Preventive/detective controls | Residual action |
|---|---|---|---|
| Direct identifier in Git or filename | Irreversible disclosure/history | Ignore rules, content scan, PII-filename scan, fictitious fixtures only | Stop, remove from publication, rotate exposed credentials, follow incident process; do not rewrite shared history without approval |
| Unknown licence treated as permission | Unauthorised use/redistribution | Registry fails closed; disabled/not-acquired state; dataset card terms review | Data steward verifies authoritative terms or source remains disabled |
| Internal consent treated as public release | Participant harm | Separate `internal_only`/`release_approved`; publication checklist | Keep private or obtain separate explicit scope |
| Withdrawal not propagated | Continued unauthorised processing | Pseudonymous key, withdrawal ledger, manifest/split/artifact rebuild rule | Disable affected runs/models until rebuild finishes |
| Source-group leakage | Inflated metrics | Frozen group split schema, disjoint validator, parent/edit grouping | Regenerate split and invalidate metrics |
| Missing balance/history converted to zero | Model distortion | Nullable transaction schema and PR10 evidence contract | Reject row/pipeline rather than impute outside fitted pipeline |
| Malicious/corrupt archive or image | Resource exhaustion/code exploitation | Private quarantine, hash/size/type validation, bounded decoders, no untrusted pickle | Delete/quarantine and investigate |
| Colab/Drive loss or over-sharing | Disclosure/lost provenance | Private Drive prefixes, least privilege, no secrets/output cells, later atomic manifests/checkpoints | Revoke links/tokens and restart from verified copies |
| Model memorises identifiers/templates | Privacy and spurious results | De-identification, group splits, slice/error review, no raw text identifiers | Reject artifact and revise data/features |
| Released aggregate enables re-identification | Participant harm | Minimum aggregation, no small identifying slices, publication review | Suppress/merge slice and reassess release |

## Security assumptions and limitations

The project assumes institution-approved private storage and identity controls will be supplied before collection. Hashing a participant identifier is pseudonymisation, not anonymisation, when a linkage record exists. Secret/filename scanning reduces accidental commits but cannot prove a dataset is lawful, anonymous or safe. Institutional/supervisor review remains required for actual participant collection, retention and incident deadlines.
