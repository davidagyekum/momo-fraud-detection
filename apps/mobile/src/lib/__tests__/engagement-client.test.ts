import type { JsonRequest } from "@/lib/api";
import {
  createAnalysisReport,
  createFraudReport,
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  saveAndShareReport,
} from "@/lib/engagement-client";

const mockWrite = jest.fn();
const mockCreate = jest.fn();

jest.mock("expo-file-system", () => ({
  Paths: { cache: "/controlled-cache" },
  File: jest.fn().mockImplementation((_path: string, name: string) => ({
    uri: `file:///controlled-cache/${name}`,
    create: mockCreate,
    write: mockWrite,
  })),
}));

const meta = { request_id: "request-id" };

test("validates the notification inbox and owner read mutations", async () => {
  const item = {
    id: "notification-id",
    type: "ANALYSIS_COMPLETED",
    title: "Analysis ready",
    message: "Your analysis is ready.",
    target: { type: "ANALYSIS", id: "analysis-id" },
    read_at: null,
    created_at: "2026-08-15T12:00:00Z",
  };
  const request = jest
    .fn()
    .mockResolvedValueOnce({
      data: { items: [item], page: 1, page_size: 50, total: 1, total_pages: 1 },
      meta,
    })
    .mockResolvedValueOnce({
      data: { ...item, read_at: "2026-08-15T12:01:00Z" },
      meta,
    })
    .mockResolvedValueOnce({ data: { marked_read: 0, unread_count: 0 }, meta });

  const inbox = await listNotifications(request, true);
  expect(inbox.items[0]?.target?.type).toBe("ANALYSIS");
  await markNotificationRead(request, "notification/id");
  await markAllNotificationsRead(request);
  expect(request).toHaveBeenNthCalledWith(
    1,
    "/api/v1/notifications?unread=true&page=1&page_size=50",
  );
  expect(request).toHaveBeenNthCalledWith(
    2,
    "/api/v1/notifications/notification%2Fid/read",
    { method: "POST" },
  );
});

test("creates, downloads and shares a private analysis report", async () => {
  const artifact = {
    id: "report-id",
    report_type: "ANALYSIS",
    transaction_id: "transaction-id",
    analysis_run_id: "analysis-id",
    status: "READY",
    sha256: "a".repeat(64),
    generated_at: "2026-08-15T12:00:00Z",
    expires_at: null,
    download_url: "/api/v1/reports/report-id/download",
    replayed: false,
  } as const;
  const request = jest.fn(async () => ({ data: artifact, meta }));
  const created = await createAnalysisReport(
    request as JsonRequest,
    "transaction/id",
    "report-key-123",
  );
  const response = jest.fn(async () => new Response("<html>safe</html>"));
  const share = jest.fn(async () => undefined);
  const delivery = await saveAndShareReport(response, created, {
    isAvailable: async () => true,
    share,
  });

  expect(request).toHaveBeenCalledWith(
    "/api/v1/transactions/transaction%2Fid/reports",
    {
      method: "POST",
      headers: { "Idempotency-Key": "report-key-123" },
      body: JSON.stringify({ format: "HTML" }),
    },
  );
  expect(response).toHaveBeenCalledWith(artifact.download_url);
  expect(mockCreate).toHaveBeenCalledWith({ overwrite: true });
  expect(mockWrite).toHaveBeenCalled();
  expect(share).toHaveBeenCalledWith(
    expect.stringMatching(/^file:\/\/\/controlled-cache\/momo-analysis-/),
    expect.objectContaining({ mimeType: "text/html" }),
  );
  expect(delivery).toBe("shared");
});

test("submits a bounded owner fraud report and validates the linked case", async () => {
  const fraudCase = {
    id: "case-id",
    transaction_id: "transaction-id",
    source: "USER_REPORT",
    category: "OTHER",
    status: "OPEN",
    version: 1,
    opened_at: "2026-08-15T12:00:00Z",
    updated_at: "2026-08-15T12:00:00Z",
    timeline: [],
    replayed: false,
    linked_existing: false,
  };
  const request = jest.fn(async () => ({ data: fraudCase, meta }));
  const result = await createFraudReport(
    request as JsonRequest,
    "transaction/id",
    "case-key-123",
    {
      category: "OTHER",
      description: "Controlled concern.",
    },
  );
  expect(result.id).toBe("case-id");
  expect(request).toHaveBeenCalledWith(
    "/api/v1/transactions/transaction%2Fid/fraud-reports",
    expect.objectContaining({ method: "POST" }),
  );
});
