# PR13 PaySim step-count reconciliation

- Review date: 2026-08-11
- Dataset ID: `paysim`
- Approved source SHA-256: `f7eef9ffad5cfa64a034143a5c9b30491d189420b273d5ad5723ca40b596613d`
- Archive size: `186385561` bytes
- Training executed: false
- Locked-test access: false
- Promotion executed: false

## First registration outcome

The owner-operated Colab registration read the approved private Drive archive and
produced a fail-closed `quarantined` manifest with only
`expected_step_count_mismatch`. Its safe validation summary measured:

| Check | Observed |
|---|---:|
| Rows | 6,362,620 |
| Fraud-positive rows | 8,213 |
| Unique steps | 743 |
| Exact duplicate rows | 0 |
| Null cells | 0 |
| Invalid labels | 0 |
| Invalid amounts | 0 |

The manifest also reproduced the approved archive hash, byte size, one-file
inventory and inventory SHA-256
`ec13068c4e7d7a8c97184e1e4c4e2c95d459c1b2053c37f67d75239ddfc87c32`.
It committed no source bytes and remained non-promotable.

## Independent aggregate-only recheck

A separate local read of the same hash-verified ZIP counted 6,362,620 rows,
8,213 fraud-positive rows and 743 unique integer step values. The minimum was 1,
the maximum was 743 and no integer in that inclusive range was missing. No raw
row, account identifier, amount or transaction detail was printed, copied into
the repository or retained as evidence.

## Decision

The blueprint's approximate 744-step expectation was an off-by-one metadata
assumption, while the authoritative byte-level evidence is the contiguous set
`1..743`. The source archive is unchanged. The validation specification now
expects 743 unique steps and retains all other exact checks. A new pinned Colab
run must still succeed before PaySim may be called registered; the first
quarantine result is preserved as audit evidence and is not overwritten in this
repository.
