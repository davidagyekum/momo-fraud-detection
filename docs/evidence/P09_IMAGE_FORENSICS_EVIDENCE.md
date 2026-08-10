# P09 deterministic image-forensics evidence

## Purpose and boundary

P09 records explainable supporting image evidence independently of a trained CNN. It does not
produce a fraud class, image-tamper probability or legal determination. A single weak signal
cannot classify a receipt as fraudulent. Automated evidence is stored immutably; later human
review adds a separate decision.

Pipeline version: `deterministic-image-forensics-v1`  
Feature schema: `deterministic-image-features-v1`

## Signal catalogue

| Domain | Reason code | Meaning | Default severity |
|---|---|---|---|
| Metadata | `DECODED_IMAGE_METADATA_CONSISTENCY` | Decoded format/dimensions are compared with the validated stored record. | Informational or medium |
| Metadata | `METADATA_ABSENT` | EXIF is missing; this is explicitly neutral. | Informational |
| Metadata | `METADATA_PRESENT` | Allowlisted technical metadata exists. | Informational |
| Metadata | `EDITING_SOFTWARE_HINT` | An allowlisted editing-software encoder term is present; contextual only. | Low |
| Duplicate | `EXACT_RECEIPT_REUSE` | Another stored receipt has the same SHA-256; only a count is exposed. | Medium |
| Duplicate | `NEAR_RECEIPT_REUSE` | Another perceptual hash is within the configured Hamming distance. | Low |
| Compression | `RECOMPRESSION_REGIONAL_INCONSISTENCY` | Controlled JPEG recompression has uneven regional absolute error. | Low |
| Compression | `RECOMPRESSION_NOT_APPLICABLE` | The image is too small for stable recompression evidence. | Informational |
| Residual | `NOISE_RESIDUAL_INCONSISTENCY` | Denoising residual energy varies across regions. | Low |
| Residual | `NOISE_RESIDUAL_NOT_APPLICABLE` | Size/quality is insufficient; no residual value is invented. | Informational |
| Layout | `TEXT_ALIGNMENT_INCONSISTENCY` | OCR baselines, box heights or cross-line overlaps exceed configured thresholds. | Medium |
| Layout | `POSSIBLE_CROP_OR_EDGE_INCOMPLETENESS` | Detected text is unusually close to an image edge. | Low |
| Layout | `OCR_LAYOUT_NOT_APPLICABLE` | Too few valid OCR boxes exist; no layout value is invented. | Informational |
| Quality | `IMAGE_QUALITY_CONTEXT` | Upload-time quality warnings reduce evidence reliability. | Informational or low |
| Quality | `UNUSUAL_RECEIPT_ASPECT_RATIO` | The broad generic aspect-ratio range is exceeded. | Low |

Every signal stores extractor version, status, severity, observed values, threshold/rule,
confidence, plain-language reason and limitations. Thresholds and the complete feature schema
version are snapshotted on the immutable analysis run.

## Private diagnostic artefacts

Controlled ELA and noise-residual maps are stored as versioned private `ReceiptDerivative`
records under generated object keys. Only ADMIN/INVESTIGATOR roles receive protected URLs and
may stream `variant=ela` or `variant=noise-map`; access and denial are audited. Normal users may
read the understandable evidence projection but receive no diagnostic URL. No derivative is
served from a public static path.

## Controlled regression evidence

- Deterministic unit fixtures use seed `20260810` and exercise regional recompression/noise,
  misaligned OCR boxes, crop proximity, neutral absent metadata and tiny-image not-applicable
  behavior.
- PostgreSQL integration tests persist a complete image-analysis record, verify null risk/class
  and tamper probability, stream both protected diagnostics, prove owner/outsider denial,
  verify the original bytes remain identical and prove the database mutation trigger rejects an
  update to automated image evidence.
- Missing private source bytes return `IMAGE_STORAGE_UNAVAILABLE` and preserve completed
  reference verification; no forensic values are fabricated.

No accuracy, precision, recall, F1 or provider-wide detection metric is claimed in P09. These
tests demonstrate deterministic behavior against controlled fixtures, not field performance.

## Scientific limitations

- Screenshots commonly lose EXIF and undergo recompression; missing metadata is neutral.
- Editing-software metadata may result from legitimate export or optimisation.
- ELA is sensitive to prior compression and does not localise every edit.
- Camera processing, text density and compression can change noise residuals.
- OCR box errors can create apparent alignment or crop anomalies.
- Provider templates vary, so generic aspect and edge checks are deliberately weak.
- Duplicate matches may represent a legitimate re-upload and never expose another user's data.
- Consequential cases still require authorised provider confirmation and human review.
