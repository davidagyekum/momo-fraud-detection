# P07 OCR and correction-workflow evidence

Date: 2026-08-10  
Branch: `codex/p07-ocr-review`  
Base: `62f411aee2bd39a7d2feb8e49073ca4bdcf04922`

## Implemented boundary

- Versioned, deterministic OpenCV preprocessing creates private derivatives while verifying that the original receipt SHA-256 is unchanged.
- Tesseract `image_to_data` retains raw text, token confidence, bounding boxes and line identifiers. Candidate selection considers confidence, required-field coverage, provider confidence and text sanity.
- Versioned provider detection supports MTN MoMo, Telecel Cash and AirtelTigo Money, with an explicit generic-template fallback.
- Canonical parsing covers transaction reference, amount/currency, sender and receiver names/phones, occurrence time, provider and status.
- The owner-only review API exposes understandable field confidence and warnings without exposing storage keys or token-coordinate evidence.
- User corrections create a separate immutable confirmation snapshot containing old value, new value and required reason. Automated OCR evidence is never rewritten.
- Analysis requests are rejected until OCR review is confirmed. After confirmation, the endpoint returns an explicit `ANALYSIS_PIPELINE_UNAVAILABLE` state because orchestration belongs to P13.
- The Expo review screen provides authenticated loading, offline/retry, partial, error, editable, confirmation and permission-denied behavior, plus a private zoomable receipt preview.

OCR output is extraction evidence. It is not fraud risk, transaction verification, proof of receipt authenticity or live MNO verification.

## Controlled OCR evaluation

Command:

```powershell
docker run --rm -v "C:\Users\David_A\Desktop\CS\momoFraudDetection:/workspace" -w /workspace -e PYTHONPATH=/workspace/services/api/src momo-fdvs-api:latest python scripts/evaluate_ocr.py
```

Environment: non-root API image, Tesseract 5.3.0, OpenCV headless, Pillow and deterministic seed `20260810`.

| Fixture | Selected variant | Reference | Amount | Currency | Date/time | Result/warnings |
|---|---|---:|---:|---:|---:|---|
| Clean | `BASE_RESIZED` | Pass | Pass | Pass | Pass | Complete |
| Rotated 4 degrees | `ADAPTIVE_BINARY` | Pass | Pass | Pass | Pass | Complete |
| Low contrast | `GRAY_CLAHE` | Pass | Pass | Pass | Pass | Complete |
| Noisy | `BASE_RESIZED` | Pass | Pass | Pass | Pass | Complete; one non-selected candidate reported `OCR_ENGINE_TIMEOUT` |
| Cropped | `BASE_RESIZED` | Pass | Pass | Pass | Pass | Complete |

- Required-field matches: **20 / 20**.
- Required-field extraction accuracy on this declared controlled set: **100.00%**.
- Per-field accuracy for transaction reference, amount, currency and occurrence time: **100.00% each**.
- The noisy receipt demonstrates candidate-level degradation: a bounded Tesseract timeout is retained as a warning while another deterministic candidate supplies the complete result.

## Verification summary

- Backend registered gate: Ruff format/lint, strict mypy, 79 tests, 89.04% total coverage, OpenAPI drift and engineering ER checks passed.
- Focused OCR suite: 12 unit/integration tests passed, including original-hash integrity, unavailable-engine, immutable rerun, ownership, corrections, audit and analysis-readiness behavior.
- Mobile registered gate: Prettier, ESLint, strict TypeScript, 46 Jest tests and the 23-route Expo web export passed; covered libraries reached 89.23% statements, 70.34% branches, 91.66% functions and 92.65% lines.
- Docker image contains Tesseract 5.3.0. Host-side missing-Tesseract behavior is retained as a tested explicit partial state.
- Chrome opened `/ocr/00000000-0000-0000-0000-000000000001`; the authenticated route guard redirected the volatile unauthenticated session to `/login`, rendered the complete sign-in DOM and emitted no warning/error console entry. The CDP navigation command timed out after the redirect, so no screenshot or authenticated file-picker flow is claimed.

## Limitations

- The fixtures are controlled synthetic generic Ghana-style receipts and are not representative of real provider receipt diversity.
- No private or production receipt dataset was used, and no provider-wide generalisation is claimed.
- This report measures OCR extraction only. It does not report fraud-model accuracy, F1, deployment success or live MNO verification.
- No ML model was trained in P07. Per ADR-014, actual P11/P12 training remains reserved for Google Colab after P10.
- Chrome could verify protected-route behavior, DOM and console output, but an end-to-end authenticated receipt selection is not claimed because web refresh deliberately clears the memory-only access token and the Chrome automation surface did not complete the native file-picker flow.
