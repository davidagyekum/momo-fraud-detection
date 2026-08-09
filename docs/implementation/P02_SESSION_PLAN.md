# P02 Session Plan — Relational Schema and Private Storage

- Base: `main` at `7a9efcc71780e1e0c9e72b5e0e2efd194771d0d1`
- Branch: `codex/p02-relational-schema-storage`
- Scope: P02-T001 through P02-T010 only

## Plan

1. Implement every table, foreign key, check, uniqueness rule and required index from `04_DATABASE_AND_STORAGE_SPEC.md` using UUIDs, UTC timestamps and migration-friendly string checks.
2. Add a deterministic Alembic revision with safe downgrade and verify clean, previous-revision and rollback/upgrade paths on PostgreSQL.
3. Add configured local-private and S3-compatible storage adapters with generated non-identifying keys, hashes, metadata, private reads and guarded deletion/retention hooks.
4. Add idempotent development seeds and reusable database factories for the later feature domains without implementing P03+ routes or business workflows.
5. Add schema/storage/migration tests, generate the implemented-schema ER reference, update traceability and run every P02 gate.

## Scope boundary

P02 establishes persistence and test data only. It does not implement authentication endpoints, uploads, OCR, verification, model training, case workflow, dashboards or user interfaces. Model registry rows remain inactive/unavailable and no model metric is claimed.
