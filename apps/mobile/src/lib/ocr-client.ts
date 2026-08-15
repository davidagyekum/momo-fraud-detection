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
    currency: data.fields.currency?.value ?? "GHS",
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

export function validateOCRConfirmation(
  review: OCRReviewData,
  confirmed: OCRConfirmedFields,
  reasons: Partial<Record<OCRFieldName, string>>,
): Partial<Record<OCRFieldName, string>> {
  const errors: Partial<Record<OCRFieldName, string>> = {};
  const required: OCRFieldName[] = [
    "provider_code",
    "transaction_reference",
    "amount",
    "currency",
    "occurred_at",
    "status_text",
  ];
  for (const name of required) {
    if (!confirmed[name].trim()) errors[name] = "This field is required.";
  }
  if (confirmed.amount && !/^\d+(\.\d{1,2})?$/.test(confirmed.amount)) {
    errors.amount = "Use a non-negative amount such as 125.00.";
  }
  if (confirmed.currency && !/^[A-Za-z]{3}$/.test(confirmed.currency)) {
    errors.currency = "Use a three-letter currency code such as GHS.";
  }
  for (const name of changedOCRFields(review, confirmed)) {
    const reason = reasons[name]?.trim() ?? "";
    if (reason.length < 5) {
      errors[name] = "Add a short reason for this correction.";
    }
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
  reasons: Partial<Record<OCRFieldName, string>>,
  confirmationKey: string,
): Promise<OCRConfirmationData> {
  const correctionReasons = Object.fromEntries(
    changedOCRFields(review, confirmed).map((name) => [
      name,
      reasons[name]?.trim(),
    ]),
  );
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
