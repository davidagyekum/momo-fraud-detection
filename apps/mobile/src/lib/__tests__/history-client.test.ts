import { getTransaction, listTransactions } from "@/lib/history-client";

const analysis = {
  id: "analysis-id",
  analysis_mode: "combined",
  status: "PARTIAL",
  band: "inconclusive",
  class: null,
  score: null,
  verification_status: "UNVERIFIED",
  completed_at: "2026-08-15T12:00:00Z",
  policy_version: "risk-policy-v1",
} as const;

const summary = {
  id: "transaction-id",
  status: "PARTIAL",
  provider_code: "MTN_MOMO",
  display_reference_masked: "ABC...123",
  created_at: "2026-08-15T11:00:00Z",
  updated_at: "2026-08-15T12:00:00Z",
  thumbnail_url:
    "/api/v1/transactions/transaction-id/receipt?variant=thumbnail",
  owner_visible: true,
  latest_analysis: analysis,
} as const;

test("encodes validated owner-history filters", async () => {
  const request = jest.fn().mockResolvedValue({
    data: {
      items: [summary],
      page: 2,
      page_size: 50,
      total: 1,
      total_pages: 1,
    },
    meta: { request_id: "request-id" },
  });

  const result = await listTransactions(request, {
    page: 2,
    page_size: 50,
    band: "inconclusive",
    provider: "MTN/MOMO",
  });

  expect(result.items).toHaveLength(1);
  expect(request).toHaveBeenCalledWith(
    "/api/v1/transactions?page=2&page_size=50&provider=MTN%2FMOMO&band=inconclusive",
  );
});

test("rejects invalid pagination and band before transport", async () => {
  const request = jest.fn();
  await expect(listTransactions(request, { page_size: 101 })).rejects.toThrow(
    "History filters are invalid",
  );
  await expect(
    listTransactions(request, { band: "safe" as never }),
  ).rejects.toThrow("History filters are invalid");
  expect(request).not.toHaveBeenCalled();
});

test("validates transaction detail and encodes the path", async () => {
  const request = jest.fn().mockResolvedValue({
    data: {
      ...summary,
      confirmed_field_coverage: {
        status: "CONFIRMED",
        ocr_result_id: "ocr-result-id",
        field_count: 2,
        correction_count: 1,
        schema_version: "ocr-fields-v1",
      },
      analysis_runs: [analysis],
    },
    meta: { request_id: "request-id" },
  });

  const detail = await getTransaction(request, "transaction/id");

  expect(detail.analysis_runs).toHaveLength(1);
  expect(request).toHaveBeenCalledWith("/api/v1/transactions/transaction%2Fid");
});
