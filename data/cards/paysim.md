# Dataset Card — PaySim

- Registry ID/version: `paysim` / `kaggle-version-2-pending-byte-verification` (immutable registration-time label; exact Version 2 byte identity is now verified)
- Source locator/citation key: `kaggle:ealaxi/paysim1`; canonical page https://www.kaggle.com/datasets/ealaxi/paysim1
- Intended role: internal personal non-commercial academic structured transaction-risk research
- Acquisition status: `registered`; disabled and non-promotable pending frozen PR14 splits. Exact official ZIP identity and safe aggregate validation evidence are recorded.
- Licence/permission: `verified` / `approved` for one official account-based Kaggle download under CC BY-SA 4.0; engineering review `docs/evidence/PR13_PAYSIM_SOURCE_RIGHTS_REVIEW.md`
- Redistribution: CC BY-SA 4.0 permits sharing/adaptation with attribution and ShareAlike, but repository policy prohibits committing or publicly serving the raw dataset
- Expected schema: `data/schemas/transaction.schema.json`
- Class distribution: owner-operated Colab measured 8,213 positive `isFraud` values in 6,362,620 rows, with 743 unique steps, zero exact duplicates, zero null cells and zero invalid labels/amounts
- Appropriate use: official Kaggle Version 2 download through the signed-in account UI, restricted private storage, required citation/attribution, change indication and ShareAlike for distributed adaptations
- Prohibited use: crawling/scraping, mirror substitution, use of another version, unattributed use, raw Git storage, Ghana prevalence claims or provider verification
- Limitations: simulated transactions may not represent Ghanaian providers, users, channels or current fraud behaviour

The canonical page identifies `PS_20174392719_1491204439457_log.csv`, Kaggle Version 2 and 493.53 MB, and cites E. A. Lopez-Rojas, A. Elmir and S. Axelsson, “PaySim: A financial mobile money simulator for fraud detection,” EMSS 2016. Kaggle Terms effective 2025-06-22 apply in addition to the dataset licence. Registration evidence is stored in `docs/evidence/PR13_PAYSIM_REGISTRATION.json`. Registration does not authorise training: the source remains disabled until split, leakage and promotion gates pass.
