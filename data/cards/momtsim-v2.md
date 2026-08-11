# Dataset Card — MoMTSim version 2

- Registry ID/version: `momtsim-v2` / `2-derived-exact-dedup-v1`
- Source locator/citation key: `mendeley:10.17632/zhj366m53p.2`; published 29 October 2024 by Denish Azamuke
- Intended role: primary structured mobile-money simulation source after approval
- Acquisition status: derived candidate `registered`; disabled and non-promotable; immutable official v2 remains quarantined
- Licence/permission: `verified` / `approved` for official Mendeley acquisition under CC BY 4.0; evidence `docs/evidence/PR13_MOMTSIM_SOURCE_RIGHTS_REVIEW.md`
- Redistribution: CC BY 4.0 permits sharing/adaptation with attribution and change indication, but repository policy prohibits raw Git/public serving
- Expected schema: `data/schemas/transaction.schema.json`
- Class distribution: derived candidate validated as 4,225,938 rows and 2,233,118 fraud-positive rows; 193 observed distinct steps and zero exact duplicate rows
- Appropriate use: academic comparison after version/licence/schema approval
- Prohibited use: silent v1/v2 substitution, production prevalence claims or public redistribution
- Limitations: simulation cannot establish real provider behaviour, calibration or Ghanaian fraud prevalence

The official version-2 CSV remains immutable and quarantined at SHA-256 `99fd07c3a9d3c4bd6d3462240058ca19d0d9e9284683f78bf77542ff7fcc05e7`. ADR-028 authorises a separate first-occurrence derivative: 20 duplicate groups of size two produced 20 removed negative rows and no removed fraud-positive rows. The registered derived CSV has SHA-256 `642fcb2ba7c9cbfffb933729d118f426fefddcbaabbf002793807be169fe80cd`; registration still does not authorise splitting, training or promotion.
