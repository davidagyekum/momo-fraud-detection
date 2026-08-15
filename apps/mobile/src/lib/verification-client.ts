export type VerificationStatus = "VERIFIED" | "MISMATCH" | "UNVERIFIED";

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
