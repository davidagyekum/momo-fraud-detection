# MoMo-FDVS PR17 OCR Parser Mismatch — External Technical Review Request

## Purpose of this document

This is a self-contained, privacy-safe request for technical help with the Ghana mobile-money OCR/parser component of MoMo-FDVS. It is intended to be given to a web-enabled GPT or another reviewer who does not have repository or private-dataset access.

Please review the evidence and recommend the next diagnostic and parser architecture. Do not infer private message content, request raw screenshots/transcripts, or claim that a proposed parser change will improve accuracy without a validation result.

## Executive summary

The OCR engine comparison now runs correctly, but none of the OCR/parser configurations passes the release gates. A second diagnostic removed OCR recognition from the equation by running the same parser directly against 33 human-verified validation transcripts. That parser-ceiling result was also poor.

The latest aggregate taxonomy shows that, for the fields with useful support, most failures are **mismatches** rather than merely missing/unavailable values:

| Field | Scored | Exact | Mismatch | Unavailable | Exact rate | Mismatch rate | Unavailable rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| Amount | 32 | 6 | 23 | 3 | 18.750% | 71.875% | 9.375% |
| Recipient | 32 | 1 | 23 | 8 | 3.125% | 71.875% | 25.000% |
| Reference | 20 | 1 | 13 | 6 | 5.000% | 65.000% | 30.000% |
| Timestamp | 1 | 0 | 0 | 1 | 0.000% | 0.000% | 100.000% |

This is not enough evidence to safely widen regular expressions. A mismatch can mean that the correct value was present but the parser selected the wrong candidate, the parser over-captured or truncated a value, normalization changed it incorrectly, or the truth/transcript representation is inconsistent. We need an aggregate-only mismatch-attribution diagnostic before changing parser behavior.

There is also a possible measurement-contract defect: recipient scoring may use either a recipient name or a wallet number depending on which truth field exists, but the v2 outcome classifier checks only the named-recipient parser field when deciding whether a failed recipient score is `unavailable`. This must be reviewed before treating all recipient counts as definitive.

## Repository and execution identity

- Repository: `davidagyekum/momo-fraud-detection`
- Work branch: `codex/p17-ocr-benchmark`
- Evidence closure commit: `9395a89b1b19c11f1323693d94c4bd4e9fa6d2b7`
- Parser implementation version: `ghana-momo-parser-v1`
- Field schema version: `ghana-momo-ocr-fields-v1`
- Parser-ceiling report schema: `ghana-ocr-parser-ceiling-report-v2`
- Latest parser-taxonomy report SHA-256: `68bfd786359cd93095d2aa22384a823523b3ddf73915a220caca17db16b278e3`
- Date of evidence: 2026-08-14

## Product context

MoMo-FDVS is a fraud detection and verification prototype for Ghanaian mobile-money evidence. It has separate components for:

1. extracting fields from receipt/message screenshots;
2. checking image-forensics evidence;
3. comparing extracted fields with stored/imported reference transactions;
4. structured fraud classification; and
5. human investigator review.

Fraud risk and transaction verification remain separate product outputs. The OCR parser is not itself the entire fraud detector. A failed or uncertain parse must produce an explicit inconclusive/partial state rather than a fake successful result.

## Fixed technical and governance constraints

- Python 3.12.
- OCR/image stack: Tesseract, OpenCV and Pillow; EasyOCR and PaddleOCR are benchmarked pretrained alternatives.
- Image model stack: TensorFlow/Keras.
- Structured-model stack: scikit-learn.
- The five controlled-real test records are locked and cannot be used for diagnosis, parser development, model selection or threshold tuning before the final evaluation phase.
- Only the 33 validation transcripts may be used for this diagnostic.
- Raw images, transcripts, names, phone numbers, references and field values are private and must remain outside Git.
- Public/repository diagnostic reports may contain only aggregate counts, bounded categorical identifiers, hashes and safe configuration metadata.
- No training is authorized or necessary for this parser diagnostic.
- No OCR engine rerun is necessary until the parser-side root cause is better understood.
- Source groups were split before preprocessing, augmentation or fitting. Group boundaries must remain independent.
- The parser must remain conservative: unknown or low-confidence evidence must not be silently converted to success.

## Data boundary

The private OCR development archive contains 58 records:

- 25 train records;
- 33 validation records;
- 0 locked-test records.

Five controlled-real records exist in the locked test but are physically excluded from the development archive. The current diagnostic reads only verified validation truth transcripts. It does not initialize an OCR engine, read the locked test, train a recognizer, or persist record-level outputs.

The validation dataset is small and not representative enough to support provider-wide or production claims. Timestamp truth is especially sparse: only one validation record has a scored timestamp. Therefore, timestamp behavior must be deferred rather than optimized from one example.

## OCR benchmark evidence

The repaired clean-validation benchmark evaluated 33 records with complete coverage for Tesseract, EasyOCR and PaddleOCR. PaddleOCR `original_rgb` ranked first under the frozen weighted selector, but all field gates failed and the selected bundle remained experimental/non-promotable.

| Engine | Version | Variant | CER | WER | Amount exact | Recipient exact | Reference exact | Timestamp exact | Required-field success |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| PaddleOCR | 3.7.0 | `original_rgb` | 0.284632 | 0.410592 | 0.15625 | 0.125 | 0.10 | 0.0 | 0.0 |
| EasyOCR | 1.7.2 | `original_rgb` | 0.348428 | 0.528409 | 0.15625 | 0.0625 | 0.15 | 0.0 | 0.0 |
| Tesseract | 5.5.3 | `original_rgb` | 0.542726 | 0.776510 | 0.0625 | 0.0 | 0.05 | 0.0 | 0.0 |

Configured release gates are:

- amount exact: 0.95;
- recipient exact: 0.90;
- reference exact: 0.90;
- timestamp exact: 0.90; and
- required-field parse success: 0.90.

These OCR results establish that recognizer loss exists, but they cannot identify how much failure comes from recognition versus parser/template coverage.

## Human-transcript parser ceiling

To isolate parser limitations, `ghana-momo-parser-v1` was run directly on the 33 human-verified validation transcripts. No OCR engine was used. The v1 ceiling report found:

| Field | Exact rate | Scored records |
|---|---:|---:|
| Amount | 0.1875 | 32 |
| Recipient | 0.03125 | 32 |
| Reference | 0.05 | 20 |
| Timestamp | 0.0 | 1 |

- Required-field success: `0.0` over one fully scored record.
- Parser inconclusive rate: `1.0` over all 33 records.

This proves that parser/template limitations remain even when OCR recognition error is removed. It does **not** prove the exact parser repair required.

## V2 failure taxonomy evidence

The v2 report classifies every truth-scored field into exactly one of:

- `exact`: normalized observed value equals normalized truth;
- `mismatch`: parser produced an available normalized value, but it differs from truth; or
- `unavailable`: truth exists, but the relevant parser output is missing/unavailable.

Measured results:

```json
{
  "field_outcome_counts": {
    "amount": {"exact": 6, "mismatch": 23, "unavailable": 3},
    "recipient": {"exact": 1, "mismatch": 23, "unavailable": 8},
    "reference": {"exact": 1, "mismatch": 13, "unavailable": 6},
    "timestamp": {"exact": 0, "mismatch": 0, "unavailable": 1}
  },
  "field_scored_record_count": {
    "amount": 32,
    "recipient": 32,
    "reference": 20,
    "timestamp": 1
  },
  "parser_inconclusive_rate": 1.0,
  "required_field_parse_success": 0.0,
  "required_field_scored_record_count": 1,
  "locked_test_accessed": false,
  "training_executed": false
}
```

The four outcome totals exactly equal their respective truth-scored denominators.

### Aggregate warning counts

```json
{
  "AMOUNT_AMBIGUOUS": 1,
  "AMOUNT_NOT_FOUND": 3,
  "RECIPIENT_NOT_FOUND": 9,
  "REFERENCE_NOT_FOUND": 19,
  "TIMESTAMP_NOT_FOUND": 33
}
```

Important denominator warning: these warning counts are accumulated across all 33 validation parses, whether or not a truth field exists for that record. They must not be compared directly with the truth-scored outcome denominators. For example, reference has 20 truth-scored records but `REFERENCE_NOT_FOUND` is counted across all 33 parses.

## Current parser behavior

### Amount

The parser recognizes Ghana cedi markers (`GHS`, `GHC`, `GH₵`, `₵`) followed by a numeric token. It first searches for values near transaction-related labels such as `amount`, `total`, `paid`, `payment`, `cash in`, `cash out`, `transferred`, `sent` and `received`. If labelled candidates exist, unlabelled candidates are ignored. Otherwise, all currency candidates are considered.

It normalizes spaces and commas, parses with `Decimal`, rejects negative/out-of-range values and more than two decimal places, and returns:

- unavailable when no valid candidate exists;
- unavailable/ambiguous when multiple distinct normalized values exist; or
- the first valid candidate when all valid candidates normalize to one distinct value.

Potential fault surfaces—not yet proven—include:

- broad proximity windows associating a label with a balance, fee or another amount;
- a `total` label meaning something different across message templates;
- labelled-candidate precedence hiding the correct unlabelled candidate;
- multiple textual mentions of one transaction value plus fee/balance values;
- truth normalization and parser normalization using different conventions.

### Reference

The parser searches for one alphanumeric token after anchors such as:

- `transaction id`;
- `transaction reference`;
- `transaction ref`;
- `reference`;
- `ref`;
- `receipt id`.

The token allows uppercase letters, digits, `.`, `_`, `/` and `-`, with a length from 5 to 50 characters. Spaces are removed and the result is uppercased. OCR ambiguity between `O`, `0`, `I` and `1` is preserved rather than silently corrected.

Potential fault surfaces—not yet proven—include:

- real template anchors not covered by the anchor list;
- a nearby unrelated identifier being selected;
- punctuation/whitespace layouts outside the current pattern;
- references containing characters or lengths outside the declared format;
- correct reference text being present elsewhere but not after a recognized anchor;
- truth and parser applying different normalization.

### Recipient name

The parser searches, in order, for:

1. labelled `recipient`, `receiver` or `beneficiary` names;
2. `payment made`, `sent`, `transferred` or `cash out` followed by `to`; or
3. `payment received`, `received` or `cash in` followed by `from`.

It captures up to the newline, then truncates at `on`, `at`, `ref`, `reference` or `transaction id`. It collapses whitespace, strips common punctuation and uppercases the result.

Potential fault surfaces—not yet proven—include:

- greedy capture including wallet numbers, provider text, balance text or status text;
- premature truncation when a legitimate name contains a stop word;
- templates using verbs/prepositions outside the current patterns;
- sender-versus-recipient semantics differing between cash-in and cash-out messages;
- a name and wallet both existing while the truth schema selects only one representation.

### Recipient wallet

Wallet parsing is separate from recipient-name parsing. It first searches for a labelled Ghana phone/wallet/account number and otherwise accepts exactly one Ghana-style phone-number candidate. Multiple numbers are treated as ambiguous. Numbers normalize to `+233…`.

### Timestamp

The parser supports several ISO-like and day-first formats anchored by `date/time`, `date`, `time`, `on` or `at`, then converts Africa/Accra local time to UTC. This field has only one truth-scored validation record, so no template repair should be selected from the current timestamp result.

### Inconclusive policy

A parse is inconclusive if any critical field—amount, reference, timestamp or recipient—is unavailable, has no normalized value, or has confidence below `0.65`. This strict policy is intentional. It is preferable to an invented success, but it also means sparse/unavailable timestamp evidence makes all 33 current validation parses inconclusive.

## Current scoring contract and suspected recipient defect

The scorer defines the expected recipient as:

```python
recipient_expected = expected.get("recipient_name") or expected.get("recipient_wallet")
recipient_observed = (
    observed["recipient"].normalized
    if expected.get("recipient_name")
    else observed["recipient_wallet"].normalized
)
```

This means the recipient score correctly chooses the name parser when name truth exists and the wallet parser otherwise.

However, after a recipient score is false, the v2 taxonomy currently decides `mismatch` versus `unavailable` using the field named by the aggregate key:

```python
elif not parser.fields[field].available or parser.fields[field].normalized is None:
    outcomes_by_field[field]["unavailable"] += 1
else:
    outcomes_by_field[field]["mismatch"] += 1
```

For aggregate field `recipient`, this always inspects `parser.fields["recipient"]`, even when `score_parser_result` compared truth against `parser.fields["recipient_wallet"]`.

Consequences that need review:

- a wallet-truth record can be scored against the wallet field but classified using name-field availability;
- some recipient `mismatch`/`unavailable` counts may be misclassified;
- recipient warning counts include only the name parser's warnings in this loop, not necessarily the wallet parser's warnings;
- the total failed recipient count remains real, but its failure subtype may not be reliable until the scorer exposes which observed field was used.

This is a measurement concern, not yet a parser repair.

## What is proven

1. The repaired OCR benchmark completed all 33 validation records for all three required engines.
2. No OCR engine/variant passes the declared release gates.
3. Parsing human transcripts directly remains far below the release gates, so OCR recognition is not the only bottleneck.
4. Amount, recipient and reference failures are mismatch-dominant under the current v2 taxonomy.
5. All 33 parser results are inconclusive under the current critical-field policy.
6. The diagnostic persisted no transcript, field value or record identifier.
7. No training or locked-test access occurred.

## What is not yet proven

1. Whether the correct amount is present among all currency candidates but loses because of candidate-selection rules.
2. Whether incorrect amount outputs represent balances, fees, totals or another semantic amount.
3. Whether the correct reference exists in the normalized transcript but is missed by anchoring/ranking.
4. Whether recipient mismatches are over-captures, truncations, direction errors, name/wallet representation differences, or truth inconsistencies.
5. Whether the v2 recipient mismatch/unavailable split is correct for wallet-truth records.
6. Whether provider-specific templates are required or a provider-agnostic candidate/ranking layer is sufficient.
7. Whether any parser change generalizes beyond these 33 validation records.
8. Timestamp performance, because its scored support is one.

## Proposed next diagnostic

The next run should remain validation-only and aggregate-only. It should not alter parser outputs. The goal is to attribute each mismatch to a bounded, mutually exclusive category.

### Recommended amount categories

For truth-scored amount records:

- `exact_selected`;
- `truth_in_candidate_set_not_selected`;
- `truth_absent_candidate_set`;
- `no_valid_candidate`;
- `multiple_distinct_candidates_including_truth`;
- `multiple_distinct_candidates_excluding_truth`; and
- `normalization_disagreement` only if it can be defined without persisting values.

Also publish bounded candidate-count buckets, for example `0`, `1`, `2`, and `3_plus`, aggregated across records.

The diagnostic should separately inspect:

- all valid currency candidates;
- transaction-labelled candidates; and
- the candidate ultimately selected by the existing parser.

It must not write the candidate values.

### Recommended reference categories

For truth-scored reference records:

- `exact_selected`;
- `truth_present_normalized_transcript_not_selected`;
- `selected_is_truth_prefix_or_suffix`;
- `truth_is_selected_prefix_or_suffix`;
- `truth_absent_normalized_transcript`;
- `anchor_absent`; and
- `candidate_unavailable`.

Any containment checks must be performed privately and emitted only as aggregate category counts.

### Recommended recipient categories

First expose a safe categorical truth subtype:

- `recipient_name_truth`; or
- `recipient_wallet_truth`.

Then classify using the actual parser field selected by the scorer:

- `exact_selected`;
- `truth_present_normalized_transcript_not_selected`;
- `selected_contains_truth` (likely over-capture);
- `truth_contains_selected` (likely truncation);
- `truth_absent_normalized_transcript`;
- `wrong_observed_subfield_used`; and
- `candidate_unavailable`.

Name and wallet results must not be combined until the same field is used consistently for scoring, outcome classification and warning attribution.

### Timestamp

Report only that the truth-scored support is one and defer repair. Do not create timestamp templates or tune formats from one validation record.

### Privacy and integrity requirements for the diagnostic

- No raw/full transcript in the report.
- No truth or observed field value in the report.
- No phone number, name, reference or amount in log messages.
- No record identifier, filename, source-group identifier or per-record category row.
- Only allowlisted category names and integer totals.
- Category totals must equal the relevant truth-scored denominator.
- Invalid/noncanonical category names must fail before report writing.
- Report must state `raw_text_persisted=false`, `field_values_persisted=false`, `record_identifiers_persisted=false`, `locked_test_accessed=false`, and `training_executed=false`.
- The report must be hash-addressed and tied to the exact code commit, parser version, field schema and split/manifest hash.

## Architectural options for review

Please compare these approaches rather than immediately recommending more regexes:

### Option A — Continue direct field regexes

Add more anchors and template variants directly to each field parser.

Advantages:

- minimal code change;
- deterministic and easy to explain; and
- no fitting/training.

Risks:

- likely overfitting to 33 validation transcripts;
- regex ordering becomes implicit ranking;
- difficult to reason about multiple amounts/identifiers; and
- provider/template exceptions may conflict.

### Option B — Candidate extraction followed by deterministic ranking

Separate each field into:

1. broad candidate discovery;
2. typed normalization;
3. contextual feature extraction;
4. deterministic scoring/ranking; and
5. ambiguity/rejection policy.

Possible safe features include label class, distance from label, same-line status, provider template family, neighbouring semantic tokens, candidate count and whether the candidate is inside a recognized transaction sentence.

Advantages:

- exposes why a candidate won;
- supports aggregate attribution;
- preserves deterministic behavior; and
- can reject close/ambiguous candidates.

Risks:

- more code and versioned contracts;
- hand-authored weights can still overfit; and
- careful privacy-safe logging is required.

### Option C — Provider/template-specific deterministic parsers

Detect provider and message-family first, then apply a versioned template parser per known family with a conservative generic fallback.

Advantages:

- message semantics may be clearer within a provider/template;
- easier to distinguish balance, fee, transaction amount and reference labels; and
- failures can be reported by safe template family.

Risks:

- genuine provider templates can change;
- current validation support per template may be sparse;
- unknown/fraudulent formats need a robust fallback; and
- template detection errors can cascade.

### Option D — Learned field extraction

Use NER, token classification, an LLM or another fitted model.

This is not the immediate preferred path because the private labelled dataset is small, no fitting is authorized for this diagnostic, reproducibility and privacy are strict, and the test set must remain sealed. If recommending this later, specify the minimum data/support, leakage controls, privacy threat model, offline deployment implications and a deterministic fallback.

## Questions for the external reviewer

Please answer these questions explicitly:

1. Is the suspected recipient measurement defect real? If so, what minimal contract change makes scoring, availability classification and warning attribution use the same selected subfield?
2. Is the proposed mismatch-attribution taxonomy mutually exclusive, exhaustive and privacy-safe? Identify any categories that are ambiguous or likely to leak private information.
3. For amount extraction, what is the smallest diagnostic that distinguishes candidate-discovery failure from candidate-selection failure without exposing amounts?
4. For recipient and reference extraction, are normalized transcript containment categories technically meaningful, or could they create misleading conclusions because of punctuation, Unicode or phone/reference normalization?
5. Should the parser move to candidate extraction plus deterministic ranking, provider/template parsers, or a hybrid? Explain the choice under small-data and privacy constraints.
6. How should recipient name and recipient wallet truth be represented and scored without conflating two different fields?
7. How can we improve the parser without repeatedly tuning to the same 33 validation records? Recommend a development protocol that preserves the sealed five-record test and source-group independence.
8. What synthetic or controlled tests can be added without claiming they represent real Ghanaian provider performance?
9. Should the strict all-critical-fields inconclusive policy be changed when timestamp truth/support is sparse, or should field extraction completeness and transaction-level usability remain separate metrics? Explain the product-safety trade-off.
10. What exact unit, property-based and metamorphic tests should precede any implementation change?
11. Which recommendations are supported by primary technical sources or established information-extraction practice? Please cite primary documentation or research where relevant.
12. Provide a staged plan that starts with measurement-contract repair, then aggregate attribution, then one minimal parser improvement, with a stop/go condition after each stage.

## Required response format

Please structure the response as:

1. **Diagnosis of the measurement contract**
2. **Assessment of the aggregate attribution design**
3. **Recommended parser architecture**
4. **Minimal next code change**
5. **Test-first verification plan**
6. **Privacy/leakage review**
7. **Validation and anti-overfitting plan**
8. **Risks and rejected alternatives**
9. **Primary sources**
10. **Concrete stop/go checklist**

Clearly distinguish:

- facts supported by the supplied evidence;
- inferences;
- hypotheses that require another diagnostic; and
- recommendations.

Do not claim that any recommendation improves accuracy until a new validation-only run demonstrates it. Do not recommend opening the locked test, inspecting private examples one by one, publishing raw transcripts, or training on validation records.

## Local repository files relevant to the project owner

These paths are included for the project owner/Codex continuation. The external reviewer does not need access to them:

- `ml/src/momo_fdvs_ml/ocr_parser.py`
- `ml/src/momo_fdvs_ml/ocr_benchmark.py`
- `ml/tests/test_ocr_parser.py`
- `ml/tests/test_ocr_benchmark.py`
- `ml/configs/ocr_benchmark_v2.json`
- `docs/evidence/PR17_OCR_BENCHMARK_PREPARATION.json`
- `docs/handoffs/2026-08-14-PR17-parser-failure-taxonomy.md`

## Current safe stop point

No parser behavior should change until:

1. the recipient measurement-contract issue is confirmed or ruled out;
2. the aggregate mismatch-attribution schema is reviewed;
3. privacy/leakage tests exist and fail for the missing behavior; and
4. the diagnostic can prove whether the truth was absent, present-but-not-selected, over-captured or truncated without persisting any value.

The selected OCR bundle remains `experimental` and non-promotable. Training and locked-test access remain false.
