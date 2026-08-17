# 05 — REST API Contract

## 1. Contract rules

- Base path: `/api/v1`
- Content type: JSON except multipart upload and binary report/image streams.
- Authentication: bearer access token for mobile/API calls; the admin portal uses the documented access/refresh-cookie pattern.
- Timestamps: ISO 8601 UTC.
- IDs: UUID strings.
- Money: string decimal plus currency, for example `"amount": "125.00", "currency": "GHS"`.
- Pagination: `page` starts at 1; `page_size` default 20, maximum 100.
- Sorting/filter values are allowlisted.
- Mutating endpoints that may be retried accept `Idempotency-Key`.
- Every response includes or returns `X-Request-ID`.
- The generated OpenAPI contract is authoritative. Examples below define intended behaviour, not an excuse to let code and documentation diverge.

## 2. Common envelopes

### Success

```json
{
  "data": {},
  "meta": {
    "request_id": "4e01ec26-3e79-4b88-bbbe-97f62ca24557"
  }
}
```

### Collection

```json
{
  "data": [],
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 42,
    "request_id": "..."
  }
}
```

### Error

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Review the highlighted fields.",
    "field_errors": {
      "email": ["Enter a valid email address."]
    },
    "request_id": "..."
  }
}
```

Internal stack traces, SQL, object keys, filesystem paths and model secrets must never appear in public errors.

## 3. System endpoints

### `GET /health`

**Auth:** none  
**Purpose:** liveness only.

```json
{
  "data": {
    "status": "ok",
    "service": "momo-fdvs-api"
  },
  "meta": {"request_id": "..."}
}
```

### `GET /ready`

**Auth:** none or deployment-protected according to environment  
**Purpose:** dependency/readiness matrix.

```json
{
  "data": {
    "ready": true,
    "components": {
      "database": {"status": "ready"},
      "storage": {"status": "ready"},
      "tesseract": {"status": "ready", "version": "masked-or-safe"},
      "structured_model": {"status": "ready", "version": "rf-1.0.0"},
      "image_model": {"status": "degraded", "reason": "not_activated"}
    },
    "analysis_available": true,
    "full_analysis_available": false
  },
  "meta": {"request_id": "..."}
}
```

Do not reveal credentials, paths or sensitive infrastructure details.

### `GET /version`

Returns application version, build commit and API contract version.

## 4. Authentication and profile

### `POST /auth/register`

**Auth:** none  
**Rate limit:** strict  
**Request:**

```json
{
  "full_name": "Demo User",
  "email": "demo@example.test",
  "password": "long-password"
}
```

**Response:** `201`; user projection and session tokens/cookie according to client.  
**Errors:** 400/422 validation, 409 duplicate when safe, 429.

### `POST /auth/login`

```json
{
  "email": "demo@example.test",
  "password": "long-password"
}
```

**Response:** `200`

```json
{
  "data": {
    "access_token": "mobile-or-memory-token",
    "expires_in": 900,
    "user": {
      "id": "uuid",
      "full_name": "Demo User",
      "email": "demo@example.test",
      "roles": ["USER"],
      "status": "ACTIVE"
    }
  },
  "meta": {"request_id": "..."}
}
```

For the web portal, refresh is set as a secure HTTP-only cookie and is not readable by JavaScript. A separate non-secret CSRF cookie is readable from portal routes and must be echoed in the `X-CSRF-Token` header for refresh and logout; the server cryptographically binds it to the refresh credential.

### `POST /auth/refresh`

Rotates refresh session. Detects reuse and revokes the token family.

### `POST /auth/logout`

Revokes the current refresh session/family as configured and clears the web cookie.

### `POST /auth/forgot-password`

```json
{"email": "demo@example.test"}
```

Always returns a generic accepted response.

### `POST /auth/reset-password`

```json
{
  "token": "single-use-reset-token",
  "new_password": "new-long-password"
}
```

### `GET /me`

Returns profile, roles, permissions and notification preferences.

### `PATCH /me`

Allowlisted fields only: name, phone, notification preferences. Role/status/password are not accepted here.

### `POST /me/change-password`

Requires current password and revokes other refresh sessions.

## 5. Transaction and receipt lifecycle

### `POST /transactions`

**Auth:** USER  
**Content type:** `multipart/form-data`  
**Headers:** `Idempotency-Key` required  
**Fields:**

- `receipt`: required image file;
- `source`: `CAMERA` or `GALLERY`;
- `client_captured_at`: optional ISO timestamp;
- `client_metadata`: optional safe device/app metadata, size-limited.

**Response:** `201`

```json
{
  "data": {
    "transaction": {
      "id": "uuid",
      "status": "UPLOADED",
      "created_at": "..."
    },
    "receipt": {
      "id": "uuid",
      "media_type": "image/jpeg",
      "size_bytes": 481223,
      "width_px": 1080,
      "height_px": 1920,
      "quality_warnings": [],
      "dimensions": {"width_px": 1080, "height_px": 1920},
      "quality": {"score": 0.94, "warnings": []},
      "duplicate_warning": {
        "exact_match_found": false,
        "near_match_found": false
      },
      "media": {
        "thumbnail_url": "/api/v1/transactions/uuid/receipt?variant=thumbnail",
        "original_url": "/api/v1/transactions/uuid/receipt?variant=original"
      }
    },
    "next_action": {
      "type": "RUN_OCR",
      "endpoint": "/api/v1/transactions/uuid/ocr"
    },
    "replayed": false
  },
  "meta": {"request_id": "..."}
}
```

The response never exposes the private object key or another user's duplicate details.
An identical retry with the same key returns the same resource with `200` and
`replayed: true`; reuse of the key for different content returns `409`. Image
quality warnings and duplicate warnings remain separate from fraud risk and
transaction verification.

**Errors:** 400 invalid image, 413 too large, 415 unsupported media, 409 idempotency conflict, 503 storage unavailable.

### `GET /transactions/{transaction_id}/receipt`

**Auth:** owner, authorised ADMIN/INVESTIGATOR  
Streams or redirects through a short-lived private URL after policy check. P06
supports `variant=thumbnail|original`; later staff-only forensic variants are
added by the image-forensics phase and remain permission checked. Streamed
responses use validated content types, generated filenames, `nosniff`, and
private no-store caching.

### `DELETE /transactions/{transaction_id}`

Optional pre-analysis user deletion/cancellation only. Completed evidence follows retention policy rather than unqualified hard deletion. Contract must make the allowed state explicit.

## 6. OCR

### `POST /transactions/{transaction_id}/ocr`

**Auth:** owner  
**Idempotency:** required or server-deduplicated  
Runs the OCR pipeline synchronously for the prototype or returns `202` if the implementation moves OCR to a job. The client must handle both consistently.

**Response when complete:** `200`

```json
{
  "data": {
    "transaction_id": "uuid",
    "status": "OCR_READY",
    "ocr_result_id": "uuid",
    "provider": {
      "value": "GENERIC_MOMO",
      "confidence": 0.82,
      "requires_review": false
    },
    "fields": {
      "transaction_reference": {
        "value": "ABC123456",
        "confidence": 0.94,
        "valid": true,
        "requires_review": false
      },
      "amount": {
        "value": "125.00",
        "currency": "GHS",
        "confidence": 0.71,
        "valid": true,
        "requires_review": true
      },
      "receiver_phone": {
        "value": "+233240000001",
        "masked": "+233 24 *** 0001",
        "confidence": 0.88,
        "requires_review": false
      }
    },
    "warnings": ["AMOUNT_LOW_CONFIDENCE"],
    "fraud_preview": {
      "schema_version": "momo-text-fraud-assessment-v1",
      "ruleset_version": "ghana-momo-obvious-scam-rules-v1",
      "status": "SUCCESS",
      "class": "FRAUDULENT",
      "score": 94,
      "score_is_probability": false,
      "reason_code": "OBVIOUS_SCAM_TEXT_DETECTED",
      "reason_codes": ["PIN_OR_OTP_REQUEST"],
      "reasons": [
        {
          "code": "PIN_OR_OTP_REQUEST",
          "title": "Secret code requested",
          "summary": "The text asks the user to disclose a MoMo PIN, OTP or security code. Legitimate support should not request these secrets.",
          "severity": "CRITICAL"
        }
      ],
      "evidence_quality": "HIGH",
      "limitations": [],
      "summary": "The screenshot contains strong scam-language indicators and should be treated as high risk.",
      "disclaimer": "This is a rule-based risk assessment of the supplied screenshot text, not live confirmation from a mobile-network operator or a legal determination."
    },
    "preview_url": "/api/v1/transactions/uuid/receipt?variant=thumbnail"
  },
  "meta": {"request_id": "..."}
}
```

### `GET /transactions/{transaction_id}/ocr-review`

Returns current raw extraction projection, field confidence and validation warnings. It does not expose all raw token data to normal users unless needed for the UI.

Both OCR endpoints return the same persisted, allowlisted `fraud_preview`. The
preview is a deterministic assessment of the immutable OCR text. Its integer
`score` is rule-ranking information on a `0..100` scale and is explicitly not a
probability. A null class means that no decisive rule fired; it never means
`GENUINE`. Historical OCR results without a stored assessment return
`UNAVAILABLE` and are not silently recomputed under a newer ruleset. Raw match
spans, phone numbers, links, secrets and OCR text are excluded from the preview.

### `POST /transactions/{transaction_id}/ocr-confirmations`

**Auth:** owner  
**Headers:** `Idempotency-Key`  
**Request:**

```json
{
  "ocr_result_id": "uuid",
  "fields": {
    "provider_code": "GENERIC_MOMO",
    "transaction_reference": "ABC123456",
    "amount": "125.00",
    "currency": "GHS",
    "sender_name": "Demo Sender",
    "sender_phone": "+233240000002",
    "receiver_name": "Demo Receiver",
    "receiver_phone": "+233240000001",
    "occurred_at": "2026-08-08T14:30:00Z",
    "status_text": "Successful"
  },
  "correction_reasons": {
    "amount": "Corrected after checking the receipt image"
  }
}
```

**Response:** `201`, confirmation ID and `OCR_REVIEWED` state.

Server validates that the referenced OCR result belongs to the transaction/user and that required fields are canonical.

## 7. Analysis

### `POST /transactions/{transaction_id}/analyses`

**Auth:** owner  
**Headers:** `Idempotency-Key` required  
**Precondition:** OCR reviewed.

**Response:** `202`

During the phase-gated P09 build, stored/imported-record verification and deterministic image
evidence may complete before the model and risk components exist. The endpoint persists an
immutable `PARTIAL` analysis, returns both `analysis_run_id` and the transitional `analysis_id`
alias, sets `risk.status` to `UNAVAILABLE` with null class/score, returns separate `verification`
and `image_evidence` objects, and lists only genuinely unavailable stages. The image block has
null classification/probability and states that deterministic signals are supporting evidence,
not proof of fraud. If the private image is unavailable, that block returns an explicit reason
code without inventing values while completed verification evidence is retained. P13 replaces
this transitional response with the queued full-pipeline response below while retaining
idempotency and the separate verification/image/risk objects.

The current categorical policy also consumes the version-bound OCR text
assessment during the existing `SEMANTIC_RULES` stage. `FRAUDULENT` text maps to
the high review band and `SUSPICIOUS` text maps to the medium review band. The
overall `risk.score` remains null until calibrated model evidence exists, and
missing required image or structured models keep the analysis `PARTIAL`.
Stored-reference verification remains a separate object and never overwrites or
authenticates the text-risk result.

```json
{
  "data": {
    "analysis_run_id": "uuid",
    "transaction_id": "uuid",
    "status": "QUEUED",
    "current_stage": "WAITING",
    "poll_url": "/api/v1/analyses/uuid",
    "estimated_message": "Your receipt is queued for analysis."
  },
  "meta": {"request_id": "..."}
}
```

### `GET /analyses/{analysis_run_id}`

**Auth:** owner, authorised staff

Active response:

```json
{
  "data": {
    "id": "uuid",
    "status": "PROCESSING",
    "current_stage": "IMAGE_FEATURES",
    "progress": {
      "completed_stages": 3,
      "total_stages": 9
    },
    "started_at": "..."
  },
  "meta": {"request_id": "..."}
}
```

Completed response:

```json
{
  "data": {
    "id": "uuid",
    "status": "COMPLETED",
    "risk": {
      "class": "SUSPICIOUS",
      "score": 57.4,
      "label": "Suspicious",
      "disclaimer": "This is an automated risk assessment, not a final legal determination.",
      "reasons": [
        {
          "code": "REFERENCE_AMOUNT_MISMATCH",
          "title": "Amount does not match the reference record",
          "severity": "HIGH"
        },
        {
          "code": "TEXT_ALIGNMENT_INCONSISTENCY",
          "title": "Some receipt text is not aligned as expected",
          "severity": "MEDIUM"
        }
      ]
    },
    "verification": {
      "status": "MISMATCH",
      "label": "Reference mismatch",
      "basis": "STORED_IMPORTED_RECORD",
      "summary": "A reference record was found, but the amount differed."
    },
    "evidence_summary": {
      "ocr_field_coverage": 0.93,
      "image_model_status": "SUCCESS",
      "structured_model_status": "SUCCESS",
      "rules_triggered": 2
    },
    "versions": {
      "ocr_pipeline": "ocr-1.0.0",
      "template": "generic-1.0.0",
      "image_model": "image-1.0.0",
      "structured_model": "rf-1.0.0",
      "rule_set": "rules-1.0.0"
    },
    "completed_at": "..."
  },
  "meta": {"request_id": "..."}
}
```

A normal user receives an understandable summary, not every raw internal feature. Authorised evidence endpoints provide more detail.

### `GET /analyses/{analysis_run_id}/evidence`

**Auth:** owner receives user-safe evidence; ADMIN/INVESTIGATOR receives role-appropriate detailed evidence.  
Returns sections:

- OCR and corrections;
- image evidence/reasons;
- model outputs/status/version;
- rule evaluations;
- reference field comparisons;
- stage timing;
- human review status when present.

P09 implements the immutable owner/staff projection for the evidence available so far:
verification comparisons, deterministic metadata/duplicate/recompression/noise/layout/quality
signals, stage status and version snapshots. Owner projections omit diagnostic-media links.
ADMIN/INVESTIGATOR projections may include protected `ela` and `noise-map` URLs. No projection
contains a storage object key, another user's identity, an image tamper probability or a final
fraud class before the corresponding later phases exist.

### `POST /transactions/{transaction_id}/reanalyses`

Optional explicit reanalysis after a completed/partial/failed run. Requires reason and creates a new run linked to the previous one. Never overwrites.

## 8. User history, reports and notifications

### `GET /transactions`

**Auth:** owner  
**Query:**

- `page`, `page_size`;
- `date_from`, `date_to`;
- `risk_class`;
- `verification_status`;
- `provider_code`;
- `status`;
- `search` limited to user's masked/reference-safe fields.

Returns transaction cards with latest persisted result.

### `GET /transactions/{transaction_id}`

Returns user-safe transaction detail, receipt thumbnail endpoint, OCR snapshot, latest/result history, report/case status and available actions.

### `POST /transactions/{transaction_id}/reports`

Generates or returns an idempotent analysis summary artifact.

### `GET /reports/{report_id}/download`

Authorised binary stream. `Content-Disposition` uses a generated safe filename.

### `GET /notifications`

Owner's paginated notifications with unread filter.

### `GET /notifications/unread-count`

Small unread-count response.

### `POST /notifications/{notification_id}/read`

Marks one owned notification as read.

### `POST /notifications/read-all`

Marks the authenticated user's notifications read; idempotent.

## 9. User fraud reports

### `POST /transactions/{transaction_id}/fraud-reports`

**Auth:** owner  
**Request:**

```json
{
  "category": "PAYMENT_NOT_RECEIVED",
  "description": "The sender showed this receipt, but the expected payment was not received."
}
```

**Response:** `201` with case ID/status. If an open case exists, return/link it according to idempotency policy rather than creating duplicates.

### `GET /fraud-reports/{case_id}`

Owner receives limited case status/timeline for cases they reported. Staff use the admin case endpoints.

## 10. Staff dashboard and transaction search

All routes below require ADMIN and/or INVESTIGATOR as declared.

### `GET /admin/dashboard`

Query `date_from`, `date_to`, `provider_code`.

Returns:

- analyses by risk/status;
- verification counts;
- case counts;
- average/p95 processing time where available;
- active model/rule/template status;
- recent operational warnings.

### `GET /admin/transactions`

Paginated staff search with masked default projection. Full evidence requires a separate authorised detail call.

### `GET /admin/transactions/{transaction_id}`

Role-projected detail. Every access is audited.

### `GET /admin/system-status`

Dependency matrix, worker heartbeat/queue depth, active versions and safe storage/database status.

## 11. Staff user management

### `GET /admin/users`

ADMIN only; filter by status/role/search.

### `POST /admin/users`

Creates staff/user account according to policy. Temporary-password delivery is not included in the response/log.

### `PATCH /admin/users/{user_id}`

Allowlisted profile/status changes with optimistic version.

### `PUT /admin/users/{user_id}/roles`

Replaces/updates roles. Prevents last-admin removal and self-lockout according to policy.

### `POST /admin/users/{user_id}/revoke-sessions`

Revokes active refresh sessions.

## 12. Reference imports and records

### `POST /admin/reference-imports`

ADMIN; multipart CSV, idempotency key. Stores private original and returns batch with `UPLOADED`.

### `POST /admin/reference-imports/{batch_id}/validate`

Parses/normalises without committing reference rows.

```json
{
  "data": {
    "batch": {
      "id": "uuid",
      "status": "VALIDATED",
      "total_rows": 100,
      "valid_rows": 94,
      "invalid_rows": 6
    },
    "batch_id": "uuid",
    "status": "VALIDATED",
    "total_rows": 100,
    "valid_rows": 94,
    "invalid_rows": 6,
    "errors": [
      {"row": 4, "field": "amount", "code": "INVALID_DECIMAL"}
    ],
    "invalid_rows_download": "/api/v1/admin/reference-imports/uuid/invalid-rows",
    "preview_truncated": false
  },
  "meta": {"request_id": "..."}
}
```

### `POST /admin/reference-imports/{batch_id}/commit`

Commits valid rows atomically or in documented batches with reconciliation. Requires optimistic status and idempotency.

### `GET /admin/reference-imports`

### `GET /admin/reference-imports/{batch_id}`

### `GET /admin/reference-imports/{batch_id}/invalid-rows`

### `GET /admin/reference-transactions`

Masked/searchable; do not expose raw imported row indiscriminately.

### `GET /admin/reference-transactions/{id}`

ADMIN/INVESTIGATOR according to purpose; audited.

## 13. Receipt templates

### `GET /admin/receipt-templates`

### `POST /admin/receipt-templates`

Creates DRAFT version.

### `GET /admin/receipt-templates/{id}`

### `PATCH /admin/receipt-templates/{id}`

Draft only or creates a new version; do not mutate active historical version.

### `POST /admin/receipt-templates/{id}/validate`

Validates configuration and optional safe fixture.

### `POST /admin/receipt-templates/{id}/activate`

ADMIN only, optimistic lock, audit.

### `POST /admin/receipt-templates/{id}/retire`

Cannot break historical references.

## 14. Rules and thresholds

### `GET /admin/rule-sets`

### `POST /admin/rule-sets`

Creates DRAFT version with risk weights/thresholds.

### `GET /admin/rule-sets/{id}`

### `PATCH /admin/rule-sets/{id}`

Draft only.

### `POST /admin/rule-sets/{id}/validate`

Validates weights, threshold ordering, reason codes and referenced features.

### `POST /admin/rule-sets/{id}/activate`

Checks weights sum policy and model/feature compatibility. Audit.

### `POST /admin/rule-sets/{id}/retire`

## 15. Model registry

### `GET /admin/models`

Filter by type/status.

### `POST /admin/models/register`

Registers metadata for an already uploaded/private artifact or a controlled server-side artifact import. Never accepts arbitrary executable code.

### `GET /admin/models/{id}`

Returns safe model card/metrics/readiness.

### `POST /admin/models/{id}/verify`

Recomputes artifact hash, checks framework/schema/preprocessing compatibility and performs a safe smoke inference.

### `POST /admin/models/{id}/activate`

ADMIN, only `READY`, audit, cache invalidation.

### `POST /admin/models/{id}/retire`

Historical predictions retain the FK.

## 16. Investigator case API

### `GET /admin/cases`

ADMIN/INVESTIGATOR; filter by status, assignment, risk, provider, date, source.

### `GET /admin/cases/{case_id}`

Returns case, masked user/transaction information, original result, OCR, image evidence, model outputs, rule evaluations, verification comparisons, reports and timeline. Receipt variants use protected endpoints.

### `POST /admin/cases/{case_id}/assign`

Valid investigator target, optimistic state.

### `POST /admin/cases/{case_id}/start-review`

Moves OPEN to IN_REVIEW.

### `POST /admin/cases/{case_id}/notes`

Adds append-only note/event.

### `POST /admin/cases/{case_id}/decisions`

```json
{
  "outcome": "ESCALATED",
  "reason": "The amount and receiver details conflict with the imported reference record.",
  "expected_case_version": 4
}
```

Response returns the new case state and decision ID. The automated result remains untouched.

### `POST /admin/cases/{case_id}/reports`

### `GET /admin/cases/{case_id}/reports/{report_id}/download`

## 17. Audit and operational reports

### `GET /admin/audit-logs`

ADMIN; query actor, action, target type/ID, outcome, date and request ID. Metadata is already redacted.

### `GET /admin/reports/operations`

Generates bounded operational CSV/PDF summaries. Large export must be asynchronous or strictly capped.

## 18. Webhook/notification adapters

External push/email is optional. When implemented:

- use an authenticated outbound adapter;
- do not include full receipt images or unmasked transaction data in message bodies;
- store provider message ID and delivery status, not provider secrets;
- retry bounded transient errors;
- preserve in-app notification;
- verify inbound webhook signatures before updating delivery status.

## 19. API permission matrix

| Resource/action | USER owner | ADMIN | INVESTIGATOR |
|---|---:|---:|---:|
| Register/login/self profile | Yes | Yes | Yes |
| Upload/view own receipt | Yes | Configured staff view | Case/authorised view |
| Correct own OCR | Yes | No by default | No by default |
| Start own analysis | Yes | Optional support | No by default |
| View own history/report | Yes | Authorised | Authorised case |
| Report own transaction | Yes | View | Review |
| Manage users/roles | No | Yes | No |
| Import reference records | No | Yes | Read if needed |
| Manage templates/rules/models | No | Yes | Read active evidence |
| View dashboard | No | Yes | Limited/yes |
| Review/decide case | No | Optional capability | Yes |
| View audit logs | No | Yes | Limited case timeline |

The server enforces this matrix. Hiding a button is not authorisation.

## 20. Contract tests

For every endpoint Codex must test:

- success response schema;
- authentication;
- role permission;
- object ownership;
- validation/error envelope;
- idempotency/conflict where relevant;
- pagination/filter limits;
- audit event where required;
- no private object key/secret leakage;
- OpenAPI snapshot/generation consistency.

No endpoint is complete when only its happy path works.
