import { z } from "zod";

export const notificationTargetSchema = z
  .object({ type: z.string(), id: z.string().min(1) })
  .strict();

export const notificationSchema = z
  .object({
    id: z.string().min(1),
    type: z.string(),
    title: z.string(),
    message: z.string(),
    target: notificationTargetSchema.nullable(),
    read_at: z.string().nullable(),
    created_at: z.string(),
  })
  .strict();

export const notificationListSchema = z
  .object({
    items: z.array(notificationSchema),
    page: z.number().int().positive(),
    page_size: z.number().int().positive(),
    total: z.number().int().nonnegative(),
    total_pages: z.number().int().nonnegative(),
  })
  .strict();

export const unreadCountSchema = z
  .object({ unread_count: z.number().int().nonnegative() })
  .strict();

export const readAllSchema = z
  .object({
    marked_read: z.number().int().nonnegative(),
    unread_count: z.number().int().nonnegative(),
  })
  .strict();

export const reportArtifactSchema = z
  .object({
    id: z.string().min(1),
    report_type: z.literal("ANALYSIS"),
    transaction_id: z.string().nullable(),
    analysis_run_id: z.string().nullable(),
    status: z.enum(["GENERATING", "READY", "FAILED", "EXPIRED"]),
    sha256: z.string().length(64).nullable(),
    generated_at: z.string().nullable(),
    expires_at: z.string().nullable(),
    download_url: z.string().nullable(),
    replayed: z.boolean(),
  })
  .strict();

export const caseEventSchema = z
  .object({
    id: z.string().min(1),
    event_type: z.string(),
    from_status: z.string().nullable(),
    to_status: z.string().nullable(),
    created_at: z.string(),
  })
  .strict();

export const ownerCaseSchema = z
  .object({
    id: z.string().min(1),
    transaction_id: z.string().min(1),
    source: z.string(),
    category: z.string(),
    status: z.string(),
    version: z.number().int().positive(),
    opened_at: z.string(),
    updated_at: z.string(),
    timeline: z.array(caseEventSchema),
    replayed: z.boolean().optional(),
    linked_existing: z.boolean().optional(),
  })
  .strict();

export type AppNotification = z.infer<typeof notificationSchema>;
export type NotificationList = z.infer<typeof notificationListSchema>;
export type OwnerCase = z.infer<typeof ownerCaseSchema>;
export type ReportArtifact = z.infer<typeof reportArtifactSchema>;
