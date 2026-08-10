# Stored reference CSV contract

This contract is for controlled or appropriately authorised reference-transaction exports used
by the prototype verifier. Importing this file does not create a live mobile-network operator
connection.

## Workflow

1. An `ADMIN` uploads a UTF-8 `.csv` file with an `Idempotency-Key` and a non-sensitive source
   label.
2. Validation canonicalises rows without creating reference transactions. Invalid rows are
   excluded and made available in a private, formula-safe error report.
3. An administrator reviews the counts and explicitly confirms commit. Only valid rows are
   inserted; the original upload, file SHA-256, counts, actor and timestamps remain evidential.

Use [`samples/reference_transactions_template.csv`](../../samples/reference_transactions_template.csv)
as the machine-readable header template.

## Columns

| Column | Required | Validation/canonical form |
| --- | --- | --- |
| `provider_code` | Yes | 1–50 uppercase letters, numbers or underscores after canonicalisation |
| `transaction_reference` | Yes | 6–50 canonical reference characters |
| `amount` | Yes | Non-negative decimal, stored to two decimal places |
| `currency` | Yes | Three-letter uppercase code, such as `GHS` |
| `sender_name` | No | Normalised uppercase text, maximum 150 characters |
| `sender_phone` | No | Ghana number canonicalised to E.164 |
| `receiver_name` | No | Normalised uppercase text, maximum 150 characters |
| `receiver_phone` | No | Ghana number canonicalised to E.164 |
| `occurred_at` | No | ISO 8601 or supported Ghana date/time, stored in UTC |
| `transaction_status` | No | Normalised uppercase text, maximum 50 characters |
| `source_system_id` | No | Source identifier, maximum 150 characters |

Unknown, blank or duplicate headers are file-level errors. Extra cells, invalid fields and
duplicate provider/reference/source combinations are row-level errors. The configured default
limits are 10 MiB and 100,000 rows.

## Matching policy

The verifier first uses exact canonical provider plus transaction reference. A provider-free
fallback is permitted only when the transaction reference identifies exactly one committed
record. Ambiguous candidates return `UNVERIFIED`; they are never selected silently. Amount,
currency, phones, timestamp and provider-normalised status are critical comparisons. Names use
the configured documented similarity threshold. Missing critical comparison data returns
`UNVERIFIED`, while a critical mismatch returns `MISMATCH`.

Responses expose masked values, field-level modes/tolerances/scores/reasons, the verifier and
rule-set versions, and warning codes. Raw imported rows and storage keys are not returned.
