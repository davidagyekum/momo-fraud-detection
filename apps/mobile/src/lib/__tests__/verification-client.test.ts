import {
  createAnalysisIdempotencyKey,
  runStoredReferenceVerification,
  verificationTone,
  verificationWarning,
} from "@/lib/verification-client";

test("analysis keys and status labels are explicit", () => {
  expect(createAnalysisIdempotencyKey()).toMatch(/^analysis-/);
  expect(verificationTone("VERIFIED")).toBe("success");
  expect(verificationTone("MISMATCH")).toBe("warning");
  expect(verificationTone("UNVERIFIED")).toBe("info");
  expect(verificationWarning("RECEIPT_REUSED")).toContain("submitted before");
  expect(verificationWarning("UNKNOWN")).toContain("needs review");
});

test("stored-reference request preserves the server endpoint and idempotency key", async () => {
  const request = jest.fn().mockResolvedValue({
    data: {
      analysis_id: "analysis-id",
      transaction_id: "transaction-id",
      status: "PARTIAL",
      verification: { status: "VERIFIED" },
      risk: { status: "UNAVAILABLE" },
      unavailable_stages: [],
      replayed: false,
    },
    meta: { request_id: "request-id" },
  });
  const result = await runStoredReferenceVerification(
    request,
    "/api/v1/transactions/transaction-id/analyses",
    "analysis-key-123",
  );
  expect(request).toHaveBeenCalledWith(
    "/api/v1/transactions/transaction-id/analyses",
    {
      method: "POST",
      headers: { "Idempotency-Key": "analysis-key-123" },
    },
  );
  expect(result.status).toBe("PARTIAL");
  expect(result.verification.status).toBe("VERIFIED");
  expect(result.risk.status).toBe("UNAVAILABLE");
});
