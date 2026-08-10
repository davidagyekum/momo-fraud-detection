# P08 session plan — reference import and verification

Date: 2026-08-10  
Branch: `codex/p08-reference-verification`  
Base: `19b38a04da7d4d977aaace85e80efc7612bbd88f`

## Scope

- Implement ADMIN-only private CSV upload, preview validation, invalid-row download, commit, list and detail APIs.
- Reuse P07 canonical normalization for provider/reference, amount/currency, Ghana phones and UTC timestamps.
- Add a versioned deterministic verification engine with field-level evidence, configured tolerances and reuse indicators.
- Persist a verification-only `PARTIAL` analysis after OCR confirmation while keeping fraud risk unset and all unavailable stages explicit.
- Replace the P05 inactive reference-import shell with an accessible operational portal workflow and add a user verification section to the mobile OCR completion flow.
- Add controlled demonstration data, API/UI tests, OpenAPI updates and traceability evidence.

## Boundaries

- Verification uses only authorised stored/imported records; no live MNO/provider connection is claimed.
- Verification status and fraud risk remain different records, API blocks and UI cards.
- No image analysis, fraud rule aggregation, model inference or training is implemented in P08.
- Google Colab remains the required environment for later P11/P12 training; this phase does not train a model.
