# 04 — Database and Private Storage Specification

## 1. Database principles

- PostgreSQL is the source of truth for structured state, evidence metadata, versions, permissions and audit history.
- Private object storage is the source of truth for original receipt bytes, derived forensic images, generated reports and large model artifacts.
- The database stores object keys and hashes, never an assumption that a local public URL is permanent.
- UUIDs are used for externally visible primary keys.
- All timestamps are timezone-aware UTC.
- Money uses fixed precision (`NUMERIC`) and an explicit three-letter currency code.
- JSONB is used for versioned evidence whose shape evolves, but core searchable/filterable values remain typed columns.
- Completed evidence rows are append-only. Corrections, reanalysis and human decisions create new linked rows.
- Foreign keys, uniqueness, checks and state transitions are enforced in both application logic and database constraints where practical.
- Migrations are the only supported way to alter production schema.

## 2. Extensions and conventions

Recommended PostgreSQL extensions:

- `pgcrypto` for UUID generation if database-generated UUIDs are selected;
- `citext` for case-insensitive unique email;
- optionally `pg_trgm` for controlled fuzzy name comparison/search.

Conventions:

- table/column names: snake_case;
- primary key: `id UUID`;
- timestamps: `created_at`, `updated_at`, plus domain timestamps;
- enum-like values: PostgreSQL enum or `VARCHAR` plus CHECK; choose one consistent migration-friendly policy;
- JSONB default: `{}` or `[]` only where an empty object/list is meaningful;
- optimistic locking/version number on mutable configuration resources;
- no `ON DELETE CASCADE` from a user to immutable evidence unless the retention policy explicitly requires it.

## 3. Identity and access tables

### 3.1 `users`

| Column | Type | Constraints / purpose |
|---|---|---|
| `id` | UUID | PK |
| `email` | CITEXT | unique, not null |
| `password_hash` | VARCHAR(255) | not null |
| `full_name` | VARCHAR(150) | not null |
| `phone_e164` | VARCHAR(20) | nullable, masked in most views |
| `status` | VARCHAR(20) | `ACTIVE`, `DISABLED`, `PENDING`; indexed |
| `email_verified_at` | TIMESTAMPTZ | nullable |
| `last_login_at` | TIMESTAMPTZ | nullable |
| `password_changed_at` | TIMESTAMPTZ | not null |
| `token_version` | INTEGER | not null default 1 |
| `created_at` | TIMESTAMPTZ | not null |
| `updated_at` | TIMESTAMPTZ | not null |

Do not store a plaintext password, reset token or current access token.

### 3.2 `roles`

| Column | Type | Constraints |
|---|---|---|
| `code` | VARCHAR(30) | PK: `USER`, `ADMIN`, `INVESTIGATOR` |
| `description` | VARCHAR(255) | not null |

### 3.3 `user_roles`

| Column | Type | Constraints |
|---|---|---|
| `user_id` | UUID | FK users.id |
| `role_code` | VARCHAR(30) | FK roles.code |
| `granted_by` | UUID | FK users.id, nullable only for bootstrap |
| `granted_at` | TIMESTAMPTZ | not null |

Composite PK `(user_id, role_code)`. The service layer prevents removal of the last active administrator.

### 3.4 `admin_profiles`

Optional profile data for staff.

| Column | Type | Constraints |
|---|---|---|
| `user_id` | UUID | PK/FK users.id |
| `staff_reference` | VARCHAR(100) | nullable, unique when present |
| `department` | VARCHAR(100) | nullable |
| `notes` | TEXT | restricted, nullable |

### 3.5 `refresh_sessions`

| Column | Type | Constraints / purpose |
|---|---|---|
| `id` | UUID | PK |
| `user_id` | UUID | FK users.id, indexed |
| `family_id` | UUID | indexed, supports rotation/reuse detection |
| `token_hash` | CHAR(64) | unique, not null |
| `expires_at` | TIMESTAMPTZ | indexed |
| `revoked_at` | TIMESTAMPTZ | nullable |
| `revoke_reason` | VARCHAR(50) | nullable |
| `replaced_by_id` | UUID | self FK, nullable |
| `user_agent_hash` | CHAR(64) | nullable |
| `ip_hash` | CHAR(64) | nullable |
| `created_at` | TIMESTAMPTZ | not null |

Only the token hash/fingerprint is stored.

### 3.6 `password_reset_tokens`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `user_id` | UUID | FK users.id, indexed |
| `token_hash` | CHAR(64) | unique, not null |
| `expires_at` | TIMESTAMPTZ | not null |
| `used_at` | TIMESTAMPTZ | nullable |
| `requested_ip_hash` | CHAR(64) | nullable |
| `created_at` | TIMESTAMPTZ | not null |

## 4. Receipt submission and OCR tables

### 4.1 `transactions`

This represents a user-submitted transaction/receipt analysis subject, not an MNO reference record.

| Column | Type | Constraints / purpose |
|---|---|---|
| `id` | UUID | PK |
| `user_id` | UUID | FK users.id, indexed |
| `status` | VARCHAR(30) | validated processing state, indexed |
| `provider_code` | VARCHAR(50) | nullable, indexed |
| `display_reference_masked` | VARCHAR(100) | nullable |
| `latest_analysis_run_id` | UUID | nullable deferred FK analysis_runs.id |
| `created_at` | TIMESTAMPTZ | not null, indexed |
| `updated_at` | TIMESTAMPTZ | not null |

Index `(user_id, created_at DESC)` and filter-supporting indexes for status/provider.

### 4.2 `receipts`

| Column | Type | Constraints / purpose |
|---|---|---|
| `id` | UUID | PK |
| `transaction_id` | UUID | FK transactions.id, unique |
| `object_key` | VARCHAR(500) | unique, not null |
| `original_filename` | VARCHAR(255) | display only, sanitised |
| `media_type` | VARCHAR(50) | not null |
| `size_bytes` | BIGINT | positive check |
| `width_px` | INTEGER | positive check |
| `height_px` | INTEGER | positive check |
| `sha256` | CHAR(64) | indexed |
| `perceptual_hash` | VARCHAR(32) | indexed |
| `quality_score` | NUMERIC(5,4) | nullable |
| `quality_warnings` | JSONB | not null default `[]` |
| `storage_version` | VARCHAR(30) | not null |
| `created_at` | TIMESTAMPTZ | not null |

Do not make `sha256` globally unique: two users may submit the same receipt. Detection is an analysis concern.

### 4.3 `receipt_derivatives`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `receipt_id` | UUID | FK receipts.id, indexed |
| `kind` | VARCHAR(50) | `THUMBNAIL`, `OCR_VARIANT`, `ELA`, `NOISE_MAP`, `HEATMAP`, etc. |
| `version` | VARCHAR(50) | not null |
| `object_key` | VARCHAR(500) | unique, not null |
| `sha256` | CHAR(64) | not null |
| `metadata` | JSONB | settings/dimensions; not null default `{}` |
| `created_at` | TIMESTAMPTZ | not null |

Unique `(receipt_id, kind, version, sha256)` where practical.

### 4.4 `receipt_templates`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `provider_code` | VARCHAR(50) | indexed |
| `name` | VARCHAR(150) | not null |
| `version` | VARCHAR(50) | not null |
| `status` | VARCHAR(20) | `DRAFT`, `ACTIVE`, `RETIRED` |
| `config` | JSONB | expected anchors/regions/regex/config |
| `parser_version` | VARCHAR(100) | not null |
| `created_by` | UUID | FK users.id |
| `activated_by` | UUID | FK users.id, nullable |
| `activated_at` | TIMESTAMPTZ | nullable |
| `created_at` | TIMESTAMPTZ | not null |
| `updated_at` | TIMESTAMPTZ | not null |
| `row_version` | INTEGER | optimistic locking |

Unique `(provider_code, version)`. At most one active template per provider/parser policy, enforced by partial unique index or service transaction.

### 4.5 `ocr_results`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `receipt_id` | UUID | FK receipts.id, indexed |
| `template_id` | UUID | FK receipt_templates.id, nullable |
| `engine_name` | VARCHAR(50) | e.g. `tesseract` |
| `engine_version` | VARCHAR(100) | not null |
| `pipeline_version` | VARCHAR(100) | not null |
| `selected_variant` | VARCHAR(50) | not null |
| `raw_text` | TEXT | not null default empty |
| `token_data` | JSONB | text/bounds/confidence |
| `extracted_fields` | JSONB | original parser output |
| `field_confidences` | JSONB | per-field 0..1 |
| `warnings` | JSONB | not null default `[]` |
| `required_field_accuracy_hint` | NUMERIC(5,4) | nullable; not a final evaluation metric |
| `created_at` | TIMESTAMPTZ | not null |

Re-running OCR creates another row. Do not update the original result in place.

### 4.6 `ocr_confirmations`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `ocr_result_id` | UUID | FK ocr_results.id, indexed |
| `transaction_id` | UUID | FK transactions.id, indexed |
| `confirmed_fields` | JSONB | canonical field snapshot |
| `corrections` | JSONB | old/new/reason per field |
| `confirmed_by` | UUID | FK users.id |
| `confirmed_at` | TIMESTAMPTZ | not null |
| `schema_version` | VARCHAR(50) | not null |

One transaction may have multiple confirmations only when an explicit re-review creates a new version. The analysis run references exactly one confirmation.

## 5. Analysis configuration and execution tables

### 5.1 `model_versions`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `model_type` | VARCHAR(30) | `STRUCTURED`, `IMAGE` |
| `name` | VARCHAR(150) | not null |
| `version` | VARCHAR(100) | not null |
| `status` | VARCHAR(20) | `DRAFT`, `READY`, `ACTIVE`, `RETIRED`, `FAILED` |
| `artifact_uri` | VARCHAR(1000) | private location |
| `artifact_sha256` | CHAR(64) | not null |
| `input_schema_hash` | CHAR(64) | not null |
| `preprocessing_version` | VARCHAR(100) | not null |
| `framework_versions` | JSONB | Python/library versions |
| `metrics` | JSONB | measured metrics and evaluation scope |
| `dataset_manifest_hash` | CHAR(64) | nullable |
| `split_hash` | CHAR(64) | nullable |
| `training_commit_sha` | VARCHAR(40) | nullable |
| `model_card_key` | VARCHAR(500) | nullable |
| `created_by` | UUID | FK users.id, nullable for CLI import |
| `activated_by` | UUID | FK users.id, nullable |
| `activated_at` | TIMESTAMPTZ | nullable |
| `created_at` | TIMESTAMPTZ | not null |

Unique `(model_type, name, version)`. Partial unique index for one active version per model type/name.

### 5.2 `fraud_rule_sets`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `version` | VARCHAR(100) | unique |
| `status` | VARCHAR(20) | draft/active/retired |
| `risk_weights` | JSONB | includes image/ML/rule weights |
| `thresholds` | JSONB | class thresholds |
| `description` | TEXT | not null |
| `created_by` | UUID | FK users.id |
| `activated_by` | UUID | nullable FK |
| `activated_at` | TIMESTAMPTZ | nullable |
| `created_at` | TIMESTAMPTZ | not null |
| `row_version` | INTEGER | not null |

### 5.3 `fraud_rules`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `rule_set_id` | UUID | FK fraud_rule_sets.id, indexed |
| `code` | VARCHAR(100) | not null |
| `description` | TEXT | not null |
| `severity` | VARCHAR(20) | informational/low/medium/high/critical |
| `condition` | JSONB | versioned declarative rule definition |
| `score_contribution` | NUMERIC(6,4) | non-negative |
| `reason_template` | TEXT | not null |
| `enabled` | BOOLEAN | not null |
| `created_at` | TIMESTAMPTZ | not null |

Unique `(rule_set_id, code)`.

### 5.4 `analysis_runs`

| Column | Type | Constraints / purpose |
|---|---|---|
| `id` | UUID | PK |
| `transaction_id` | UUID | FK transactions.id, indexed |
| `ocr_confirmation_id` | UUID | FK ocr_confirmations.id |
| `status` | VARCHAR(20) | `QUEUED`, `PROCESSING`, `COMPLETED`, `PARTIAL`, `FAILED`, `CANCELLED`; indexed |
| `current_stage` | VARCHAR(50) | indexed |
| `template_id` | UUID | snapshot FK, nullable |
| `rule_set_id` | UUID | FK fraud_rule_sets.id |
| `structured_model_id` | UUID | FK model_versions.id, nullable |
| `image_model_id` | UUID | FK model_versions.id, nullable |
| `idempotency_key_hash` | CHAR(64) | indexed |
| `request_fingerprint` | CHAR(64) | not null |
| `attempt_count` | INTEGER | not null default 0 |
| `claimed_by` | VARCHAR(100) | nullable |
| `claimed_at` | TIMESTAMPTZ | nullable |
| `heartbeat_at` | TIMESTAMPTZ | nullable |
| `queued_at` | TIMESTAMPTZ | not null |
| `started_at` | TIMESTAMPTZ | nullable |
| `completed_at` | TIMESTAMPTZ | nullable |
| `risk_score` | NUMERIC(6,3) | check 0..100, nullable |
| `risk_class` | VARCHAR(20) | nullable, indexed |
| `component_scores` | JSONB | raw image/structured/rule values |
| `top_reasons` | JSONB | ordered reason codes/text |
| `configuration_snapshot` | JSONB | immutable settings not covered by FKs |
| `error_code` | VARCHAR(100) | nullable |
| `error_message_safe` | TEXT | nullable |
| `created_at` | TIMESTAMPTZ | not null |

Unique `(transaction_id, idempotency_key_hash)` when the key is present. Index for queue claim `(status, queued_at)`.

### 5.5 `analysis_stage_runs`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `analysis_run_id` | UUID | FK analysis_runs.id, indexed |
| `stage` | VARCHAR(50) | not null |
| `status` | VARCHAR(20) | queued/running/completed/skipped/failed |
| `attempt` | INTEGER | not null |
| `started_at` | TIMESTAMPTZ | nullable |
| `completed_at` | TIMESTAMPTZ | nullable |
| `duration_ms` | INTEGER | nullable |
| `error_code` | VARCHAR(100) | nullable |
| `details` | JSONB | safe stage metadata |
| `created_at` | TIMESTAMPTZ | not null |

Unique `(analysis_run_id, stage, attempt)`.

### 5.6 `image_analyses`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `analysis_run_id` | UUID | FK analysis_runs.id, unique |
| `algorithm_version` | VARCHAR(100) | not null |
| `metadata_evidence` | JSONB | not null |
| `duplicate_evidence` | JSONB | not null |
| `compression_evidence` | JSONB | not null |
| `noise_evidence` | JSONB | not null |
| `layout_evidence` | JSONB | not null |
| `quality_evidence` | JSONB | not null |
| `engineered_features` | JSONB | versioned structured values |
| `image_tamper_probability` | NUMERIC(7,6) | nullable, 0..1 |
| `warnings` | JSONB | not null default `[]` |
| `created_at` | TIMESTAMPTZ | not null |

### 5.7 `fraud_predictions`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `analysis_run_id` | UUID | FK analysis_runs.id, indexed |
| `model_version_id` | UUID | FK model_versions.id |
| `prediction_type` | VARCHAR(30) | `STRUCTURED`, `IMAGE` |
| `predicted_class` | VARCHAR(20) | nullable |
| `probabilities` | JSONB | class/probability map |
| `feature_schema_hash` | CHAR(64) | not null |
| `feature_snapshot` | JSONB | identifier-minimised |
| `inference_ms` | INTEGER | nullable |
| `status` | VARCHAR(20) | success/unavailable/error |
| `error_code` | VARCHAR(100) | nullable |
| `created_at` | TIMESTAMPTZ | not null |

Unique `(analysis_run_id, prediction_type)`.

### 5.8 `rule_evaluations`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `analysis_run_id` | UUID | FK analysis_runs.id, indexed |
| `rule_id` | UUID | FK fraud_rules.id |
| `triggered` | BOOLEAN | not null |
| `observed_value` | JSONB | safe feature/value |
| `score_contribution` | NUMERIC(6,4) | not null |
| `reason_code` | VARCHAR(100) | not null |
| `reason_text` | TEXT | not null |
| `created_at` | TIMESTAMPTZ | not null |

Unique `(analysis_run_id, rule_id)`.

## 6. Reference verification tables

### 6.1 `reference_import_batches`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `source_label` | VARCHAR(200) | not null |
| `original_filename` | VARCHAR(255) | not null |
| `file_sha256` | CHAR(64) | indexed |
| `object_key` | VARCHAR(500) | private original import, nullable by retention policy |
| `status` | VARCHAR(20) | uploaded/validated/committed/failed |
| `total_rows` | INTEGER | non-negative |
| `valid_rows` | INTEGER | non-negative |
| `invalid_rows` | INTEGER | non-negative |
| `invalid_report_key` | VARCHAR(500) | nullable |
| `uploaded_by` | UUID | FK users.id |
| `validated_at` | TIMESTAMPTZ | nullable |
| `committed_at` | TIMESTAMPTZ | nullable |
| `created_at` | TIMESTAMPTZ | not null |

Idempotency policy may make `(source_label, file_sha256)` unique.

### 6.2 `reference_transactions`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `import_batch_id` | UUID | FK reference_import_batches.id, indexed |
| `provider_code` | VARCHAR(50) | not null, indexed |
| `transaction_reference` | VARCHAR(150) | canonical, not null, indexed |
| `amount` | NUMERIC(18,2) | non-negative |
| `currency` | CHAR(3) | not null default `GHS` |
| `sender_name_normalised` | VARCHAR(200) | nullable |
| `sender_phone_e164` | VARCHAR(20) | nullable |
| `receiver_name_normalised` | VARCHAR(200) | nullable |
| `receiver_phone_e164` | VARCHAR(20) | nullable |
| `occurred_at` | TIMESTAMPTZ | nullable, indexed |
| `transaction_status` | VARCHAR(50) | nullable |
| `source_system_id` | VARCHAR(150) | nullable |
| `raw_row` | JSONB | restricted original row |
| `created_at` | TIMESTAMPTZ | not null |

Unique policy: `(provider_code, transaction_reference, source_system_id)` when source ID exists; otherwise `(provider_code, transaction_reference, import_batch_id)`.

### 6.3 `verification_results`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `analysis_run_id` | UUID | FK analysis_runs.id, unique |
| `reference_transaction_id` | UUID | FK reference_transactions.id, nullable |
| `status` | VARCHAR(20) | `VERIFIED`, `UNVERIFIED`, `MISMATCH`; indexed |
| `verifier_version` | VARCHAR(100) | not null |
| `candidate_method` | VARCHAR(100) | not null |
| `field_comparisons` | JSONB | match/mismatch/NA, tolerances and masked values |
| `matched_field_count` | INTEGER | non-negative |
| `mismatched_field_count` | INTEGER | non-negative |
| `warnings` | JSONB | not null default `[]` |
| `created_at` | TIMESTAMPTZ | not null |

## 7. Cases, reports, notifications and audit

### 7.1 `fraud_cases`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `transaction_id` | UUID | FK transactions.id, indexed |
| `source` | VARCHAR(30) | `USER_REPORT`, `AUTO_HIGH_RISK`, `ADMIN` |
| `reporter_id` | UUID | FK users.id, nullable |
| `category` | VARCHAR(100) | not null |
| `description` | TEXT | nullable |
| `status` | VARCHAR(20) | indexed |
| `assigned_to` | UUID | FK users.id, nullable, indexed |
| `opened_at` | TIMESTAMPTZ | not null |
| `closed_at` | TIMESTAMPTZ | nullable |
| `created_at` | TIMESTAMPTZ | not null |
| `updated_at` | TIMESTAMPTZ | not null |

Partial unique index prevents more than one open/in-review case for the same transaction and configured source policy.

### 7.2 `case_events`

Append-only timeline.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `case_id` | UUID | FK fraud_cases.id, indexed |
| `actor_id` | UUID | FK users.id |
| `event_type` | VARCHAR(50) | opened/assigned/note/status/decision/reopened |
| `from_status` | VARCHAR(20) | nullable |
| `to_status` | VARCHAR(20) | nullable |
| `reason` | TEXT | mandatory for decision |
| `metadata` | JSONB | safe |
| `created_at` | TIMESTAMPTZ | not null |

### 7.3 `case_decisions`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `case_id` | UUID | FK fraud_cases.id, indexed |
| `decided_by` | UUID | FK users.id |
| `outcome` | VARCHAR(20) | confirmed/dismissed/escalated |
| `reason` | TEXT | not null |
| `supersedes_id` | UUID | self FK, nullable |
| `created_at` | TIMESTAMPTZ | not null |

The original automated analysis is not updated.

### 7.4 `report_artifacts`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `report_type` | VARCHAR(30) | analysis/case/operations |
| `owner_user_id` | UUID | FK users.id, nullable |
| `transaction_id` | UUID | nullable FK |
| `case_id` | UUID | nullable FK |
| `object_key` | VARCHAR(500) | unique, private |
| `sha256` | CHAR(64) | not null |
| `status` | VARCHAR(20) | generating/ready/failed/expired |
| `generated_by` | UUID | FK users.id, nullable for system |
| `generated_at` | TIMESTAMPTZ | nullable |
| `expires_at` | TIMESTAMPTZ | nullable |
| `created_at` | TIMESTAMPTZ | not null |

Check that exactly the required target fields are present for each report type.

### 7.5 `notifications`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `user_id` | UUID | FK users.id, indexed |
| `type` | VARCHAR(50) | not null |
| `title` | VARCHAR(200) | not null |
| `message` | TEXT | not null |
| `target_type` | VARCHAR(50) | nullable |
| `target_id` | UUID | nullable |
| `read_at` | TIMESTAMPTZ | nullable |
| `delivery_status` | JSONB | per adapter; no secret payload |
| `created_at` | TIMESTAMPTZ | not null, indexed |

Index `(user_id, read_at, created_at DESC)`.

### 7.6 `audit_logs`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `actor_id` | UUID | nullable FK users.id for system/anonymous |
| `actor_role_snapshot` | JSONB | not null default `[]` |
| `action` | VARCHAR(100) | indexed |
| `target_type` | VARCHAR(50) | indexed |
| `target_id` | UUID | nullable, indexed |
| `outcome` | VARCHAR(20) | success/failure/denied |
| `request_id` | UUID | indexed |
| `ip_hash` | CHAR(64) | nullable |
| `user_agent_hash` | CHAR(64) | nullable |
| `metadata` | JSONB | safe, redacted |
| `created_at` | TIMESTAMPTZ | not null, indexed |

Application code never updates or deletes individual audit rows. Retention/archival is a separately authorised administrative procedure.

### 7.7 `idempotency_records`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `principal_id` | UUID | FK users.id |
| `scope` | VARCHAR(100) | route/action |
| `key_hash` | CHAR(64) | not null |
| `request_hash` | CHAR(64) | not null |
| `resource_type` | VARCHAR(50) | nullable |
| `resource_id` | UUID | nullable |
| `response_status` | INTEGER | nullable |
| `expires_at` | TIMESTAMPTZ | indexed |
| `created_at` | TIMESTAMPTZ | not null |

Unique `(principal_id, scope, key_hash)`. Reuse with a different request hash returns conflict.

## 8. Index plan

At minimum:

- users.email unique;
- transactions `(user_id, created_at DESC)`;
- transactions `(status, created_at)`;
- receipts.sha256 and perceptual_hash;
- ocr_results `(receipt_id, created_at DESC)`;
- analysis_runs `(status, queued_at)` for worker claim;
- analysis_runs `(transaction_id, created_at DESC)`;
- analysis_runs `(risk_class, completed_at)`;
- verification_results `(status, created_at)` through join/index;
- reference_transactions `(provider_code, transaction_reference)`;
- reference_transactions.occurred_at;
- fraud_cases `(status, assigned_to, opened_at)`;
- notifications `(user_id, read_at, created_at DESC)`;
- audit_logs `(created_at DESC)`, `(actor_id, created_at DESC)`, `(action, created_at DESC)`;
- model/rules/template partial unique active indexes.

Codex must use `EXPLAIN (ANALYZE, BUFFERS)` on critical dashboard/history/reference queries with representative data before final release.

## 9. Migration policy

Every schema change includes:

1. model change;
2. migration;
3. upgrade test from clean database;
4. upgrade test from previous revision;
5. downgrade where safe;
6. data backfill plan when required;
7. deployment note;
8. rollback limitations.

Destructive operations require a two-step release where possible:

- release A adds new field/table and dual-write/backfill;
- release B switches reads and later removes old data after verification.

Never auto-run migrations from every web worker. Run one explicit release/migration task.

## 10. Seed policy

Safe development seeds may create:

- one admin;
- one investigator;
- two users;
- generic templates;
- one active rule set;
- inactive/unavailable demo model records;
- fake reference records;
- fake receipt/analysis metadata only when fixture storage exists.

Credentials come from environment or are generated and printed once in local development. Production startup must not create known default credentials.

## 11. Private object-storage layout

Recommended key format:

```text
receipts/{user_uuid}/{transaction_uuid}/original/{receipt_uuid}.{ext}
receipts/{user_uuid}/{transaction_uuid}/derived/{kind}/{version}/{uuid}.{ext}
imports/reference/{batch_uuid}/original.csv
imports/reference/{batch_uuid}/invalid_rows.csv
reports/users/{user_uuid}/{report_uuid}.pdf
reports/cases/{case_uuid}/{report_uuid}.pdf
models/{model_type}/{name}/{version}/{sha256}/{artifact_name}
model-cards/{model_uuid}.md
```

Rules:

- object keys are generated server-side;
- no email, phone, name or transaction reference in a key;
- buckets/containers are private;
- server-side encryption is enabled when available;
- content type is recorded but never trusted as validation;
- access logs or API audit events cover sensitive retrieval;
- signed URLs expire quickly and are issued only after policy checks;
- local development storage lives outside the repository and web static root.

## 12. Retention and deletion

A configurable retention policy must define:

- account/profile retention;
- original receipt retention;
- derived forensic artifact retention;
- reference import retention;
- report expiration;
- model/dataset artifact retention;
- audit retention;
- backup retention.

User deletion does not silently destroy evidence needed for an open case or audit. Apply one of:

- legal/approved retention with access restriction;
- anonymisation/pseudonymisation;
- scheduled deletion after the retention basis ends.

Codex must not invent a legal retention period. It must implement configuration and document the owner's pending policy.

## 13. Backup and consistency

- Database: automated managed backup or documented `pg_dump` schedule.
- Object storage: versioning/lifecycle where available.
- Consistency report identifies database objects whose storage key is missing and private objects without a live database reference.
- Restoration rehearsal uses non-production data.
- Model artifact restore includes hash verification.
- Backup files are encrypted and excluded from Git.

## 14. Database acceptance checklist

- [ ] clean migration to head;
- [ ] previous-version migration to head;
- [ ] all foreign keys and check constraints tested;
- [ ] money precision tests;
- [ ] state transition tests;
- [ ] active-version uniqueness tests;
- [ ] cross-user ownership queries tested;
- [ ] critical indexes verified;
- [ ] worker claim concurrency tested;
- [ ] storage rollback/orphan reconciliation tested;
- [ ] audit append-only policy tested;
- [ ] backup/restore rehearsal recorded.
