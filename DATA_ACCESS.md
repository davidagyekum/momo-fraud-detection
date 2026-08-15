# Data Access Policy

## Default state

No external or participant dataset is approved merely because it appears in `data/registry.yaml`. Every entry starts disabled and `not_acquired`. Acquisition requires a named reviewer to verify the authoritative licence/consent terms, citation, exact version, storage class and permitted purpose, then record an activation decision without placing credentials or completed consent records in Git.

## Classifications and locations

| Classification | Examples | Permitted location | Git |
|---|---|---|---|
| Public fictitious fixture | `data/fixtures` contract examples | Repository | Allowed after scanner/tests |
| Restricted external | STFD or source with unverified/restricted terms | Institution-approved private storage | Never |
| Private research | Ghana participant screenshots, transcripts, consent/withdrawal records | Access-controlled private bucket/Drive prefix | Never |
| Derived de-identified | Approved derivatives retaining research sensitivity | Separate restricted derivative prefix | Never unless explicitly release-approved and reviewed |
| Safe aggregate evidence | Counts/metrics that cannot identify a participant | Reviewed evidence folder | Allowed after publication checklist |

## Roles

- **Data steward:** verifies permission, approves access, maintains private consent/withdrawal linkage and initiates deletion/rebuild.
- **Researcher:** accesses only approved de-identified working data for the recorded purpose; cannot approve release.
- **Annotator:** receives least-privilege task subsets without consent records or unrelated fields.
- **Model operator:** runs approved manifests/splits; cannot browse raw participant data unless separately authorised.
- **Reviewer/auditor:** reads safe manifests, decisions and aggregate evidence; raw access requires separate approval.
- **Public user:** receives only release-approved artifacts and documentation.

Access grants must have owner, purpose, dataset/version, role, start, review/expiry and revocation status. Shared credentials and public links are prohibited.

## Activation checklist

1. Verify source identity/version and authoritative terms; unresolved status is a stop condition.
2. Record owner, purpose, permitted/prohibited uses, redistribution, retention/review and incident contact.
3. Register archive bytes, size and SHA-256 in private metadata; never overwrite a version with different bytes.
4. Validate schema and quarantine mismatches.
5. For participant data, record internal/release consent scope and pseudonymous withdrawal key before collection.

Logical PR13 adds a no-network registration boundary. Acquisition requests and source bytes stay in ignored/restricted storage. The repository may retain only content-addressed manifests and aggregate safe profiles after validation; these artifacts never change an entry's permission state automatically. A quarantined result preserves the source in place and requires human resolution rather than deletion or silent substitution.
6. Assign source groups before preprocessing, edits or splits.
7. Run governance, secret/PII/large-file and manifest checks.
8. Obtain owner/data-steward approval before enabling the registry entry.

## Withdrawal and incident handling

On withdrawal, disable affected participant records, delete raw/derived objects within the approved process, rebuild manifests/splits, invalidate dependent runs/artifacts and record completion privately. On suspected exposure, stop access and processing, preserve non-sensitive audit evidence, notify the data steward/project owner, assess affected objects and follow the approved institutional process. This repository does not invent legal deadlines or replace institutional advice.

## Publication

Internal consent is not public-release consent. No screenshot, transcript, filename, consent form, participant key or brand-sensitive derivative is public unless its record says `release_approved` and the publication checklist is signed off outside Git. Aggregate claims must state synthetic/private scope and cannot imply provider verification or Ghana-wide prevalence.
