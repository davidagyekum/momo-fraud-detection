# P06 Session Plan — Secure Receipt Capture and Private Upload

## Scope lock

- Branch: `codex/p06-receipt-upload`
- Base: P05 merge `1d7891fd2087a8f5412d864a66dafc939b967a60`
- Requirements: FR-UPL-001 through FR-UPL-007 and NFR-SEC-003
- Backlog: P06-T001 through P06-T011
- In scope: camera/gallery selection, native permissions, preview/replace/remove, multipart upload, strict hostile-image validation, immutable private original, EXIF-oriented thumbnail, hashes/quality warnings, duplicate candidate signal, idempotency, atomic database/storage behavior, authenticated retrieval, audit and abuse tests.
- Out of scope: OCR execution/extraction/correction (P07), reference verification (P08), forensic tamper maps (P09), model training/inference (P11/P12) and end-to-end risk aggregation (P13).

## Implementation sequence

1. Pin Pillow under Python 3.12 and add validated upload configuration with safe defaults.
2. Implement isolated image validation/metadata/hash/quality/thumbnail services with hostile fixtures and no storage side effects.
3. Implement the transaction repository/service boundary: generated object keys, idempotency claim/replay/conflict, duplicate candidate queries, private writes, atomic rows, cleanup and audit.
4. Add authenticated multipart upload and private original/thumbnail stream routes with OpenAPI schemas and ownership/role checks.
5. Reuse the existing transaction/receipt/idempotency schema unless behavior proves a migration is necessary; no speculative migration.
6. Add integration and security tests for valid JPEG/PNG/WEBP, fake MIME/extension, corruption, trailing/polyglot bytes, size/pixel/frame limits, path traversal, duplicate privacy, idempotency, cross-user access and injected cleanup failures.
7. Add Expo ImagePicker camera/gallery permissions, preview/replace/remove, guidance, upload mutation/progress states and authenticated private preview reopening through the existing session/query architecture.
8. Run backend, migration, mobile, contract, secret, audit and live Docker/device-web-fallback gates; update evidence, traceability, status, changelog and handoff before commit/push/PR.

## Fixed safety decisions

- Original bytes are immutable; EXIF transpose and metadata stripping affect only the derived thumbnail.
- User filenames are display-only after sanitisation and never participate in object-key construction.
- Client MIME, dimensions, filename and ownership identifiers are never trusted.
- Duplicate responses expose only candidate signals/counts, never another owner, transaction or object key.
- Quality warnings are usability/OCR-readiness hints and never a fraud classification.
- Receipt bytes are delivered only after server-side authentication and ownership/role checks, with `nosniff`, private caching and generated download names.
- Missing storage or cleanup integrity produces an explicit dependency/failure state, never a fake successful upload.

## Phase gates

- Ruff format/lint, strict mypy and backend coverage.
- Clean/previous migration upgrade and Alembic drift check (even if no migration is added).
- OpenAPI drift check.
- Upload abuse/security matrix and database/storage rollback injection.
- Mobile format/lint/type/Jest/static export and token policy.
- Live local Docker USER upload and reopen-private-preview flow.
- No private receipt, credential or runtime object is committed.
