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
      image_evidence: {
        status: "COMPLETED",
        classification: null,
        tamper_probability: null,
        summary: "Supporting evidence recorded.",
        policy: {
          supporting_evidence_only: true,
          single_weak_signal_can_classify_fraud: false,
        },
      },
      evidence_url: "/api/v1/analyses/analysis-id/evidence",
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
  expect(result.image_evidence.classification).toBeNull();
  expect(result.image_evidence.policy.supporting_evidence_only).toBe(true);
  expect(result.risk.status).toBe("UNAVAILABLE");
});
