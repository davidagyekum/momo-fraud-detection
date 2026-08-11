# PR13 PaySim acquisition identity

- Acquisition date: 2026-08-11
- Method: official signed-in Kaggle Dataset Version 2 ZIP download from `https://www.kaggle.com/datasets/ealaxi/paysim1`
- Network acquisition executed: true
- Raw records inspected: true, by the bounded registration validator and an
  independent aggregate-only local recheck
- Training executed: false
- Promotion executed: false

## Content-addressed identity

- Local filename at acquisition: `archive.zip` outside the repository
- Private Drive object: `MyDrive/momo-fraud/datasets/paysim-ealaxi-v2-f7eef9ffad5c.zip`
- Archive size: `186385561` bytes
- Archive SHA-256: `f7eef9ffad5cfa64a034143a5c9b30491d189420b273d5ad5723ca40b596613d`
- ZIP member count: `1`
- Member name: `PS_20174392719_1491204439457_log.csv`
- Member uncompressed size: `493534783` bytes
- Member compressed size: `186385351` bytes
- Member ZIP timestamp: `2019-09-20T12:26:28+01:00`

The archive was hashed as downloaded and its central directory was inspected
without extraction. The first owner-operated Colab registration attempt verified
the archive identity, schema, `6362620` rows, `8213` positives, zero exact
duplicates, zero null cells, zero invalid labels and zero invalid amounts. It
quarantined only because the predeclared metadata expected 744 unique steps while
the canonical archive contains the contiguous range `1..743` (743 unique values).
An independent aggregate-only local pass reproduced the same row, positive and
step counts. No raw value, identifier or transaction row entered Git. See
`docs/evidence/PR13_PAYSIM_STEP_COUNT_RECONCILIATION.md`.
