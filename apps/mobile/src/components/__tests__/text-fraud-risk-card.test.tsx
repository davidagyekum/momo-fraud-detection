import { render } from "@testing-library/react-native";

import { TextFraudRiskCard } from "@/components/text-fraud-risk-card";
import type { OCRTextFraudPreview } from "@/lib/ocr-client";

const fraudulent: OCRTextFraudPreview = {
  schema_version: "momo-text-fraud-assessment-v1",
  ruleset_version: "ghana-momo-obvious-scam-rules-v1",
  status: "SUCCESS",
  class: "FRAUDULENT",
  score: 95,
  score_is_probability: false,
  reason_code: "OBVIOUS_SCAM_TEXT_DETECTED",
  reason_codes: ["PIN_OR_OTP_REQUEST"],
  reasons: [
    {
      code: "PIN_OR_OTP_REQUEST",
      title: "Secret code requested",
      summary: "The message asks the user to disclose a secret code.",
      severity: "CRITICAL",
    },
  ],
  evidence_quality: "HIGH",
  limitations: [],
  summary: "Strong scam-language indicators were detected.",
  disclaimer: "Automated text assessment; not live provider verification.",
};

test("shows explicit fraud wording, safe action and a non-probability rule score", async () => {
  const view = await render(<TextFraudRiskCard preview={fraudulent} />);

  expect(
    view.getByLabelText(/Preliminary message-risk preview.*High fraud risk/),
  ).toBeTruthy();
  expect(view.getByLabelText("Status: High fraud risk")).toBeTruthy();
  expect(view.getByText("Rule score 95/100 · not a probability")).toBeTruthy();
  expect(view.getByText(/CRITICAL · Secret code requested/)).toBeTruthy();
  expect(
    view.getByText(/Do not share a PIN, OTP or security code/),
  ).toBeTruthy();
});

test("keeps unavailable evidence distinct from a safe or genuine result", async () => {
  const view = await render(
    <TextFraudRiskCard
      preview={{
        ...fraudulent,
        status: "UNAVAILABLE",
        class: null,
        score: null,
        reasons: [],
        reason_codes: ["OCR_TEXT_UNAVAILABLE"],
        summary: "The screenshot text could not be assessed.",
      }}
    />,
  );

  expect(
    view.getByLabelText("Status: Text assessment unavailable"),
  ).toBeTruthy();
  expect(view.queryByText(/safe|genuine/i)).toBeNull();
  expect(view.queryByText(/Rule score/)).toBeNull();
});
