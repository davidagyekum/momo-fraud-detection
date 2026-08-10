# ML dataset governance

This directory may contain only small, sanitised synthetic or controlled research fixtures approved for Git. Raw authorised receipts, derived private receipts and credentials belong in an access-controlled external location such as an institution-approved private bucket or mounted Google Drive folder; they must never be committed.

## Required record for every source

Before a source enters a manifest, its dataset card must record:

- accountable owner and approval date;
- `real_authorised`, `synthetic` or `controlled_tamper` source type;
- consent or licence reference and permitted research purpose;
- whether personal data is present and how it was anonymised;
- collection origin, parent/source grouping method and label provenance;
- retention or review date and a revocation/deletion procedure;
- permitted storage location and access roles;
- known population, provider and manipulation limitations.

Unknown or disputed consent/licence status is a stop condition. Do not replace it with a guessed reference.

## Manifest and storage rules

- Use `manifest.csv` with the schema in `samples/receipt_dataset_manifest.csv`.
- `relative_path` is for committed sanitised fixtures only. Authorised real data must use an opaque `private_object_id` resolved outside Git.
- The manifest must contain no real names, phone numbers, transaction references or storage credentials.
- Each original receipt and all controlled/augmented derivatives share one `source_group_id` and one split.
- Assign source groups to train/validation/test before preprocessing fit or augmentation.
- Augmentation is training-only. Validation and test samples remain held out and unchanged.
- Hash every image with SHA-256 and record the parent, operations, coordinates and deterministic seed for every controlled derivative.
- A training run must record the canonical manifest hash, source-group split hash, seed, dependency versions, exact Git commit and output artifact hash.

## Private-data lifecycle

Keep raw and derived authorised data in separate private prefixes with least-privilege access and audit logging. The dataset card must name the retention/review rule and revocation process approved by the institution; this project does not invent a legal retention period. If permission is withdrawn, remove the affected private objects and all derivatives, rebuild manifests/splits, and invalidate training artifacts that depended on them.

Run `scripts/verify.py --ml` before any training handoff. A valid report proves schema and leakage checks passed; it does not prove that the dataset is representative or that a model is accurate.

## Ghana mobile-money fraud corpus

The separate Ghana fraud-message collection workspace lives at the ignored path
`ml/data/authorized/ghana_momo_fraud/`. Its protocol is documented in
`docs/dataset-cards/GHANA_MOMO_FRAUD_DATASET_PROTOCOL.md` and its validator is
`scripts/ghana_dataset.py`.

This corpus uses `fraudulent`, `genuine` and `suspicious` labels and is not a
replacement for the P12 `ORIGINAL` versus `CONTROLLED_TAMPERED` dataset. Real
authorised rows must use private object IDs in the canonical manifest; local
redacted copies are for controlled research work only and are never committed.
