import {
  evidenceRowsForPreview,
  highRiskSummaryFromReasonCodes,
  riskPresentation,
  riskTone,
} from "@/lib/fraud-risk-presentation";
import type { OCRTextFraudPreview } from "@/lib/ocr-client";

const basePreview: OCRTextFraudPreview = {
  schema_version: "momo-hybrid-text-risk-assessment-v1",
  ruleset_version: "ghana-momo-hybrid-text-risk-v3",
  status: "SUCCESS",
  class: null,
  score: null,
  score_is_probability: false,
  reason_code: "NO_DECISIVE_TEXT_FRAUD_SIGNAL",
  reason_codes: [],
  reasons: [],
  evidence_quality: "HIGH",
  limitations: ["ABSENCE_OF_RULE_MATCH_IS_NOT_PROOF_OF_GENUINENESS"],
  summary: "No decisive text signal was detected.",
  disclaimer: "Automated assessment; not live provider verification.",
};

test("presents null success as explicitly inconclusive rather than safe", () => {
  expect(riskPresentation(basePreview)).toEqual(
    expect.objectContaining({
      title: "Inconclusive. No reliable fraud classification",
      subtitle:
        "The available evidence did not support a decisive result. This is not a genuine or safe verdict.",
      saveLabel: "Save inconclusive assessment",
    }),
  );
});

test("presents fraudulent evidence with immediate protective guidance", () => {
  expect(
    riskPresentation({
      ...basePreview,
      class: "FRAUDULENT",
      score: 95,
      reason_codes: [
        "NUMERIC_SENDER_TRANSACTION_CLAIM",
        "GENUINE_TEMPLATE_ANOMALY",
      ],
    }),
  ).toEqual(
    expect.objectContaining({
      title: "High fraud risk",
      subtitle: "Likely counterfeit transaction notification",
      guidance: expect.stringContaining("Do not act on this message"),
      saveLabel: "Save screenshot risk result",
    }),
  );
});

test("uses reason-aware high-risk copy in the OCR preview", () => {
  expect(highRiskSummaryFromReasonCodes(["PIN_OR_OTP_REQUEST"])).toBe(
    "Strong scam indicators detected",
  );
  expect(highRiskSummaryFromReasonCodes(["STRUCTURED_MODEL_HIGH_RISK"])).toBe(
    "Multiple high-risk indicators detected",
  );
  expect(
    highRiskSummaryFromReasonCodes([
      "PIN_OR_OTP_REQUEST",
      "NUMERIC_SENDER_TRANSACTION_CLAIM",
      "GENUINE_TEMPLATE_ANOMALY",
    ]),
  ).toBe("Likely counterfeit transaction notification");
});

test.each([
  ["low", "success"],
  ["low_risk", "success"],
  ["medium", "warning"],
  ["medium_risk", "warning"],
  ["high", "error"],
  ["high_risk", "error"],
  ["inconclusive", "info"],
] as const)("maps %s to the shared %s risk tone", (risk, tone) => {
  expect(riskTone(risk)).toBe(tone);
});

test("maps fixed evidence codes once without exposing matched OCR values", () => {
  const rows = evidenceRowsForPreview({
    ...basePreview,
    class: "FRAUDULENT",
    reason_codes: [
      "NUMERIC_SENDER_TRANSACTION_CLAIM",
      "GENUINE_TEMPLATE_ANOMALY",
      "FINANCIAL_TERM_SPELLING_ANOMALY",
      "MALFORMED_FINANCIAL_FORMAT",
      "NUMERIC_SENDER_TRANSACTION_CLAIM",
    ],
    evidence_quality: "LOW",
  });

  expect(rows).toEqual([
    { label: "Sender", value: "Numeric sender" },
    { label: "MTN format", value: "Strong anomaly" },
    { label: "Language", value: "Multiple financial misspellings" },
    { label: "Formatting", value: "Multiple malformed fields" },
    { label: "OCR quality", value: "Limited" },
  ]);
  expect(JSON.stringify(rows)).not.toMatch(/233|matched text|candidate/i);
});

test("keeps unavailable distinct from inconclusive", () => {
  expect(
    riskPresentation({
      ...basePreview,
      status: "UNAVAILABLE",
      evidence_quality: "UNAVAILABLE",
    }),
  ).toEqual(
    expect.objectContaining({
      title: "Assessment unavailable",
      saveLabel: "Save unavailable assessment",
    }),
  );
});
