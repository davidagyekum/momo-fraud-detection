# 07 — OCR, Image Analysis, Machine Learning and Verification Specification

## 1. Analytical philosophy

MoMo-FDVS is a hybrid evidence system. No single component is sufficient:

- OCR reads visible text but does not prove authenticity.
- Image forensics can reveal inconsistencies but can be affected by normal compression, screenshots and device processing.
- Machine learning estimates patterns found in its training scope but cannot generalise beyond the evidence without validation.
- Reference matching can confirm consistency with an available record but cannot operate when no trustworthy record exists.
- Human review is required for consequential or ambiguous cases.

Every component must return both a machine-readable result and an explicit limitation/status.

## 2. End-to-end pipeline

```text
Private original receipt
    ↓
Decode/quality checks
    ↓
Preprocessing variants
    ↓
Tesseract tokens + confidence + bounding boxes
    ↓
Template detection and field parsing
    ↓
User confirms/corrects fields
    ↓
Analysis snapshot
    ├── Reference verification
    ├── Deterministic image evidence
    ├── CNN image tampering inference
    ├── Structured feature assembly
    ├── Random Forest inference
    └── Versioned rule evaluation
    ↓
Risk aggregation + top reasons
    ↓
Persisted risk result + separate verification result
    ↓
User result / investigator evidence
```

## 3. Receipt decoding and quality

### 3.1 Decode

- Read bytes from private storage.
- Verify expected SHA-256 before processing.
- Decode with Pillow/OpenCV using safe limits.
- Apply EXIF transpose to a derived image.
- Convert to a defined colour representation.
- Reject or safely flatten unsupported animation/multi-frame content according to upload policy.
- Record decoder/library versions.

### 3.2 Quality features

Suggested versioned features:

- width, height, aspect ratio;
- grayscale mean/std;
- contrast range;
- Laplacian variance or equivalent sharpness proxy;
- estimated text/edge density;
- clipping/overexposure/underexposure proportion;
- possible crop/edge completeness;
- compression format/quality proxy;
- OCR-scale suitability.

Quality features produce warnings such as:

- `IMAGE_TOO_SMALL`;
- `IMAGE_BLURRY`;
- `IMAGE_LOW_CONTRAST`;
- `RECEIPT_EDGES_MISSING`;
- `IMAGE_OVERCOMPRESSED`.

Quality warnings are not fraud labels.

## 4. OCR preprocessing

Create several deterministic variants from the same oriented input:

1. `BASE_RESIZED`
   - preserve aspect;
   - enlarge small text to target minimum scale;
   - avoid uncontrolled repeated interpolation.

2. `GRAY_CLAHE`
   - grayscale;
   - local contrast enhancement with versioned parameters.

3. `DENOISE_SHARPEN`
   - bounded denoise;
   - unsharp mask or controlled sharpening.

4. `OTSU_BINARY`
   - global Otsu threshold.

5. `ADAPTIVE_BINARY`
   - adaptive threshold for uneven lighting.

6. `DESKEWED_*`
   - optional deskew when a reliable angle is detected.

Store only necessary derivatives according to retention; always store preprocessing metadata.

### 4.1 Variant selection

For each variant run OCR and calculate a selection score from:

- mean/median token confidence;
- required-field parser coverage;
- valid transaction-reference candidate;
- valid amount candidate;
- date/time candidate;
- phone candidate;
- text length/density sanity;
- template anchor matches.

Do not select only by mean OCR confidence because a high-confidence irrelevant header can hide missing transaction fields. Store the winning variant plus candidate summary.

## 5. Tesseract invocation

- Use `image_to_data`/TSV-equivalent to retain word text, confidence and bounding box.
- Set language/config based on supported content; begin with English and documented receipt symbols.
- Use a small evaluated set of page-segmentation modes, not an unbounded brute-force search.
- Set a process timeout.
- Capture safe stderr/error code.
- Record Tesseract version and configuration.
- Never build a shell command with untrusted filename or options.

Token structure:

```json
{
  "text": "125.00",
  "confidence": 91.2,
  "x": 413,
  "y": 622,
  "width": 144,
  "height": 38,
  "line_id": "..."
}
```

## 6. Provider/template detection

Each template version defines:

- provider code;
- optional anchor phrases;
- expected field labels;
- expected regions/relative order;
- regex patterns;
- date formats;
- amount/currency formats;
- transaction-reference patterns;
- phone/name parsing hints;
- layout tolerances.

Detection returns:

- selected template ID/version;
- provider confidence;
- matched anchors;
- fallback warning.

The generic template must permit extraction when no provider-specific layout is available.

## 7. Field extraction and normalisation

### 7.1 Canonical field schema

```json
{
  "provider_code": "GENERIC_MOMO",
  "transaction_reference": "ABC123456",
  "amount": "125.00",
  "currency": "GHS",
  "sender_name": "DEMO SENDER",
  "sender_phone": "+233240000002",
  "receiver_name": "DEMO RECEIVER",
  "receiver_phone": "+233240000001",
  "occurred_at": "2026-08-08T14:30:00Z",
  "status_text": "SUCCESSFUL"
}
```

Every field also has:

- raw candidate;
- canonical value;
- confidence;
- source token IDs/bounds;
- validation state;
- warnings;
- parser version.

### 7.2 Transaction reference

- normalise whitespace/separators/case only when the provider rules permit;
- preserve raw value;
- enforce provider/generic length and character checks;
- avoid replacing ambiguous characters automatically unless confidence and context justify it; otherwise flag review.

### 7.3 Amount

- recognise `GH₵`, `GHS`, currency symbol variants and thousands separators;
- parse with `Decimal`;
- reject negative/unreasonable formats according to validation, not fraud logic;
- retain two-decimal canonical string;
- avoid selecting fees/balance as transaction amount by using label/layout context.

### 7.4 Phone

- remove display separators;
- convert recognised `0XXXXXXXXX` Ghana format to `+233XXXXXXXXX`;
- validate digit count/prefix conservatively;
- preserve raw;
- display masked in non-owner/staff list contexts.

### 7.5 Date/time

- parse template-known formats first;
- retain raw date/time;
- record inferred timezone warning;
- reject impossible dates;
- store canonical UTC when possible;
- do not invent a year/date missing from the receipt without explicit warning.

### 7.6 Names

- Unicode normalisation;
- collapse whitespace;
- uppercase/casefold comparison copy;
- preserve display/raw;
- avoid aggressive phonetic correction;
- fuzzy comparison belongs to verification, not OCR overwrite.

## 8. OCR confidence

Field confidence can combine:

- source token confidences;
- regex/format validity;
- label association;
- template-region match;
- candidate ambiguity;
- cross-field consistency.

The exact formula is versioned and evaluated. Initial review threshold may be `0.75`, but must remain configurable.

Required-field accuracy evaluation:

- exact or normalised match per required field;
- field present/absent;
- macro/micro field accuracy;
- per-field accuracy;
- provider/template breakdown;
- unreadable/unsupported category.

The target of 90% is a goal, not a value to report until measured on the declared set.

### 8.1 Deterministic OCR-text fraud assessment

After recognition and before user confirmation, run the versioned
`ghana-momo-obvious-scam-rules-v1` assessment over immutable raw OCR text. The
initial high-precision rules cover bounded combinations such as a request to
disclose a PIN/OTP, a wrong-transfer return lure, a payment demanded to unlock
funds, an account threat plus external action, an account-action link, an
unverified contact redirect, a prize/action lure and urgency pressure. Negated
official advisories such as “never share your PIN” must not trigger the secret
request rule.

The assessment must:

- retain schema and ruleset versions;
- use token confidence only as evidence-quality context, never as a fraud label;
- return only `SUSPICIOUS`, `FRAUDULENT` or null for no decisive rule;
- keep its integer rule score explicitly non-probabilistic;
- persist fixed reason codes and fixed public summaries, never match spans or
  extracted private values;
- return `UNAVAILABLE` for missing/legacy evidence rather than silently
  recomputing history; and
- feed the existing semantic-rules analysis stage without changing the separate
  reference-verification record.

No-match text is inconclusive, not evidence of genuineness. Missing accepted
image or structured models still produces a `PARTIAL` analysis even when the
categorical text signal maps to a high review band.

`PARTIAL` describes degraded component availability; it does not make a low,
medium or high fraud-risk band inconclusive. Persist and project
`conclusion_status=CONCLUSIVE` with `component_status=DEGRADED` for those runs,
and reserve `ANALYSIS_EVIDENCE_INCONCLUSIVE` for the `inconclusive` band.

## 9. User correction

The confirmed field snapshot is authoritative input to verification and structured features, but correction itself is evidence:

Suggested features:

- correction count;
- corrected critical-field count;
- magnitude of amount/reference change;
- confidence before correction;
- time spent/repeated confirmation, only if privacy-approved and genuinely useful.

Do not treat a normal user correction as fraud by itself.

## 10. Deterministic image evidence

### 10.1 Metadata

Capture only safe technical fields:

- format;
- dimensions;
- colour mode;
- EXIF presence;
- software/encoder string when present;
- screenshot-like dimensions/format hints.

Rules:

- no metadata -> neutral;
- editing-software metadata -> supporting evidence only;
- metadata conflicts with decoded image -> stronger inconsistency, still contextual.

### 10.2 Exact and near duplicate

- SHA-256 equality for exact duplicate;
- perceptual hash/Hamming distance for near duplicate;
- compare within authorised system scope;
- return counts/reuse reason without exposing another user's identity;
- distinguish repeated legitimate user re-upload from suspicious reference reuse through policy.

### 10.3 Recompression / ELA

Procedure:

1. convert a derived copy to a controlled JPEG quality;
2. calculate absolute difference;
3. normalise safely;
4. summarise global and regional statistics;
5. optionally retain a private visual derivative.

Features may include mean, max percentile, regional variance and connected high-error region count. ELA is weak on already recompressed screenshots and must not be treated as proof.

### 10.4 Noise residual consistency

- create denoised estimate;
- calculate residual;
- partition into regions;
- compare regional statistics;
- exclude blank/text-heavy regions where appropriate;
- mark not-applicable for tiny/overcompressed images.

### 10.5 Layout and text consistency

Using OCR boxes/template:

- expected label-value relative positions;
- line baseline deviation;
- character/box height variation;
- spacing irregularity;
- overlapping boxes;
- inconsistent alignment within one field;
- unexpected missing/duplicated regions;
- crop/completeness.

These are numerical features plus reason codes.

### 10.6 Evidence object

```json
{
  "code": "TEXT_ALIGNMENT_INCONSISTENCY",
  "extractor_version": "layout-1.0.0",
  "status": "TRIGGERED",
  "severity": "MEDIUM",
  "observed": {"baseline_deviation": 0.24},
  "threshold": {"baseline_deviation": 0.18},
  "confidence": 0.72,
  "reason": "Some transaction text is not aligned with nearby fields.",
  "limitations": []
}
```

## 11. Dataset manifest

Minimum columns:

- `sample_id`;
- `relative_path` or private object ID;
- `sha256`;
- `source_group_id`;
- `parent_sample_id`;
- `source_type`: real_authorised / synthetic / controlled_tamper;
- `provider_code`;
- `label`: genuine / suspicious / fraudulent, or binary image label;
- `tamper_operations`;
- `split`: train / validation / test;
- `consent_or_licence_reference`;
- `contains_personal_data`;
- `anonymisation_status`;
- `generated_seed`;
- `notes`.

The manifest itself must not expose private names/phones/references.

## 12. Controlled sample generation

A generator may create generic receipt layouts with fake values, timestamps and references. It must not falsely represent samples as actual MNO receipts.

Controlled manipulations:

- replace amount;
- replace transaction reference;
- replace name/phone;
- clone/paste a text region;
- crop header/footer;
- shift/misalign a field;
- alter font-size/weight;
- add inconsistent blur/noise;
- recompress;
- compose a near-duplicate with one critical change.

For each derived image:

- retain parent/source group;
- record operations and coordinates;
- use deterministic seed;
- keep parent and all derivatives in one split;
- never apply the generator to test data after the split to inflate sample count.

## 13. Label policy

### Image model

Initial task: binary `ORIGINAL/UNTAMPERED` versus `CONTROLLED_TAMPERED`. If real labels are uncertain, report the model only as controlled-tamper detection.

### Structured model

Three classes:

- `GENUINE`: labelled/controlled low-risk evidence with trustworthy source;
- `SUSPICIOUS`: ambiguous, incomplete, low-quality or conflicting evidence requiring review;
- `FRAUDULENT`: confirmed/controlled manipulation or appropriately adjudicated fraudulent sample.

Labels from automated rules alone must not be used as ground truth for a model that then claims independence from those rules. Record label provenance and reviewer agreement where real data is used.

## 14. Split and leakage prevention

1. Group by original/source receipt or event.
2. Assign groups to train/validation/test.
3. Freeze split files and hash them.
4. Fit imputer/encoder/scaler only on training.
5. Apply augmentation only to training.
6. Tune only with training/validation.
7. Use test once for final model report.
8. Keep repeated imports/near duplicates in the same group.
9. Record random seed and library versions.
10. Add an automated assertion that group intersections are empty.

For small data, use stratified group cross-validation for development while preserving a final group-held-out test set.

## 15. Structured feature schema

Version the exact list and ordering. Candidate features:

### OCR/field features

- required field coverage;
- mean/min critical-field confidence;
- provider confidence;
- critical correction count;
- total correction count;
- transaction-reference validity;
- amount validity;
- phone validity;
- timestamp validity;
- status-text consistency;
- OCR text density/length;
- template anchor coverage.

### Image/quality features

- blur/sharpness;
- contrast;
- aspect ratio/template deviation;
- crop/completeness;
- metadata inconsistency count;
- ELA summary values;
- noise regional variance;
- text alignment/box variation;
- exact duplicate count;
- nearest perceptual-hash distance;
- CNN tamper probability and availability flag.

### Verification features

- reference candidate found;
- amount match;
- currency match;
- sender/receiver phone match;
- sender/receiver name similarity;
- timestamp difference;
- reference status match;
- mismatch count;
- reused reference count.

### Missingness

Include explicit missing/not-applicable indicators rather than silently converting all missing evidence to zero.

Do not include:

- final human case decision when predicting pre-review risk;
- final risk class;
- user identity;
- raw phone/reference/name;
- features calculated using the test label;
- post-outcome information unavailable at prediction time.

## 16. Structured classifier

### 16.1 Baseline

Use a scikit-learn Pipeline with:

- column selection;
- numeric imputation;
- categorical encoding;
- optional scaling where relevant;
- `RandomForestClassifier` with class weights and deterministic random state.

Random Forest is selected because it handles nonlinear interactions and mixed engineered evidence and can provide useful feature-importance diagnostics, but its probabilities may require calibration.

### 16.2 Output

Three probabilities:

```json
{
  "GENUINE": 0.22,
  "SUSPICIOUS": 0.61,
  "FRAUDULENT": 0.17
}
```

For the scalar risk component:

`p_ml = P(FRAUDULENT) + 0.5 × P(SUSPICIOUS)`

Clamp to `[0,1]`. Store the full probability vector and scalar transformation version.

### 16.3 Calibration

Evaluate probability reliability. If calibration improves validation performance, use a documented calibration method trained only on training/validation data. Store calibration as part of the artifact pipeline.

### 16.4 Explainability

For users, provide evidence-based reason codes from input features/rules, not unstable raw feature importance. For staff/model cards, permutation importance or a documented compatible explanation may be reported on validation/test data. Avoid claiming causality.

## 17. CNN image classifier

### 17.1 Initial configuration

- input: configurable, initial 224×224 RGB;
- deterministic decode/resize/normalise;
- backbone: MobileNetV3Small or documented compatible transfer-learning model;
- head: global pooling, regularisation and binary output;
- loss: binary cross-entropy or documented alternative;
- metrics: precision, recall, F1 derived from predictions, PR-AUC where useful;
- class weighting/sampling based on training distribution;
- early stopping and best validation checkpoint.

### 17.2 Training stages

1. Train classification head with frozen backbone.
2. Optionally unfreeze a small top block with low learning rate.
3. Select checkpoint on validation criterion.
4. Evaluate once on held-out test.
5. Export `.keras` artifact and preprocessing metadata.
6. Hash and register.

### 17.3 Output

`p_img = P(TAMPERED)`.

If the model is not available:

- status `UNAVAILABLE`;
- `p_img` remains null;
- aggregation follows the partial-evidence policy;
- UI discloses that the image model did not run.

### 17.4 Heatmaps

Grad-CAM or similar may be generated for investigators as an exploratory aid. It must be labelled as model attention/supporting evidence, not the precise location/proof of editing.

## 18. Reference verification

### 18.1 Candidate lookup

Preferred:

1. canonical provider + transaction reference;
2. source-system ID when supplied;
3. safe provider-specific fallback only when documented.

A fuzzy transaction-reference lookup must never silently choose among multiple candidates. Return ambiguous/unverified and require review.

### 18.2 Field comparison

For each field store:

- extracted/confirmed value, masked where appropriate;
- reference value, masked;
- comparison mode;
- tolerance;
- match result;
- score/similarity;
- reason.

Suggested policy:

- reference: exact canonical match;
- amount: exact decimal or configured small tolerance only if justified;
- currency: exact;
- phone: exact E.164 when present;
- name: normalised exact first, then documented fuzzy threshold;
- timestamp: absolute difference within configured minutes/hours;
- status: provider-normalised mapping.

### 18.3 Status

- candidate missing/ambiguous -> `UNVERIFIED`;
- candidate found and all required available comparisons match -> `VERIFIED`;
- candidate found and any critical comparison mismatches -> `MISMATCH`;
- candidate found but data insufficient -> `UNVERIFIED` with warnings.

Verification version/tolerances are persisted.

## 19. Rule engine

Rules are versioned and declarative where practical.

Examples:

- `REFERENCE_AMOUNT_MISMATCH`;
- `REFERENCE_RECEIVER_PHONE_MISMATCH`;
- `RECEIPT_EXACT_DUPLICATE`;
- `RECEIPT_NEAR_DUPLICATE_CRITICAL_FIELD_CHANGED`;
- `TRANSACTION_REFERENCE_REUSED`;
- `CRITICAL_OCR_FIELDS_MISSING`;
- `TEMPLATE_LAYOUT_INCONSISTENT`;
- `TEXT_ALIGNMENT_INCONSISTENCY`;
- `HIGH_CNN_TAMPER_PROBABILITY`;
- `MULTIPLE_MEDIUM_IMAGE_SIGNALS`;
- `IMAGE_QUALITY_INSUFFICIENT`.

For each rule:

- code;
- description;
- feature dependencies;
- condition;
- severity;
- score contribution;
- user-safe reason;
- staff detail;
- enabled state.

The normalised rule component:

`p_rule = min(1, sum(triggered_contributions) / configured_rule_scale)`

or a documented equivalent. Store the exact version and triggered contributions.

## 20. Risk aggregation

### 20.1 Default preliminary formula

When all components are available:

`R = 100 × (0.40 × p_img + 0.40 × p_ml + 0.20 × p_rule)`

Initial class thresholds, until validation:

- `R < 35`: `GENUINE`;
- `35 ≤ R < 70`: `SUSPICIOUS`;
- `R ≥ 70`: `FRAUDULENT`.

These are configuration defaults, not validated conclusions. Validation may change weights/thresholds through a new rule-set version.

### 20.2 Partial-evidence policy

Do not blindly renormalise missing components in a way that overstates confidence.

Store:

- available components;
- missing components;
- raw weighted sum;
- coverage/confidence;
- final policy.

Suggested safe policy:

- missing a mandatory active model -> `PARTIAL`;
- calculate a provisional score from available evidence for staff;
- normal user receives conservative class/wording such as `SUSPICIOUS` or “Needs review” when high-confidence low-risk conclusion cannot be supported;
- verification remains separately displayed;
- top reason includes `ANALYSIS_COMPONENT_UNAVAILABLE`.

For categorical policy results, component completeness and risk conclusiveness
are separate axes. Missing optional/accepted models may retain execution status
`PARTIAL` and explicit limitations while decisive low/medium/high evidence stays
`CONCLUSIVE`. Reports, notifications and user interfaces must preserve that
hierarchy and must not describe a high-risk band as inconclusive.

The exact policy is versioned and tested.

### 20.3 Reason selection

Rank triggered evidence by:

- severity;
- contribution;
- confidence;
- user relevance;
- non-duplication.

Return 2–4 user reasons plus full staff evidence. Never generate a reason unsupported by stored evidence.

## 21. Model registry and artifacts

### Structured model

Prefer a safer serialisation format such as `skops.io` where supported. If joblib/pickle is used, load only artifacts produced by the project and verified by hash; never load an arbitrary user upload.

### TensorFlow model

Use `.keras` format with explicit preprocessing metadata.

### Registry readiness checks

- file exists in private storage;
- SHA-256 matches;
- framework version is compatible;
- input/preprocessing schema matches runtime;
- smoke inference passes;
- model card/metrics present;
- status is `READY`.

Activation is an audited admin action. A worker caches active artifacts but responds to activation changes safely.

## 22. Evaluation reports

### OCR report

- dataset description and split;
- number of receipts;
- required-field accuracy;
- per-field accuracy;
- provider/template breakdown;
- confidence calibration/review threshold;
- failure examples;
- synthetic/real scope.

### Structured model report

- class distribution;
- group split;
- confusion matrix;
- per-class precision/recall/F1;
- macro F1;
- balanced accuracy;
- calibration;
- threshold selection;
- limitations;
- exact artifact/hash/commit.

### CNN report

- source types;
- split/group policy;
- class distribution;
- confusion matrix;
- precision/recall/F1;
- PR/ROC information where meaningful;
- calibration/threshold;
- CPU inference latency;
- controlled/synthetic limitation.

### End-to-end report

- risk/verification combinations;
- partial/failure rate;
- false-positive/false-negative analysis;
- reason-code correctness;
- stage timings;
- user/investigator evaluation.

## 23. Required automated ML/data tests

- manifest schema validation;
- duplicate hash detection;
- empty group intersection across splits;
- augmentation train-only assertion;
- feature schema hash stability;
- fit/test leakage guard;
- deterministic seed/reproducibility smoke;
- model artifact hash check;
- preprocessing parity;
- probability bounds/sum;
- threshold boundaries;
- missing-feature behaviour;
- absent/corrupt model behaviour;
- golden inference fixtures;
- evaluation report generation.

## 24. Scientific and product limitations to state

- performance depends on the representativeness and legality of the dataset;
- controlled synthetic edits do not cover all real fraud techniques;
- screenshots naturally undergo compression and metadata loss;
- ELA/noise/layout checks are supporting evidence, not proof;
- OCR errors can propagate if the user does not correct them;
- a reference record is only as trustworthy/current as its source;
- absence of a reference record is not evidence of fraud;
- a model trained only on generic/demo receipts must not claim provider-wide production accuracy;
- human review and authorised provider confirmation remain necessary for consequential cases.

## 25. Analytical definition of done

- [ ] controlled data and manifests exist;
- [ ] split-leakage tests pass;
- [ ] OCR fields/confidence/corrections persist;
- [ ] deterministic image evidence persists;
- [ ] verification field comparisons persist;
- [ ] structured model pipeline is reproducible and registered;
- [ ] CNN pipeline is reproducible and registered or explicitly unavailable;
- [ ] risk score is reconstructable;
- [ ] reasons map to evidence;
- [ ] historical versions are immutable;
- [ ] actual metrics and limitations are documented;
- [ ] end-to-end golden fixtures pass.
