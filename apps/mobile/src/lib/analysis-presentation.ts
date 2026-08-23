export function readableAnalysisStatus(status: string | null): string {
  if (!status) return "Not available";
  const readable = status.toLowerCase().replaceAll("_", " ");
  return `${readable.charAt(0).toUpperCase()}${readable.slice(1)}`;
}

const providerNames: Record<string, string> = {
  MTN_MOMO: "MTN MoMo",
  TELECEL_CASH: "Telecel Cash",
};

export function readableProviderName(providerCode: string | null): string {
  if (!providerCode) return "Receipt";
  const knownName = providerNames[providerCode];
  if (knownName) return knownName;
  return providerCode
    .toLowerCase()
    .split("_")
    .map((word) => `${word.charAt(0).toUpperCase()}${word.slice(1)}`)
    .join(" ");
}

export function analysisRecordLabel(
  transactionStatus: string,
  ocrReviewStatus: string,
): string {
  if (ocrReviewStatus === "NOT_REQUIRED") return "Screenshot-only analysis";
  return `Transaction: ${readableAnalysisStatus(transactionStatus)}`;
}
