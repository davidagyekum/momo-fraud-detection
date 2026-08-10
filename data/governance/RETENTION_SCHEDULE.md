# Retention and Review Schedule Template

This repository does not declare a universal legal retention period. Before collection, the data steward records institution/supervisor-approved values for:

| Data class | Review/retention decision required | End action |
|---|---|---|
| Contact and consent linkage | Minimum needed for consent/withdrawal accountability | Restricted deletion/archive per approved process |
| Raw identifiable screenshots | Shortest approved period needed for de-identification/quality control | Delete or irreversibly de-identify |
| Pseudonymised derivatives/transcripts | Approved research period and recurring review | Delete, renew approval or release only under separate scope |
| External restricted archives | Source licence/access term | Delete/return or renew access |
| Manifests/splits/runs | Reproducibility and withdrawal dependency period | Rebuild/invalidate when source permission changes |
| Checkpoints/models | Valid only while all source permissions and governance hashes remain active | Retire/delete after withdrawal or expiry |
| Safe aggregate evidence | Publication/research record policy | Retain only if non-identifying and approved |

Each registry activation must replace `pending` decisions with an owner, review date, authority and disposition. An expired review blocks new processing.
