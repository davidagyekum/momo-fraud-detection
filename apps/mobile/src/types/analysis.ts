import { z } from "zod";

export const riskBandSchema = z.enum([
  "low_risk",
  "medium_risk",
  "high_risk",
  "inconclusive",
]);

export const analysisStatusSchema = z.enum([
  "QUEUED",
  "PROCESSING",
  "COMPLETED",
  "PARTIAL",
  "FAILED",
  "CANCELLED",
]);

export const verificationStatusSchema = z.enum([
  "VERIFIED",
  "MISMATCH",
  "UNVERIFIED",
]);

export const policyReasonSchema = z
  .object({
    code: z.string(),
    title: z.string(),
    severity: z.enum(["INFORMATIONAL", "LOW", "MEDIUM", "HIGH", "CRITICAL"]),
  })
  .strict();

export const riskSchema = z
  .object({
    status: z.string(),
    band: riskBandSchema,
    class: z.enum(["GENUINE", "SUSPICIOUS", "FRAUDULENT"]).nullable(),
    score: z.number().min(0).max(1).nullable(),
    summary: z.string(),
    reasons: z.array(policyReasonSchema),
    missing_signals: z.array(z.string()),
    limitations: z.array(z.string()),
    policy_version: z.string(),
    disclaimer: z.string(),
  })
  .strict();

export const verificationSchema = z
  .object({
    status: verificationStatusSchema,
    label: z.string(),
    basis: z.literal("STORED_IMPORTED_RECORD"),
    summary: z.string(),
    reference_transaction_id: z.string().nullable(),
    candidate_method: z.string(),
    verifier_version: z.string(),
    rule_set_version: z.string().nullable(),
    field_comparisons: z.record(z.string(), z.unknown()),
    matched_field_count: z.number().int().nonnegative(),
    mismatched_field_count: z.number().int().nonnegative(),
    warnings: z.array(z.string()),
    disclaimer: z.string(),
  })
  .strict();

export const componentStatusSchema = z
  .object({
    status: z.enum([
      "COMPLETED",
      "FAILED",
      "SKIPPED",
      "SUCCESS",
      "UNAVAILABLE",
      "ERROR",
    ]),
    reason_code: z.string().nullable().optional(),
    reason_codes: z.array(z.string()).optional(),
    model_version: z.string().nullable().optional(),
  })
  .strict();

export const analysisStageSchema = z
  .object({
    stage: z.string(),
    status: z.enum(["QUEUED", "RUNNING", "COMPLETED", "SKIPPED", "FAILED"]),
    attempt: z.number().int().positive(),
    duration_ms: z.number().int().nonnegative().nullable(),
    error_code: z.string().nullable(),
  })
  .strict();

export const analysisStartSchema = z
  .object({
    analysis_run_id: z.string().min(1),
    transaction_id: z.string().min(1),
    status: analysisStatusSchema,
    current_stage: z.string().nullable(),
    poll_url: z.string(),
    replayed: z.boolean(),
  })
  .strict();

export const analysisSchema = z
  .object({
    id: z.string().min(1),
    transaction_id: z.string().min(1),
    status: analysisStatusSchema,
    risk: riskSchema,
    verification: verificationSchema.nullable(),
    evidence_summary: z
      .object({
        deterministic_image: componentStatusSchema,
        image_model: componentStatusSchema,
        structured_model: componentStatusSchema,
        automated_evidence_immutable: z.literal(true),
      })
      .strict(),
    ocr_review: z
      .object({
        confirmed_field_count: z.number().int().nonnegative(),
        correction_count: z.number().int().nonnegative(),
        schema_version: z.string(),
      })
      .strict(),
    versions: z
      .object({
        policy_version: z.string().nullable(),
        policy_sha256: z.string().nullable(),
        rule_set_version: z.string().nullable(),
        ocr_pipeline_version: z.string().nullable(),
        ocr_engine_version: z.string().nullable(),
        image_forensics_version: z.string().nullable(),
        image_model_version: z.string().nullable(),
        structured_model_version: z.string().nullable(),
      })
      .strict(),
    progress: z
      .object({
        current_stage: z.string().nullable(),
        completed_stage_count: z.number().int().nonnegative(),
        total_stage_count: z.number().int().nonnegative(),
        stages: z.array(analysisStageSchema),
      })
      .strict(),
    evidence_url: z.string(),
    created_at: z.string(),
    completed_at: z.string().nullable(),
  })
  .strict();

export type AnalysisStart = z.infer<typeof analysisStartSchema>;
export type AnalysisResult = z.infer<typeof analysisSchema>;
export type AnalysisStatus = z.infer<typeof analysisStatusSchema>;
export type RiskBand = z.infer<typeof riskBandSchema>;
export type StoredReferenceVerification = z.infer<typeof verificationSchema>;
