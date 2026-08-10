# P09 session plan — deterministic image forensics

Date: 2026-08-10  
Branch: `codex/p09-image-forensics`  
Base: `36d39e0d59b4b36672890e51e22233a8ca01604e`

## Scope

- Implement a versioned deterministic service for safe metadata, duplicate, controlled recompression/ELA, noise residual, crop/layout and OCR token-alignment evidence.
- Persist each available or not-applicable signal with observed values, thresholds, severity, confidence, reason code, limitations and extractor version in the existing P02 `image_analyses` record.
- Preserve the original receipt byte-for-byte and generate only private, versioned diagnostic derivatives.
- Add owner/staff evidence projection and authorised diagnostic retrieval without exposing object keys or other users' identities.
- Add a transparent supporting-evidence summary that cannot produce or claim a final fraud class.
- Create controlled manipulated fixtures and regression, ownership, private-storage and unchanged-original tests.
- Document the evidence catalogue and scientific limitations of metadata, ELA, noise and template/layout heuristics.

## Boundaries

- P09 produces supporting deterministic evidence, not proof of fraud and not a final fraud-risk classification.
- A missing EXIF block is neutral. Editing-software hints are contextual only.
- Low-quality, tiny or unsupported inputs return explicit not-applicable evidence instead of invented values.
- No TensorFlow/Keras or scikit-learn model is trained, loaded or inferred in P09.
- Google Colab remains the required environment for later P11/P12 training; local work proceeds only through P10 before the training handoff.
