# PR13 PaySim source-rights review

- Review date: 2026-08-11
- Review scope: engineering acquisition gate for this personal, internal, non-commercial academic project; not legal advice
- Dataset ID: `paysim`
- Acquisition executed: false
- Source bytes opened: false
- Training executed: false

## Authoritative identity

The reviewed canonical listing is [Synthetic Financial Datasets For Fraud Detection](https://www.kaggle.com/datasets/ealaxi/paysim1), published under the Kaggle profile of PaySim author Edgar Lopez-Rojas. The page identifies:

- Kaggle dataset Version 2;
- one file, `PS_20174392719_1491204439457_log.csv`;
- displayed size 493.53 MB;
- a 744-step simulation;
- citation to E. A. Lopez-Rojas, A. Elmir and S. Axelsson, “PaySim: A financial mobile money simulator for fraud detection,” 28th EMSS, 2016;
- CC BY-SA 4.0 as the dataset licence.

No mirror, repost or similarly named Kaggle dataset is an approved substitute.

## Licence and platform conditions

The [CC BY-SA 4.0 deed](https://creativecommons.org/licenses/by-sa/4.0/) permits sharing and adaptation, including commercial purposes, provided appropriate credit and a licence link are supplied, changes are indicated and distributed adaptations use the same or a compatible licence. It prohibits additional legal/technological restrictions and notes that other rights may still apply.

The [Kaggle Terms of Use](https://www.kaggle.com/terms) reviewed in Chrome showed the active version effective 2025-06-22. They restrict service use to internal, personal, non-commercial use; prohibit crawling/scraping; require compliance with content restrictions; and state that public dataset submissions are accessible to users through the service functionality. The dataset page exposes an official Download action but requires account sign-in.

## Decision and controls

`permission_status` is approved and `licence_status` is verified only for an official signed-in Kaggle Version 2 download for this internal personal non-commercial academic project. Acquisition must:

1. use the project owner's own Kaggle account and the official dataset Download functionality;
2. preserve the dataset title, author/citation, canonical URL and CC BY-SA 4.0 attribution;
3. store raw bytes in approved private storage outside Git;
4. record exact downloaded byte size and SHA-256 before registration;
5. reject a mirror, renamed substitute or non-Version-2 source;
6. avoid scraping, crawling, public raw-data publication and provider/Ghana prevalence claims.

This review makes PaySim eligible for local registration; it does not mark it acquired, registered, validated, enabled or promotable for training.
