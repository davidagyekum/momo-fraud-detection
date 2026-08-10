import type { Envelope } from "@/types/api";

export type VerificationStatus = "VERIFIED" | "MISMATCH" | "UNVERIFIED";

export type FieldComparison = {
  status: "MATCH" | "MISMATCH" | "NOT_AVAILABLE";
  observed: string | null;
  expected: string | null;
  tolerance: Record<string, unknown>;
};

export type StoredReferenceVerification = {
  status: VerificationStatus;
  label: string;
  basis: "STORED_IMPORTED_RECORD";
  summary: string;
  reference_transaction_id: string | null;
  candidate_method: string;
  verifier_version: string;
  rule_set_version: string | null;
  field_comparisons: Record<string, FieldComparison>;
  matched_field_count: number;
  mismatched_field_count: number;
  warnings: string[];
  disclaimer: string;
};

export type DeterministicImageEvidence = {
  status: "COMPLETED" | "UNAVAILABLE";
  algorithm_version?: string;
  reason_code?: string;
  classification: null;
  tamper_probability: null;
  summary: string;
  triggered_signals?: {
    code: string;
    severity: "INFORMATIONAL" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
    reason: string;
    confidence: number;
  }[];
  warnings?: string[];
  policy: {
    supporting_evidence_only: true;
    single_weak_signal_can_classify_fraud: false;
  };
};

export type PartialAnalysisData = {
  analysis_id: string;
  analysis_run_id: string;
  transaction_id: string;
  status: "PARTIAL";
  current_stage: string;
  risk: {
    status: "UNAVAILABLE";
    class: null;
    score: null;
    reason_code: string;
    summary: string;
  };
  verification: StoredReferenceVerification;
  image_evidence: DeterministicImageEvidence;
  evidence_url: string;
  unavailable_stages: string[];
  replayed: boolean;
};

type JsonRequest = <T>(path: string, init?: RequestInit) => Promise<T>;

export function createAnalysisIdempotencyKey(): string {
  const randomUuid = globalThis.crypto?.randomUUID?.();
  return randomUuid
    ? `analysis-${randomUuid}`
    : `analysis-${Date.now()}-${Math.random().toString(36).slice(2)}-${Math.random().toString(36).slice(2)}`;
}

export async function runStoredReferenceVerification(
  request: JsonRequest,
  endpoint: string,
  idempotencyKey: string,
): Promise<PartialAnalysisData> {
  const response = await request<Envelope<PartialAnalysisData>>(endpoint, {
    method: "POST",
    headers: { "Idempotency-Key": idempotencyKey },
  });
  return response.data;
}

export function verificationTone(
  status: VerificationStatus,
): "success" | "warning" | "info" {
  if (status === "VERIFIED") return "success";
  if (status === "MISMATCH") return "warning";
  return "info";
}

export function verificationWarning(code: string): string {
  const messages: Record<string, string> = {
    NO_STORED_REFERENCE_RECORD:
      "No matching record exists in the currently imported reference data.",
    CANONICAL_REFERENCE_UNAVAILABLE:
      "The confirmed receipt does not contain a usable transaction reference.",
    PROVIDER_FALLBACK_USED:
      "A unique transaction-reference match was used because the provider was generic.",
    REFERENCE_PREVIOUSLY_USED:
      "This stored reference record has been matched to another submitted receipt.",
    RECEIPT_REUSED: "The same receipt image has been submitted before.",
    MULTIPLE_REFERENCE_CANDIDATES:
      "More than one stored record shared this provider and reference, so no record was selected.",
    INSUFFICIENT_REFERENCE_COMPARISON_DATA:
      "The stored record did not contain enough critical fields for a verified result.",
  };
  return messages[code] ?? "Additional verification evidence needs review.";
}
