# De-identification Standard

- Use a random private participant identifier and store only its SHA-256 research key in manifests. Keep the linkage separately with stricter access.
- Remove or replace names, full phone/wallet identifiers, balances, references, account IDs, precise location and unrelated message content unless explicitly essential and approved.
- Use fictitious values in public fixtures. Redaction boxes must be irreversible in exported pixels; overlays or metadata-only hiding are insufficient.
- Strip unnecessary EXIF/metadata from derivatives while preserving the immutable private original and hash where approved.
- Keep original/derivative grouping so withdrawal and leakage prevention remain possible.
- Never put direct identifiers in filenames, object keys, run IDs, notebook outputs or logs.
- Review OCR text independently because pixel redaction alone does not remove copied transcripts.
- Treat pseudonymised data as private while a linkage or realistic re-identification route exists.
- Record de-identification method/version, reviewer and result privately; automated scanning is supporting evidence only.
