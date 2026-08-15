# PR13 MoMTSim v1/v2 source-rights and schema review

- Review date: 2026-08-11
- Review scope: engineering acquisition gate for internal personal academic research; not legal advice
- Dataset IDs: `momtsim-v1`, `momtsim-v2`
- Acquisition executed: false
- Source bytes opened: false
- Training executed: false

## Authoritative identity

The canonical Mendeley Data record is [Synthetic Mobile Money Transaction
Dataset](https://data.mendeley.com/datasets/zhj366m53p/2), contributed by Denish
Azamuke of Makerere University. Its immutable DOI versions are:

- version 1: `10.17632/zhj366m53p.1`, published 7 October 2024;
- version 2: `10.17632/zhj366m53p.2`, published 29 October 2024.

Both official version pages declare CC BY 4.0. The version-2 page lists two
files: `MoMTSim_20240722202413_1000_dataset.csv` (displayed as 349 MB) and
`synthetic_mobile_money_transaction_dataset.csv` (displayed as 149 MB). The
official UI exposes `Download All`. No Kaggle repost, mirror or simulator output
generated with different parameters is an approved substitute.

## Licence and platform conditions

The [CC BY 4.0 deed](https://creativecommons.org/licenses/by/4.0/) permits copy,
redistribution and adaptation for any purpose when appropriate credit and the
licence link are supplied and changes are indicated. It prohibits additional
legal or technological restrictions and warns that other rights may still apply.

Mendeley Data states that open-access content is governed by its Creative
Commons terms. The repository will nevertheless retain raw bytes only in private
storage, preserve author/title/DOI/version attribution and prohibit raw Git or
public-static serving.

## Published schema and aggregates

The peer-reviewed open-access data article [A labeled synthetic mobile money
transaction dataset](https://pmc.ncbi.nlm.nih.gov/articles/PMC12036017/)
publishes the same ten raw fields for both versions:

`step`, `transactionType`, `amount`, `initiator`, `oldBalInitiator`,
`newBalInitiator`, `recipient`, `oldBalRecipient`, `newBalRecipient`, `isFraud`.

It reports:

| Version | Rows | Fraud-positive rows | Simulation `nbSteps` parameter |
|---|---:|---:|---:|
| v1 | 1,720,181 | 175,518 | 720 |
| v2 | 4,225,958 | 2,233,118 | 720 |

`nbSteps` is a simulator parameter, not yet treated as an observed unique-step
count. The validator must measure the actual distinct values from each exact
file before an `expected_step_count` is frozen.

## Decision and remaining gate

Permission is approved and the licence is verified only for the official
Mendeley DOI versions and the recorded academic purpose. Both registry entries
remain disabled and `not_acquired`. Before bytes may be registered, the official
download must establish for each version:

1. exact file-to-version mapping rather than inference from displayed size;
2. exact byte size and SHA-256;
3. exact header and encoding;
4. measured rows, positives, distinct steps, duplicates, nulls and invalids;
5. private storage location and attribution record.

This review does not authorise mirrors, version substitution, raw publication,
merged-population claims, Ghana/provider prevalence claims, splits or training.
