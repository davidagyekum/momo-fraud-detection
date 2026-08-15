# Data Publication Checklist

- [ ] Every included record is synthetic or has explicit `release_approved` scope; internal-only records are absent.
- [ ] Authoritative licence/redistribution terms and citation are recorded for every external source.
- [ ] Direct identifiers, OCR text, filenames, metadata and small slices have been reviewed for re-identification risk.
- [ ] Participant withdrawal ledger and permission expiry checks pass against the release manifest.
- [ ] Brands/templates are reviewed and no provider endorsement/verification claim is implied.
- [ ] Dataset/model cards state distributions, missing groups, synthetic/private scope and prohibited claims.
- [ ] Source groups remain isolated and released split/manifests have stable hashes.
- [ ] Secret, PII-filename, large-file and schema validators pass.
- [ ] Public figures/samples are fictitious or specifically release-approved.
- [ ] Data steward, project owner and required institutional/supervisor reviewer have approved the exact release.

Keep the completed approval record outside Git; publish only a safe release decision/reference.
