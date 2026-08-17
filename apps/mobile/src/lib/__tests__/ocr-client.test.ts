import { ApiError } from "@/lib/api";
import {
  changedOCRFields,
  confidenceLabel,
  confirmOCR,
  createOCRIdempotencyKey,
  fetchOrRunOCR,
  initialOCRFields,
  type OCRReviewData,
  validateOCRConfirmation,
} from "@/lib/ocr-client";

function review(): OCRReviewData {
  const field = (value: string | null, requiresReview = false) => ({
    raw_value: value,
    value,
    confidence: requiresReview ? 0.5 : 0.9,
    valid: value !== null,
    requires_review: requiresReview,
    source_token_ids: [1],
    warnings: [],
  });
  return {
    transaction_id: "transaction-id",
    status: "OCR_READY",
    ocr_result_id: "ocr-id",
    provider: {
      value: "MTN_MOMO",
      confidence: 0.9,
      requires_review: false,
      warnings: [],
    },
    fraud_preview: {
      schema_version: "momo-text-fraud-assessment-v1",
      ruleset_version: "ghana-momo-obvious-scam-rules-v1",
      status: "SUCCESS",
      class: null,
      score: null,
      score_is_probability: false,
      reason_code: "NO_DECISIVE_TEXT_FRAUD_SIGNAL",
      reason_codes: [],
      reasons: [],
      evidence_quality: "HIGH",
      limitations: ["ABSENCE_OF_RULE_MATCH_IS_NOT_PROOF_OF_GENUINENESS"],
      summary: "No decisive scam-language rule was triggered.",
      disclaimer: "Not live provider verification.",
    },
    fields: {
      transaction_reference: field("ABC123456"),
      amount: { ...field("125.00"), currency: "GHS" },
      currency: field("GHS"),
      sender_name: field("DEMO SENDER"),
      sender_phone: field("+233240000002"),
      receiver_name: field("DEMO RECEIVER"),
      receiver_phone: field("+233240000001"),
      occurred_at: field("2026-08-08T14:30:00Z"),
      status_text: field("SUCCESSFUL"),
    },
    warnings: [],
    raw_text: "controlled",
    selected_variant: "GRAY_CLAHE",
    pipeline_version: "ocr-pipeline-v1",
    engine_version: "5.3.0",
    preview_url: "/preview",
    confirmation_endpoint: "/confirm",
    replayed: false,
  };
}

test("creates scoped OCR idempotency keys", () => {
  expect(createOCRIdempotencyKey("run")).toMatch(/^ocr-run-/);
  expect(createOCRIdempotencyKey("confirm")).toMatch(/^ocr-confirm-/);
});

test("maps extraction to editable canonical fields", () => {
  expect(initialOCRFields(review())).toEqual(
    expect.objectContaining({
      provider_code: "MTN_MOMO",
      transaction_reference: "ABC123456",
      amount: "125.00",
      receiver_phone: "+233240000001",
    }),
  );
});

test("requires a reason for every changed field", () => {
  const source = review();
  const fields = { ...initialOCRFields(source), amount: "130.00" };
  expect(changedOCRFields(source, fields)).toEqual(["amount"]);
  expect(validateOCRConfirmation(source, fields, {})).toEqual({
    amount: "Add a short reason for this correction.",
  });
  expect(
    validateOCRConfirmation(source, fields, { amount: "Checked receipt" }),
  ).toEqual({});
});

test("validates required and formatted confirmation fields", () => {
  const source = review();
  const fields = {
    ...initialOCRFields(source),
    transaction_reference: "",
    amount: "not money",
    currency: "GH",
  };
  const errors = validateOCRConfirmation(source, fields, {
    transaction_reference: "Not visible",
    amount: "Checked receipt",
    currency: "Checked receipt",
  });
  expect(errors.transaction_reference).toBe("This field is required.");
  expect(errors.amount).toContain("non-negative amount");
  expect(errors.currency).toContain("three-letter");
});

test("uses existing review without starting another run", async () => {
  const data = review();
  const request = jest.fn().mockResolvedValue({ data, meta: {} });
  await expect(
    fetchOrRunOCR(request, "transaction-id", "run-key-123"),
  ).resolves.toBe(data);
  expect(request).toHaveBeenCalledTimes(1);
  expect(request).toHaveBeenCalledWith(
    "/api/v1/transactions/transaction-id/ocr-review",
  );
});

test("runs OCR only after an explicit not-run response", async () => {
  const data = review();
  const request = jest
    .fn()
    .mockRejectedValueOnce(new ApiError("Run OCR", 409, "OCR_NOT_RUN"))
    .mockResolvedValueOnce({ data, meta: {} });
  await expect(
    fetchOrRunOCR(request, "transaction-id", "run-key-123"),
  ).resolves.toBe(data);
  expect(request).toHaveBeenLastCalledWith(
    "/api/v1/transactions/transaction-id/ocr",
    {
      method: "POST",
      headers: { "Idempotency-Key": "run-key-123" },
    },
  );
});

test("does not hide unrelated review failures", async () => {
  const request = jest
    .fn()
    .mockRejectedValue(new ApiError("Denied", 404, "NOT_FOUND"));
  await expect(
    fetchOrRunOCR(request, "transaction-id", "run-key-123"),
  ).rejects.toMatchObject({
    code: "NOT_FOUND",
  });
  expect(request).toHaveBeenCalledTimes(1);
});

test("submits only documented correction reasons", async () => {
  const source = review();
  const fields = { ...initialOCRFields(source), amount: "130.00" };
  const request = jest.fn().mockResolvedValue({
    data: { status: "OCR_REVIEWED", corrected_fields: ["amount"] },
    meta: {},
  });
  await confirmOCR(
    request,
    "transaction-id",
    source,
    fields,
    { amount: "Checked receipt", sender_name: "Unused reason" },
    "confirm-key-123",
  );
  expect(request).toHaveBeenCalledWith(
    "/api/v1/transactions/transaction-id/ocr-confirmations",
    expect.objectContaining({
      method: "POST",
      headers: { "Idempotency-Key": "confirm-key-123" },
      body: expect.stringContaining('"amount":"Checked receipt"'),
    }),
  );
  expect(request.mock.calls[0]?.[1]?.body).not.toContain("Unused reason");
});

test("turns numeric confidence into understandable guidance", () => {
  expect(confidenceLabel(review().fields.amount)).toContain("Looks clear");
  expect(
    confidenceLabel({
      ...review().fields.amount!,
      requires_review: true,
    }),
  ).toContain("Needs checking");
  expect(confidenceLabel(undefined)).toContain("Not detected");
});
