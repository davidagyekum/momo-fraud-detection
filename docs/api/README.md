# API contract workflow

The committed contract is `packages/api-client/openapi.json`. It is generated from the registered Flask-Smorest schemas:

```powershell
py -3.12 scripts/export_openapi.py
py -3.12 scripts/export_openapi.py --check
```

Do not edit the JSON snapshot manually. Client-visible changes must update schemas, regenerate this document, update generated consumers and add contract tests.

## P07 OCR lifecycle

The owner-only OCR contract is deliberately stateful and idempotent:

1. `POST /api/v1/transactions/{transaction_id}/ocr` runs or replays a bounded OCR result for a private receipt. `Idempotency-Key` is required.
2. `GET /api/v1/transactions/{transaction_id}/ocr-review` returns the latest owner-safe review projection. Raw text is private; storage keys and token-coordinate evidence are not returned to the mobile client.
3. `POST /api/v1/transactions/{transaction_id}/ocr-confirmations` creates or replays an immutable canonical confirmation. Reasons are required for changed fields.
4. `POST /api/v1/transactions/{transaction_id}/analyses` rejects unreviewed OCR with `OCR_REVIEW_REQUIRED`. P07 returns `ANALYSIS_PIPELINE_UNAVAILABLE` after review because the actual orchestration belongs to P13.

`OCR_PARTIAL` and warning codes such as `OCR_ENGINE_UNAVAILABLE`, `OCR_ENGINE_TIMEOUT`, `OCR_ENGINE_FAILED` and `CRITICAL_OCR_FIELDS_MISSING` are explicit degraded states, not successful extraction claims. OCR status is separate from fraud risk and transaction verification.
