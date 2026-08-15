# PR17 Parser-Ceiling Mismatch Attribution Design

**Date:** 2026-08-15  
**Status:** Pending written-spec review  
**Phase:** PR17 Stage 2, validation-only diagnostic

## Goal

Extend the validation parser-ceiling diagnostic so aggregate evidence can distinguish candidate-discovery failures from parser-selection failures without changing parser outputs. The result must remain safe to run against private validation transcripts: it may persist only allowlisted aggregate counts, never transcripts, field values, candidate values, record identifiers, or per-record outcomes.

The diagnostic will answer three bounded questions:

1. For amount, did the parser discover the truth among its active candidates, and how many distinct valid candidates did it have to resolve?
2. For recipient, using the exact name-or-wallet comparison subfield selected by the established truth contract, was the truth absent, present but not selected, or contained by the selected value?
3. For reference, was the truth absent, present but not selected, or contained by the selected value?

This is measurement work only. It does not tune parsing, run OCR engines, train models, access the locked test partition, or claim an accuracy improvement.

## Constraints and non-goals

- Preserve every public `ParserResult` and `ParsedField` value, warning, confidence, semantic reason, and inconclusive decision for the same input.
- Preserve all parser-ceiling v3 fields and their semantics, including flat warning compatibility and warning attribution by selected observed field.
- Operate only on the development bundle's validation partition and its verified transcripts.
- Keep `RUN_BENCHMARK = False`; the owner-operated notebook path remains cells 1-4 and does not invoke Tesseract or any other OCR engine.
- Do not use secondary recipient truth to override the selected primary comparison subfield.
- Defer timestamp mismatch attribution because only one validation record currently has timestamp truth. The existing timestamp exact/outcome counts remain in the report.
- Do not persist arbitrary category keys supplied at runtime. Report keys are fixed allowlists defined in code.
- Do not add parser candidates, relax normalization, or change matching semantics in this stage.

## Architecture

### Report evolution

`run_ocr_parser_ceiling_diagnostic` will emit `ghana-ocr-parser-ceiling-report-v4`. Version 4 is an additive evolution of version 3: all current v3 aggregates remain, and three new aggregate sections are added:

- `amount_candidate_source_counts`
- `amount_candidate_count_buckets`
- `mismatch_attribution_counts`

`mismatch_attribution_counts` contains allowlisted maps for `amount`, `recipient`, and `reference`. Each map is mutually exclusive and exhaustive over that field's truth-scored denominator. Existing `field_exact`, `field_outcome_counts`, warning counts, recipient truth-subtype counts, privacy flags, and self-hash remain unchanged in meaning.

### Shared amount-candidate snapshot

The current `parse_amount` candidate discovery will be extracted into a private immutable snapshot helper. The snapshot contains only in-memory parser evidence:

- whether the active source was `labelled`, `currency_fallback`, or `none`;
- the active raw candidates used by the parser;
- valid normalized candidates; and
- the distinct valid normalized candidate set.

`parse_amount` will consume that snapshot to reproduce its current behavior exactly. The diagnostic will call the same helper and immediately reduce its contents to counters. No candidate strings or normalized values enter the report.

The active source follows current behavior precisely: if any transaction-labelled matches exist, only those matches form the active candidate pool; otherwise all currency-token matches form the fallback pool. `none` means the active pool has no matches. The helper is private because candidate evidence is not a parser API contract.

### Containment normalization

Containment checks are in-memory diagnostic predicates, not new parser normalization rules.

- Recipient-name checks use the established recipient text normalization: Unicode NFKC, whitespace collapse, surrounding punctuation removal, and uppercase comparison.
- Recipient-wallet checks extract phone-shaped transcript candidates, apply the established phone normalization to each candidate, and use only the selected `recipient_wallet` comparison.
- Reference checks use uppercase text with internal whitespace removed, matching the established reference normalization.

The full transcript is normalized transiently for containment checks and discarded. The report records only which allowlisted category counter was incremented.

## Aggregate definitions

### Amount candidate source

For every truth-scored amount record, exactly one source counter increments:

- `labelled`: one or more transaction-labelled raw candidates formed the active pool;
- `currency_fallback`: no labelled candidate existed and one or more currency-token candidates formed the active pool;
- `none`: neither source produced a raw candidate.

The three counters must sum to the amount truth-scored denominator.

### Amount candidate-count bucket

For every truth-scored amount record, the number of **distinct valid normalized candidates in the active parser pool** increments exactly one bucket:

- `0`
- `1`
- `2`
- `3_plus`

Counting distinct valid values aligns the diagnostic with the parser's ambiguity decision and avoids inflating the bucket when the same amount is repeated. The four counters must sum to the amount truth-scored denominator.

### Amount mismatch attribution

For every truth-scored amount record, apply this ordered classification:

1. `exact_selected`: the selected amount comparison is exact.
2. `no_valid_candidate`: the active parser pool has no valid normalized amount.
3. `truth_in_candidate_set_not_selected`: the normalized truth is in the distinct valid candidate set but was not selected exactly. This includes unresolved ambiguity.
4. `truth_absent_candidate_set`: at least one valid candidate exists, but the normalized truth is absent.

These categories are mutually exclusive and must sum to the amount truth-scored denominator.

### Recipient and reference mismatch attribution

For each truth-scored recipient or reference record, use the already-selected `FieldComparison.observed_field`. Recipient therefore compares name truth only to `recipient` and wallet truth only to `recipient_wallet`; it never searches the other subfield for a better result. An unexpected observed field fails closed.

Apply this ordered classification:

1. `exact_selected`: the selected comparison is exact.
2. `truth_present_parser_unavailable`: the selected parser field is unavailable, but normalized truth is present in the normalized transcript.
3. `truth_absent_parser_unavailable`: the selected parser field is unavailable and normalized truth is absent from the normalized transcript.
4. `selected_contains_truth`: the available selected value strictly contains normalized truth.
5. `truth_contains_selected`: normalized truth strictly contains the available selected value.
6. `truth_present_not_selected`: normalized truth is present in the normalized transcript, but none of the prior selected-value relationships applies.
7. `truth_absent_transcript`: normalized truth is absent from the normalized transcript.

"Strictly contains" excludes equality, which is handled by `exact_selected`. The ordered rules make overlaps deterministic. Each field's seven counters must sum to its own truth-scored denominator.

An inconsistent parser state such as `available=False` with a normalized value already fails closed in `compare_parser_result`; this diagnostic will not reinterpret it. Likewise, `wrong_observed_subfield` is an invariant violation rather than a report category.

## Validation and privacy controls

Before writing a report, the implementation must validate:

- every new map has exactly its fixed allowlisted keys;
- every count is a non-negative integer and not a boolean;
- source, bucket, and amount-attribution totals equal the amount scored denominator;
- recipient and reference attribution totals equal their respective scored denominators;
- existing outcome totals and recipient subtype totals still hold;
- `raw_text_persisted`, `field_values_persisted`, `record_identifiers_persisted`, `locked_test_accessed`, and `training_executed` are all `false`;
- the canonical report self-hash is computed after all fields are present.

Errors fail closed with `OCRBenchmarkError`, and no partial report is written. No logs or exception messages may interpolate private values, transcripts, candidate strings, truth paths, or record identifiers.

## Notebook and evidence flow

The owner-operated Colab notebook remains aggregate-only:

1. install the repository package from an immutable implementation commit;
2. mount the owner's private development bundle;
3. validate the bundle without exposing rows;
4. run the parser-ceiling diagnostic and print the v4 aggregate JSON.

The notebook keeps `RUN_BENCHMARK = False`, so cells beyond the parser-ceiling path cannot execute accidentally. After the code commit, the notebook is pinned to that immutable SHA. Only owner-returned aggregate v4 output may be recorded in repository evidence; no private bundle artifact is copied into Git.

## Test strategy

Implementation follows test-driven development.

### Parser parity tests

- Lock current `parse_amount` outputs across labelled, fallback, absent, repeated, invalid, single, and ambiguous candidate cases before extracting the helper.
- Verify parity for raw value, normalized value, confidence, availability, and warnings.
- Include Unicode normalization and punctuation/spacing variants that exercise existing behavior without expanding it.

### Synthetic attribution tests

- Cover each amount source, each count bucket, and every amount attribution category.
- Cover all seven recipient-name categories and all seven reference categories.
- Cover wallet-primary recipient truth to prove the classifier uses `recipient_wallet` and its phone normalization.
- Prove secondary recipient truth does not affect attribution.
- Prove category priority for containment overlaps.

### Contract and privacy tests

- Assert every new total equals its scored denominator, including sparse-truth records.
- Assert exact allowlisted keys and reject malformed or unexpected categories.
- Assert the report contains no transcript fragments, truth values, record IDs, source paths, per-record arrays, or candidate values.
- Assert all privacy/training/locked-test flags remain false and the canonical self-hash verifies.
- Assert v3-compatible aggregates retain their established values for a fixed synthetic bundle.
- Assert invalid parser fields and invalid observed recipient subfields fail closed before a report is written.

### Notebook policy tests

- Assert the notebook pins the immutable implementation commit.
- Assert the parser-ceiling path remains in cells 1-4.
- Assert `RUN_BENCHMARK = False` and no training, locked-test, or OCR-engine path is activated.

## Documentation and delivery

After implementation and verification:

- update `IMPLEMENTATION_STATUS.md`, `requirements_traceability.csv`, and `CHANGELOG.md` with measured local gates only;
- update the PR17 evidence artifact only after the owner supplies the aggregate v4 result;
- add a session handoff using `templates/SESSION_HANDOFF.md`;
- record exact base/head SHAs and test commands;
- commit coherently and push `codex/p17-ocr-benchmark` without force-pushing.

Stage 2 is not complete merely because local synthetic tests pass. Repository evidence remains explicitly pending until the owner-operated private validation run returns a valid, self-hash-verifiable v4 aggregate report.
