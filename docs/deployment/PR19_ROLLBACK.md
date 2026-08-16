# PR19 Rollback Runbook

This runbook favours service rollback without destructive data changes.

1. Stop new acceptance traffic and record the running image identities and database revision.
2. Back up PostgreSQL and the private receipt volume using `docs/deployment/P02_BACKUP_AND_RETENTION.md`.
3. Repoint the Compose image tags to the previously accepted immutable image identities, then rebuild/restart only the application services.
4. Verify `/api/v1/health`, `/api/v1/ready`, login, owner history, case access, private report download, and audit visibility.
5. Keep the current database schema when the prior application is forward-compatible.

Alembic downgrade is exceptional. Perform it only after a verified backup, migration-specific impact review, and explicit owner approval. Never remove Compose volumes as a rollback technique. If application and schema compatibility cannot be proven, stop the release and preserve all evidence rather than guessing.

PR19 was accepted locally, so rollback evidence is also local. A hosted environment needs its own backup/restore rehearsal, immutable image registry, HTTPS termination, secret manager, and monitoring evidence before deployment can be claimed.

