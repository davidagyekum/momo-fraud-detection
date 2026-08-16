import { z } from "zod";
import type { ApiEnvelope } from "../types/api";

export type PortalRequest = <T>(
  path: string,
  init?: RequestInit,
) => Promise<ApiEnvelope<T>>;

const pageSchema = z.object({
  page: z.number().int().positive(),
  page_size: z.number().int().positive(),
  total: z.number().int().nonnegative(),
  total_pages: z.number().int().nonnegative(),
});

const analysisSummarySchema = z.object({
  id: z.string(),
  status: z.string(),
  risk_band: z.string(),
  verification_status: z.string().nullable(),
  completed_at: z.string().nullable(),
});

const transactionSchema = z.object({
  id: z.string(),
  provider_code: z.string().nullable(),
  display_reference_masked: z.string().nullable(),
  status: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
  analysis: analysisSummarySchema.nullable(),
  case: z
    .object({ id: z.string(), status: z.string(), source: z.string() })
    .nullable(),
  receipt_available: z.boolean().optional(),
  ocr_confirmation_count: z.number().int().nonnegative().optional(),
  automated_evidence_immutable: z.literal(true).optional(),
});

const caseEventSchema = z.object({
  id: z.string(),
  event_type: z.string(),
  from_status: z.string().nullable(),
  to_status: z.string().nullable(),
  reason: z.string().nullable().optional(),
  actor_id: z.string().optional(),
  created_at: z.string(),
});

export const caseSchema = z.object({
  id: z.string(),
  transaction_id: z.string(),
  source: z.string(),
  category: z.string(),
  status: z.string(),
  version: z.number().int().positive(),
  opened_at: z.string(),
  updated_at: z.string(),
  assigned_to: z.string().nullable().optional(),
  description: z.string().nullable().optional(),
  timeline: z.array(caseEventSchema).optional(),
  decisions: z
    .array(
      z.object({
        id: z.string(),
        outcome: z.string(),
        reason: z.string(),
        created_at: z.string().optional(),
      }),
    )
    .optional(),
  automated_evidence: z
    .object({
      immutable: z.literal(true),
      analysis_run_id: z.string().nullable(),
      status: z.string(),
      risk_band: z.string(),
      risk_class: z.string().nullable(),
    })
    .optional(),
});

const transactionListSchema = pageSchema.extend({
  items: z.array(transactionSchema),
});
const caseListSchema = pageSchema.extend({ items: z.array(caseSchema) });

const dashboardSchema = z.object({
  risk_counts: z.record(z.string(), z.number()),
  verification_counts: z.record(z.string(), z.number()),
  case_status_counts: z.record(z.string(), z.number()),
  case_source_counts: z.record(z.string(), z.number()),
  analysis_status_counts: z.record(z.string(), z.number()),
  processing_duration_ms: z.object({
    average: z.number().nullable(),
    p95: z.number().nullable(),
  }),
  active_versions: z.object({
    models: z.array(
      z.object({ type: z.string(), name: z.string(), version: z.string() }),
    ),
    rule_set: z.string().nullable(),
  }),
  recent_activity: z.array(
    z.object({
      id: z.string(),
      action: z.string(),
      outcome: z.string(),
      target_type: z.string(),
      created_at: z.string(),
    }),
  ),
});

const auditListSchema = pageSchema.extend({
  items: z.array(
    z.object({
      id: z.string(),
      action: z.string(),
      outcome: z.string(),
      target_type: z.string(),
      actor_roles: z.array(z.string()),
      created_at: z.string(),
    }),
  ),
});

const statusSchema = z.object({
  ready: z.boolean(),
  analysis_available: z.boolean(),
  full_analysis_available: z.boolean(),
  components: z.record(
    z.string(),
    z.object({
      status: z.string(),
      reason: z.string().optional(),
      version: z.string().optional(),
    }),
  ),
});

const modelListSchema = pageSchema.extend({
  items: z.array(
    z.object({
      id: z.string(),
      model_type: z.string(),
      name: z.string(),
      version: z.string(),
      status: z.string(),
      preprocessing_version: z.string(),
      created_at: z.string(),
    }),
  ),
});

const ruleListSchema = pageSchema.extend({
  items: z.array(
    z.object({
      id: z.string(),
      version: z.string(),
      status: z.string(),
      description: z.string(),
      row_version: z.number(),
      rule_count: z.number(),
      created_at: z.string(),
    }),
  ),
});

const reportSchema = z.object({
  id: z.string(),
  report_type: z.literal("CASE"),
  status: z.literal("READY"),
  download_url: z.string(),
  replayed: z.boolean(),
});

const reportListSchema = pageSchema.extend({
  items: z.array(
    z.object({
      id: z.string(),
      report_type: z.literal("CASE"),
      case_id: z.string(),
      source_version: z.number().int().positive(),
      status: z.string(),
      sha256: z.string().nullable(),
      generated_at: z.string().nullable(),
      download_url: z.string().nullable(),
    }),
  ),
});

function parse<T>(schema: z.ZodType<T>, value: unknown, label: string): T {
  const result = schema.safeParse(value);
  if (!result.success) throw new Error(`${label} response is incompatible.`);
  return result.data;
}

export async function getDashboard(request: PortalRequest) {
  return parse(
    dashboardSchema,
    (await request("/admin/dashboard")).data,
    "Dashboard",
  );
}

export async function getTransactions(request: PortalRequest, page = 1) {
  return parse(
    transactionListSchema,
    (await request(`/admin/transactions?page=${String(page)}&page_size=25`))
      .data,
    "Transactions",
  );
}

export async function getTransaction(request: PortalRequest, id: string) {
  return parse(
    transactionSchema,
    (await request(`/admin/transactions/${encodeURIComponent(id)}`)).data,
    "Transaction",
  );
}

export async function getCases(request: PortalRequest, page = 1) {
  return parse(
    caseListSchema,
    (await request(`/admin/cases?page=${String(page)}&page_size=25`)).data,
    "Cases",
  );
}

export async function getCase(request: PortalRequest, id: string) {
  return parse(
    caseSchema,
    (await request(`/admin/cases/${encodeURIComponent(id)}`)).data,
    "Case",
  );
}

async function mutateCase(
  request: PortalRequest,
  id: string,
  action: string,
  body: Record<string, unknown>,
) {
  return parse(
    caseSchema,
    (
      await request(`/admin/cases/${encodeURIComponent(id)}/${action}`, {
        method: "POST",
        body: JSON.stringify(body),
      })
    ).data,
    "Case update",
  );
}

export const assignCase = (
  request: PortalRequest,
  id: string,
  investigatorId: string,
  version: number,
) =>
  mutateCase(request, id, "assign", {
    investigator_id: investigatorId,
    expected_case_version: version,
  });

export const startReview = (
  request: PortalRequest,
  id: string,
  version: number,
) =>
  mutateCase(request, id, "start-review", { expected_case_version: version });

export const addCaseNote = (
  request: PortalRequest,
  id: string,
  version: number,
  note: string,
) => mutateCase(request, id, "notes", { expected_case_version: version, note });

export const decideCase = (
  request: PortalRequest,
  id: string,
  version: number,
  outcome: string,
  reason: string,
) =>
  mutateCase(request, id, "decisions", {
    expected_case_version: version,
    outcome,
    reason,
  });

export async function getAuditLogs(request: PortalRequest, page = 1) {
  return parse(
    auditListSchema,
    (await request(`/admin/audit-logs?page=${String(page)}&page_size=25`)).data,
    "Audit log",
  );
}

export async function getSystemStatus(request: PortalRequest) {
  return parse(
    statusSchema,
    (await request("/admin/system-status")).data,
    "Status",
  );
}

export async function getModels(request: PortalRequest) {
  return parse(
    modelListSchema,
    (await request("/admin/models")).data,
    "Models",
  );
}

export async function getRuleSets(request: PortalRequest) {
  return parse(
    ruleListSchema,
    (await request("/admin/rule-sets")).data,
    "Rule sets",
  );
}

export async function createCaseReport(
  request: PortalRequest,
  caseId: string,
  idempotencyKey: string,
) {
  return parse(
    reportSchema,
    (
      await request(`/admin/cases/${encodeURIComponent(caseId)}/reports`, {
        method: "POST",
        headers: { "Idempotency-Key": idempotencyKey },
        body: JSON.stringify({ format: "HTML" }),
      })
    ).data,
    "Case report",
  );
}

export async function getReports(request: PortalRequest, page = 1) {
  return parse(
    reportListSchema,
    (await request(`/admin/reports?page=${String(page)}&page_size=25`)).data,
    "Reports",
  );
}

export type DashboardData = z.infer<typeof dashboardSchema>;
export type TransactionRow = z.infer<typeof transactionSchema>;
export type CaseRow = z.infer<typeof caseSchema>;
