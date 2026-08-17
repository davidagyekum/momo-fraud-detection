import {
  AnalysisContractError,
  getAnalysis,
  pollAnalysis,
  startAnalysis,
} from "@/lib/analysis-client";

const risk = {
  status: "PARTIAL",
  band: "inconclusive",
  class: null,
  score: null,
  summary: "Evidence is insufficient.",
  reasons: [],
  missing_signals: ["IMAGE_MODEL_NOT_ACTIVE"],
  limitations: ["No image model."],
  policy_version: "risk-policy-v1",
  disclaimer:
    "This is an automated risk assessment, not a final legal determination.",
} as const;

const verification = {
  status: "VERIFIED",
  label: "Verified",
  basis: "STORED_IMPORTED_RECORD",
  summary: "Stored fields matched.",
  reference_transaction_id: null,
  candidate_method: "PROVIDER_AND_REFERENCE",
  verifier_version: "verifier-v1",
  rule_set_version: "rules-v1",
  field_comparisons: {},
  matched_field_count: 2,
  mismatched_field_count: 0,
  warnings: [],
  disclaimer: "Not live provider confirmation.",
} as const;

function envelope(status: "QUEUED" | "PROCESSING" | "PARTIAL" = "PARTIAL") {
  return {
    data: {
      id: "analysis-id",
      transaction_id: "transaction-id",
      status,
      risk,
      verification,
      evidence_summary: {
        deterministic_image: { status: "COMPLETED", reason_code: null },
        image_model: {
          status: "UNAVAILABLE",
          reason_code: null,
          reason_codes: ["IMAGE_MODEL_NOT_ACTIVE"],
          model_version: null,
        },
        structured_model: {
          status: "UNAVAILABLE",
          reason_code: null,
          reason_codes: ["STRUCTURED_CONTEXT_UNAVAILABLE"],
          model_version: null,
        },
        text_fraud: {
          status: "SUCCESS",
          class: null,
          policy_score: null,
          score_is_probability: false,
          reason_codes: [],
          evidence_quality: "HIGH",
          ruleset_version: "ghana-momo-obvious-scam-rules-v1",
          limitations: ["ABSENCE_OF_RULE_MATCH_IS_NOT_PROOF_OF_GENUINENESS"],
        },
        automated_evidence_immutable: true,
      },
      ocr_review: {
        confirmed_field_count: 10,
        correction_count: 0,
        schema_version: "ocr-fields-v1",
      },
      versions: {
        policy_version: "risk-policy-v1",
        policy_sha256: "a".repeat(64),
        rule_set_version: "rules-v1",
        ocr_pipeline_version: "ocr-v1",
        ocr_engine_version: "5.3.0",
        image_forensics_version: "forensics-v1",
        image_model_version: null,
        structured_model_version: null,
        text_fraud_schema_version: "momo-text-fraud-assessment-v1",
        text_fraud_ruleset_version: "ghana-momo-obvious-scam-rules-v1",
      },
      progress: {
        current_stage: "FINALIZE",
        completed_stage_count: 8,
        total_stage_count: 8,
        stages: [],
      },
      evidence_url: "/api/v1/analyses/analysis-id/evidence",
      created_at: "2026-08-15T12:00:00Z",
      completed_at: "2026-08-15T12:00:01Z",
    },
    meta: { request_id: "request-id" },
  };
}

test("starts analysis with an encoded path and idempotency key", async () => {
  const request = jest.fn().mockResolvedValue({
    data: {
      analysis_run_id: "analysis-id",
      transaction_id: "transaction/id",
      status: "PARTIAL",
      current_stage: "FINALIZE",
      poll_url: "/api/v1/analyses/analysis-id",
      replayed: false,
    },
    meta: { request_id: "request-id" },
  });

  const started = await startAnalysis(
    request,
    "transaction/id",
    "analysis-key-123",
  );

  expect(started.analysis_run_id).toBe("analysis-id");
  expect(request).toHaveBeenCalledWith(
    "/api/v1/transactions/transaction%2Fid/analyses",
    { method: "POST", headers: { "Idempotency-Key": "analysis-key-123" } },
  );
});

test("rejects an incompatible risk enum", async () => {
  const bad = envelope();
  bad.data.risk = { ...risk, band: "safe" } as never;
  const request = jest.fn().mockResolvedValue(bad);

  await expect(getAnalysis(request, "analysis-id")).rejects.toThrow(
    "Analysis response is incompatible",
  );
});

test("polls with capped delays until a terminal partial result", async () => {
  const request = jest
    .fn()
    .mockResolvedValueOnce(envelope("QUEUED"))
    .mockResolvedValueOnce(envelope("PROCESSING"))
    .mockResolvedValueOnce(envelope("PARTIAL"));
  const wait = jest.fn().mockResolvedValue(undefined);

  const result = await pollAnalysis(request, "analysis/id", {
    maxAttempts: 4,
    wait,
  });

  expect(result.status).toBe("PARTIAL");
  expect(wait).toHaveBeenNthCalledWith(1, 500);
  expect(wait).toHaveBeenNthCalledWith(2, 1000);
  expect(request).toHaveBeenCalledWith("/api/v1/analyses/analysis%2Fid");
});

test("polling supports cancellation and a bounded timeout", async () => {
  const controller = new AbortController();
  controller.abort();
  await expect(
    pollAnalysis(jest.fn(), "analysis-id", { signal: controller.signal }),
  ).rejects.toMatchObject({ name: "AbortError" });

  const request = jest.fn().mockResolvedValue(envelope("PROCESSING"));
  await expect(
    pollAnalysis(request, "analysis-id", {
      maxAttempts: 2,
      wait: async () => undefined,
    }),
  ).rejects.toBeInstanceOf(AnalysisContractError);
  expect(request).toHaveBeenCalledTimes(2);
});
