# P02 Backup, Retention and Consistency Runbook

P02 provides technical hooks; the institution/project owner must supply approved retention periods. No legal period is invented here.

## PostgreSQL backup and restore rehearsal

1. Run `pg_dump --format=custom --file=momo_fdvs.dump momo_fdvs` using a protected operator environment.
2. Encrypt and store the dump outside Git and outside public web roots.
3. Restore only into an isolated non-production database with `pg_restore --clean --if-exists`.
4. Run `flask db current`, schema integrity tests and controlled row-count/hash checks.
5. Record date, operator, source revision, destination, checksum and result in the release evidence.

## Private storage

- Local development storage lives under the configured ignored `.local/private-storage` root.
- S3-compatible storage uses a private bucket, server-side encryption and generated non-identifying keys.
- Enable provider versioning/lifecycle only after approved retention values are supplied.
- Deletion requires an explicit `DeletionDecision`; database audit/evidence rows are never deleted by the object adapter.

## Consistency and recovery

A later operational phase will schedule reconciliation of database keys against storage inventory. Until then, any failed multi-resource operation must retain or log its generated key for controlled orphan cleanup. Backup artifacts and restore credentials are restricted, encrypted and prohibited from Git.
