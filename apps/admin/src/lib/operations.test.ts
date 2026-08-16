import { describe, expect, it, vi } from "vitest";
import {
  addCaseNote,
  assignCase,
  createCaseReport,
  decideCase,
  getAuditLogs,
  getCase,
  getCases,
  getDashboard,
  getModels,
  getReports,
  getRuleSets,
  getSystemStatus,
  getTransaction,
  getTransactions,
  startReview,
  type PortalRequest,
} from "./operations";

const now = "2026-08-16T12:00:00Z";
const transaction = {
  id: "transaction/one",
  provider_code: "MTN",
  display_reference_masked: "***1234",
  status: "ANALYSED",
  created_at: now,
  updated_at: now,
  analysis: null,
  case: null,
};
const caseItem = {
  id: "case/one",
  transaction_id: transaction.id,
  source: "USER_REPORT",
  category: "suspicious",
  status: "OPEN",
  version: 1,
  opened_at: now,
  updated_at: now,
};
const page = { page: 1, page_size: 25, total: 1, total_pages: 1 };

function dataFor(path: string): unknown {
  if (path === "/admin/dashboard") {
    return {
      risk_counts: { high: 1 },
      verification_counts: { MISMATCH: 1 },
      case_status_counts: { OPEN: 1 },
      case_source_counts: { USER_REPORT: 1 },
      analysis_status_counts: { COMPLETED: 1 },
      processing_duration_ms: { average: 50, p95: 50 },
      active_versions: { models: [], rule_set: null },
      recent_activity: [],
    };
  }
  if (path.includes("/transactions/")) return transaction;
  if (path.includes("/transactions")) return { ...page, items: [transaction] };
  if (path.includes("/cases/") && path.endsWith("/reports")) {
    return {
      id: "report-one",
      report_type: "CASE",
      status: "READY",
      download_url: "/private/report-one",
      replayed: false,
    };
  }
  if (path.includes("/cases/") && !path.endsWith("/reports")) return caseItem;
  if (path.includes("/cases")) return { ...page, items: [caseItem] };
  if (path.includes("audit-logs")) {
    return {
      ...page,
      items: [
        {
          id: "audit-one",
          action: "case.viewed",
          outcome: "SUCCESS",
          target_type: "fraud_case",
          actor_roles: ["ADMIN"],
          created_at: now,
        },
      ],
    };
  }
  if (path.includes("system-status")) {
    return {
      ready: true,
      analysis_available: true,
      full_analysis_available: false,
      components: { database: { status: "ready" } },
    };
  }
  if (path.includes("/models")) {
    return {
      ...page,
      items: [
        {
          id: "model-one",
          model_type: "IMAGE",
          name: "receipt",
          version: "1",
          status: "ACTIVE",
          preprocessing_version: "1",
          created_at: now,
        },
      ],
    };
  }
  if (path.includes("rule-sets")) {
    return {
      ...page,
      items: [
        {
          id: "rules-one",
          version: "1",
          status: "ACTIVE",
          description: "Controlled rules",
          row_version: 1,
          rule_count: 2,
          created_at: now,
        },
      ],
    };
  }
  if (path.includes("/reports?")) {
    return {
      ...page,
      items: [
        {
          id: "report-one",
          report_type: "CASE",
          case_id: "case-one",
          source_version: 1,
          status: "READY",
          sha256: "a".repeat(64),
          generated_at: now,
          download_url: "/private/report-one",
        },
      ],
    };
  }
  throw new Error(`Unexpected test path: ${path}`);
}

describe("operations client", () => {
  it("validates all staff read models and builds bounded URLs", async () => {
    const mock = vi.fn((path: string) =>
      Promise.resolve({ data: dataFor(path), meta: { request_id: "test" } }),
    );
    const request = mock as PortalRequest;

    await Promise.all([
      getDashboard(request),
      getTransactions(request, 2),
      getTransaction(request, "transaction/one"),
      getCases(request, 3),
      getCase(request, "case/one"),
      getAuditLogs(request, 4),
      getSystemStatus(request),
      getModels(request),
      getRuleSets(request),
      getReports(request, 5),
    ]);

    expect(mock).toHaveBeenCalledWith("/admin/transactions/transaction%2Fone");
    expect(mock).toHaveBeenCalledWith("/admin/reports?page=5&page_size=25");
  });

  it("submits versioned case actions and report idempotency", async () => {
    const mock = vi.fn((path: string) =>
      Promise.resolve({ data: dataFor(path), meta: { request_id: "test" } }),
    );
    const request = mock as PortalRequest;

    await assignCase(request, "case/one", "investigator-one", 1);
    await startReview(request, "case/one", 2);
    await addCaseNote(request, "case/one", 3, "Controlled note");
    await decideCase(
      request,
      "case/one",
      4,
      "CONFIRMED_FRAUD",
      "Evidence reviewed",
    );
    await createCaseReport(request, "case/one", "report-key-one");

    expect(mock).toHaveBeenLastCalledWith(
      "/admin/cases/case%2Fone/reports",
      expect.objectContaining({
        method: "POST",
        headers: { "Idempotency-Key": "report-key-one" },
      }),
    );
  });

  it("fails closed on an incompatible server response", async () => {
    const request = vi.fn(() =>
      Promise.resolve({
        data: { unexpected: true },
        meta: { request_id: "test" },
      }),
    ) as PortalRequest;
    await expect(getDashboard(request)).rejects.toThrow("incompatible");
  });
});
