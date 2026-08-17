import { z } from "zod";

import {
  analysisModeSchema,
  analysisStatusSchema,
  riskBandSchema,
  verificationStatusSchema,
} from "@/types/analysis";

export const transactionStatusSchema = z.enum([
  "DRAFT",
  "UPLOADED",
  "OCR_PENDING",
  "OCR_REVIEW",
  "READY",
  "ANALYSIS_QUEUED",
  "ANALYSING",
  "COMPLETED",
  "PARTIAL",
  "FAILED",
]);

export const transactionAnalysisSummarySchema = z
  .object({
    id: z.string().min(1),
    analysis_mode: analysisModeSchema,
    status: analysisStatusSchema,
    band: riskBandSchema,
    class: z.enum(["GENUINE", "SUSPICIOUS", "FRAUDULENT"]).nullable(),
    score: z.number().min(0).max(1).nullable(),
    verification_status: verificationStatusSchema.nullable(),
    completed_at: z.string().nullable(),
    policy_version: z.string(),
  })
  .strict();

export const transactionSummarySchema = z
  .object({
    id: z.string().min(1),
    status: transactionStatusSchema,
    provider_code: z.string().nullable(),
    display_reference_masked: z.string().nullable(),
    created_at: z.string(),
    updated_at: z.string(),
    thumbnail_url: z.string().nullable(),
    owner_visible: z.literal(true),
    latest_analysis: transactionAnalysisSummarySchema.nullable(),
  })
  .strict();

export const transactionHistorySchema = z
  .object({
    items: z.array(transactionSummarySchema),
    page: z.number().int().positive(),
    page_size: z.number().int().min(1).max(100),
    total: z.number().int().nonnegative(),
    total_pages: z.number().int().nonnegative(),
  })
  .strict();

export const transactionDetailSchema = transactionSummarySchema
  .extend({
    confirmed_field_coverage: z
      .object({
        status: z.enum(["CONFIRMED", "NOT_REQUIRED"]),
        ocr_result_id: z.string().min(1).nullable(),
        field_count: z.number().int().nonnegative(),
        correction_count: z.number().int().nonnegative(),
        schema_version: z.string().nullable(),
      })
      .strict(),
    analysis_runs: z.array(transactionAnalysisSummarySchema).max(20),
  })
  .strict();

export const historyFiltersSchema = z
  .object({
    page: z.number().int().positive().optional(),
    page_size: z.number().int().min(1).max(100).optional(),
    provider: z.string().min(1).optional(),
    status: transactionStatusSchema.optional(),
    verification: verificationStatusSchema.optional(),
    band: riskBandSchema.optional(),
  })
  .strict();

export type TransactionHistory = z.infer<typeof transactionHistorySchema>;
export type TransactionSummary = z.infer<typeof transactionSummarySchema>;
export type TransactionDetail = z.infer<typeof transactionDetailSchema>;
export type HistoryFilters = z.infer<typeof historyFiltersSchema>;
