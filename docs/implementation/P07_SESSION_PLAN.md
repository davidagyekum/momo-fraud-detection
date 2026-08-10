# P07 Session Plan — OCR Review

## Scope lock

- Base: merged P06 `62f411aee2bd39a7d2feb8e49073ca4bdcf04922`.
- Branch: `codex/p07-ocr-review`.
- Requirements: FR-OCR-001 through FR-OCR-008.
- Backlog: P07-T001 through P07-T011.
- Boundary: OCR preprocessing, recognition, parsing, review and confirmation only. Image-forensics scoring, reference verification and model training remain in P09, P08 and P11/P12 respectively.

## Plan

1. Add pinned headless OpenCV and pytesseract runtime dependencies plus bounded OCR configuration.
2. Implement deterministic preprocessing variants, safe Tesseract invocation, variant scoring, generic/provider detection and canonical field parsing.
3. Persist immutable OCR evidence, selected private derivative, explicit degraded results and correction confirmations with idempotency/audit coverage.
4. Expose owner-only OCR run/review/confirmation APIs and the pre-analysis review guard; regenerate OpenAPI.
5. Build the authenticated Expo OCR review screen with private preview, editable validation states, correction reasons and offline/retry handling.
6. Add parser, pipeline, API, mobile and controlled evaluation coverage; measure only actual fixture extraction.
7. Run migration, backend, mobile, Docker/live and browser gates; update traceability, status, changelog, evidence and handoff before publication.

## Known preflight conditions

- Docker API image includes Tesseract 5.3.0 and is the authoritative local OCR execution environment.
- Tesseract is absent from the Windows host. This is not hidden; it supplies the required explicit unavailable/degraded-path test condition.
- GitHub Actions remains externally blocked by B-CI-001.
- Google Colab is reserved for actual P11/P12 model training under ADR-014; no training occurs in P07.
