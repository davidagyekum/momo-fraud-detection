import type { OCRTextFraudPreview } from "@/lib/ocr-client";

export type RiskPresentation = {
  title: string;
  subtitle: string;
  guidance: string | null;
  tone: "error" | "info" | "warning";
  saveLabel: string;
};

export type RiskTone = "error" | "info" | "success" | "warning";

const ACTIVE_SCAM_REASON_CODES = new Set([
  "PIN_OR_OTP_REQUEST",
  "WRONG_TRANSFER_REFUND_LURE",
  "ACCOUNT_BLOCK_THREAT_WITH_ACTION",
  "PAY_TO_UNLOCK_OR_RELEASE",
  "SUSPICIOUS_LINK_ACCOUNT_ACTION",
  "UNVERIFIED_CONTACT_REDIRECT",
  "PRIZE_OR_BONUS_LURE",
  "URGENCY_PRESSURE",
  "UNOFFICIAL_SENDER_CONTEXT",
]);

export function highRiskSummaryFromReasonCodes(
  reasonCodes: readonly string[],
): string {
  const codes = new Set(reasonCodes);
  if (
    codes.has("NUMERIC_SENDER_TRANSACTION_CLAIM") &&
    codes.has("GENUINE_TEMPLATE_ANOMALY")
  ) {
    return "Likely counterfeit transaction notification";
  }
  if (reasonCodes.some((code) => ACTIVE_SCAM_REASON_CODES.has(code))) {
    return "Strong scam indicators detected";
  }
  return "Multiple high-risk indicators detected";
}

export function riskTone(risk: string | null | undefined): RiskTone {
  const normalized = risk?.toLowerCase().replace(/_risk$/, "");
  if (normalized === "low") return "success";
  if (normalized === "medium") return "warning";
  if (normalized === "high") return "error";
  return "info";
}

export type EvidenceRow = { label: string; value: string };

const EVIDENCE_BY_REASON_CODE: Readonly<
  Record<string, Omit<EvidenceRow, never>>
> = {
  NUMERIC_SENDER_TRANSACTION_CLAIM: {
    label: "Sender",
    value: "Numeric sender",
  },
  GENUINE_TEMPLATE_ANOMALY: {
    label: "MTN format",
    value: "Strong anomaly",
  },
  FINANCIAL_TERM_SPELLING_ANOMALY: {
    label: "Language",
    value: "Multiple financial misspellings",
  },
  MALFORMED_FINANCIAL_FORMAT: {
    label: "Formatting",
    value: "Multiple malformed fields",
  },
};

export function riskPresentation(
  preview: OCRTextFraudPreview,
): RiskPresentation {
  if (preview.class === "FRAUDULENT") {
    return {
      title: "High fraud risk",
      subtitle: highRiskSummaryFromReasonCodes(preview.reason_codes),
      guidance:
        "Do not act on this message. Do not send money or disclose a PIN, OTP or security code. Verify through an official provider channel.",
      tone: "error",
      saveLabel: "Save screenshot risk result",
    };
  }
  if (preview.class === "SUSPICIOUS") {
    return {
      title: "Suspicious message",
      subtitle:
        "One strong warning sign was detected. Pause before acting and verify through an official provider channel.",
      guidance:
        "Pause before acting. Verify through an official provider channel or a contact you already trust.",
      tone: "warning",
      saveLabel: "Save screenshot risk result",
    };
  }
  if (preview.status === "UNAVAILABLE") {
    return {
      title: "Assessment unavailable",
      subtitle:
        "The screenshot text could not be read well enough for a message-risk assessment. Try a clearer image or verify through an official provider channel.",
      guidance: null,
      tone: "info",
      saveLabel: "Save unavailable assessment",
    };
  }
  return {
    title: "Inconclusive. No reliable fraud classification",
    subtitle:
      "The available evidence did not support a decisive result. This is not a genuine or safe verdict.",
    guidance: null,
    tone: "info",
    saveLabel: "Save inconclusive assessment",
  };
}

function ocrQualityValue(
  quality: OCRTextFraudPreview["evidence_quality"],
): string {
  if (quality === "HIGH") return "Readable";
  if (quality === "UNAVAILABLE") return "Unavailable";
  return "Limited";
}

export function evidenceRowsForPreview(
  preview: OCRTextFraudPreview,
): EvidenceRow[] {
  const seenLabels = new Set<string>();
  const rows: EvidenceRow[] = [];

  for (const code of preview.reason_codes) {
    const row = EVIDENCE_BY_REASON_CODE[code];
    if (!row || seenLabels.has(row.label)) continue;
    rows.push(row);
    seenLabels.add(row.label);
  }

  rows.push({
    label: "OCR quality",
    value: ocrQualityValue(preview.evidence_quality),
  });
  return rows;
}
