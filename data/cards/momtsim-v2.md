# Dataset Card — MoMTSim version 2

- Registry ID/version: `momtsim-v2` / `2`
- Source locator/citation key: `mendeley:10.17632/zhj366m53p.2`; published 29 October 2024 by Denish Azamuke
- Intended role: primary structured mobile-money simulation source after approval
- Acquisition status: `quarantined`; disabled and non-promotable
- Licence/permission: `verified` / `approved` for official Mendeley acquisition under CC BY 4.0; evidence `docs/evidence/PR13_MOMTSIM_SOURCE_RIGHTS_REVIEW.md`
- Redistribution: CC BY 4.0 permits sharing/adaptation with attribution and change indication, but repository policy prohibits raw Git/public serving
- Expected schema: `data/schemas/transaction.schema.json`
- Class distribution: validated as 4,225,958 rows and 2,233,118 fraud-positive rows; 193 observed distinct steps and 20 exact duplicate rows
- Appropriate use: academic comparison after version/licence/schema approval
- Prohibited use: silent v1/v2 substitution, production prevalence claims or public redistribution
- Limitations: simulation cannot establish real provider behaviour, calibration or Ghanaian fraud prevalence

The official version-2 registration CSV is 366,397,921 bytes with SHA-256 `99fd07c3a9d3c4bd6d3462240058ca19d0d9e9284683f78bf77542ff7fcc05e7`. Its retained smaller file is byte-identical to v1 and must not be merged as a second population. The strict validator quarantined v2 for 20 exact duplicate rows; no silent deduplication, splitting, training or promotion is allowed.
