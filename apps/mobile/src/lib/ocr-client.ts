import { ApiError, type JsonRequest } from "@/lib/api";
import type { Envelope } from "@/types/api";

export const OCR_FIELD_NAMES = [
  "provider_code",
  "transaction_reference",
  "amount",
  "currency",
  "sender_name",
  "sender_phone",
  "receiver_name",
  "receiver_phone",
  "occurred_at",
  "status_text",
] as const;

export type OCRFieldName = (typeof OCR_FIELD_NAMES)[number];
export type OCRConfirmedFields = Record<OCRFieldName, string>;

export const REQUIRED_OCR_FIELD_NAMES: readonly OCRFieldName[] = [
  "provider_code",
  "transaction_reference",
  "amount",
  "currency",
  "occurred_at",
  "status_text",
];

export type OCRField = {
  raw_value: string | null;
  value: string | null;
  confidence: number;
  valid: boolean;
  requires_review: boolean;
  source_token_ids: number[];
  warnings: string[];
  currency?: string | null;
  masked?: string | null;
};

export type OCRTextFraudReason = {
  code: string;
  title: string;
  summary: string;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
};

export type OCRTextFraudPreview = {
  schema_version: string;
  ruleset_version: string;
  status: "SUCCESS" | "UNAVAILABLE";
  class: "SUSPICIOUS" | "FRAUDULENT" | null;
  score: number | null;
  score_is_probability: false;
  reason_code: string;
  reason_codes: string[];
  reasons: OCRTextFraudReason[];
  evidence_quality: "HIGH" | "MEDIUM" | "LOW" | "UNAVAILABLE";
  limitations: string[];
  summary: string;
  disclaimer: string;
};

export type OCRReviewData = {
  transaction_id: string;
  status: "OCR_READY" | "OCR_PARTIAL";
  ocr_result_id: string;
  provider: {
    value: string;
    confidence: number;
    requires_review: boolean;
    warnings: string[];
  };
  fraud_preview: OCRTextFraudPreview;
  fields: Partial<Record<Exclude<OCRFieldName, "provider_code">, OCRField>>;
  warnings: string[];
  raw_text: string;
  selected_variant: string;
  pipeline_version: string;
  engine_version: string;
  preview_url: string;
  confirmation_endpoint: string;
  replayed: boolean;
};

export type OCRConfirmationData = {
  confirmation_id: string;
  ocr_result_id: string;
  transaction_id: string;
  status: "OCR_REVIEWED";
  schema_version: string;
  corrected_fields: OCRFieldName[];
  replayed: boolean;
  next_action: { type: "RUN_ANALYSIS"; endpoint: string };
};

export function createOCRIdempotencyKey(prefix: "run" | "confirm"): string {
  const randomUuid = globalThis.crypto?.randomUUID?.();
  return randomUuid
    ? `ocr-${prefix}-${randomUuid}`
    : `ocr-${prefix}-${Date.now()}-${Math.random().toString(36).slice(2)}-${Math.random().toString(36).slice(2)}`;
}

export function initialOCRFields(data: OCRReviewData): OCRConfirmedFields {
  return {
    provider_code: data.provider.value ?? "GENERIC_MOMO",
    transaction_reference: data.fields.transaction_reference?.value ?? "",
    amount: data.fields.amount?.value ?? "",
    currency: data.fields.currency?.value ?? "",
    sender_name: data.fields.sender_name?.value ?? "",
    sender_phone: data.fields.sender_phone?.value ?? "",
    receiver_name: data.fields.receiver_name?.value ?? "",
    receiver_phone: data.fields.receiver_phone?.value ?? "",
    occurred_at: data.fields.occurred_at?.value ?? "",
    status_text: data.fields.status_text?.value ?? "",
  };
}

export function changedOCRFields(
  review: OCRReviewData,
  confirmed: OCRConfirmedFields,
): OCRFieldName[] {
  const original = initialOCRFields(review);
  return OCR_FIELD_NAMES.filter(
    (name) => confirmed[name].trim() !== original[name].trim(),
  );
}

function originalOCRValue(review: OCRReviewData, name: OCRFieldName): string {
  if (name === "provider_code") return review.provider.value ?? "";
  return String(review.fields[name]?.value ?? "");
}

export function automaticOCRCorrectionReasons(
  review: OCRReviewData,
  confirmed: OCRConfirmedFields,
): Partial<Record<OCRFieldName, string>> {
  return Object.fromEntries(
    changedOCRFields(review, confirmed).map((name) => [
      name,
      originalOCRValue(review, name)
        ? "Corrected after comparing the OCR value with the private image."
        : "Entered manually because OCR did not detect this value.",
    ]),
  );
}

export function validateOCRConfirmation(
  confirmed: OCRConfirmedFields,
): Partial<Record<OCRFieldName, string>> {
  const errors: Partial<Record<OCRFieldName, string>> = {};
  for (const name of REQUIRED_OCR_FIELD_NAMES) {
    if (!confirmed[name].trim()) {
      errors[name] = "Required for the stored-reference comparison.";
    }
  }
  if (
    confirmed.transaction_reference &&
    !/^[A-Za-z0-9][A-Za-z0-9._/-]{5,49}$/.test(
      confirmed.transaction_reference.trim(),
    )
  ) {
    errors.transaction_reference =
      "Use the full reference shown in the image (6–50 letters, numbers or . _ / -).";
  }
  if (confirmed.amount && !/^\d+(\.\d{1,2})?$/.test(confirmed.amount)) {
    errors.amount = "Use a non-negative amount such as 125.00.";
  }
  if (confirmed.currency && !/^[A-Za-z]{3}$/.test(confirmed.currency)) {
    errors.currency = "Use a three-letter currency code such as GHS.";
  }
  for (const name of ["sender_name", "receiver_name"] as const) {
    const value = confirmed[name].trim();
    if (value && (value.length > 150 || !/[A-Za-z]/.test(value))) {
      errors[name] =
        "Enter a name containing letters, or leave this optional field blank.";
    }
  }
  for (const name of ["sender_phone", "receiver_phone"] as const) {
    const digits = confirmed[name].replace(/\D/g, "");
    if (
      digits &&
      !(
        (digits.startsWith("233") && digits.length === 12) ||
        (digits.startsWith("0") && digits.length === 10) ||
        (digits.length === 9 && /^[25]/.test(digits))
      )
    ) {
      errors[name] =
        "Use a Ghanaian number such as 0240000000, or leave this optional field blank.";
    }
  }
  if (
    confirmed.status_text &&
    !/^[A-Za-z][A-Za-z _-]{1,49}$/.test(confirmed.status_text.trim())
  ) {
    errors.status_text = "Enter the transaction status shown in the image.";
  }
  return errors;
}

export async function fetchOrRunOCR(
  request: JsonRequest,
  transactionId: string,
  runKey: string,
): Promise<OCRReviewData> {
  try {
    const review = await request<Envelope<OCRReviewData>>(
      `/api/v1/transactions/${transactionId}/ocr-review`,
    );
    return review.data;
  } catch (error) {
    if (!(error instanceof ApiError) || error.code !== "OCR_NOT_RUN")
      throw error;
  }
  const run = await request<Envelope<OCRReviewData>>(
    `/api/v1/transactions/${transactionId}/ocr`,
    {
      method: "POST",
      headers: { "Idempotency-Key": runKey },
    },
  );
  return run.data;
}

export async function confirmOCR(
  request: JsonRequest,
  transactionId: string,
  review: OCRReviewData,
  confirmed: OCRConfirmedFields,
  confirmationKey: string,
): Promise<OCRConfirmationData> {
  const correctionReasons = automaticOCRCorrectionReasons(review, confirmed);
  const response = await request<Envelope<OCRConfirmationData>>(
    `/api/v1/transactions/${transactionId}/ocr-confirmations`,
    {
      method: "POST",
      headers: { "Idempotency-Key": confirmationKey },
      body: JSON.stringify({
        ocr_result_id: review.ocr_result_id,
        fields: confirmed,
        correction_reasons: correctionReasons,
      }),
    },
  );
  return response.data;
}

export function confidenceLabel(field: OCRField | undefined): string {
  if (!field?.value || !field.valid)
    return "Not detected — enter this manually";
  if (field.requires_review) return "Needs checking against the receipt";
  return "Looks clear — still check before confirming";
}
