import { act, fireEvent, render } from "@testing-library/react-native";

import { TextFraudRiskCard } from "@/components/text-fraud-risk-card";
import type { OCRTextFraudPreview } from "@/lib/ocr-client";

const fraudulent: OCRTextFraudPreview = {
  schema_version: "momo-hybrid-text-risk-assessment-v1",
  ruleset_version: "ghana-momo-hybrid-text-risk-v3",
  status: "SUCCESS",
  class: "FRAUDULENT",
  score: 95,
  score_is_probability: false,
  reason_code: "OBVIOUS_SCAM_TEXT_DETECTED",
  reason_codes: [
    "NUMERIC_SENDER_TRANSACTION_CLAIM",
    "GENUINE_TEMPLATE_ANOMALY",
    "FINANCIAL_TERM_SPELLING_ANOMALY",
    "MALFORMED_FINANCIAL_FORMAT",
  ],
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

test("keeps compact evidence visible and collapses technical rule detail", async () => {
  const view = await render(<TextFraudRiskCard preview={fraudulent} />);

  expect(
    view.getByLabelText(/Preliminary message-risk preview.*High fraud risk/),
  ).toBeTruthy();
  expect(view.getByLabelText("Status: High fraud risk")).toBeTruthy();
  expect(
    view.queryByText("Policy score 95/100 — not a probability"),
  ).toBeNull();
  expect(view.queryByText(/CRITICAL · Secret code requested/)).toBeNull();
  expect(
    view.getByText(/Do not act on this message.*Do not send money/s),
  ).toBeTruthy();
  expect(
    view.getByText("Likely counterfeit transaction notification"),
  ).toBeTruthy();
  expect(view.getByText("Numeric sender")).toBeTruthy();
  expect(view.getByText("Strong anomaly")).toBeTruthy();
  expect(view.getByText("Multiple financial misspellings")).toBeTruthy();
  expect(view.getByText("Multiple malformed fields")).toBeTruthy();

  const whyButton = view.getByRole("button", { name: "Why this result?" });
  expect(whyButton.props.accessibilityState).toEqual(
    expect.objectContaining({ expanded: false }),
  );
  await act(async () => fireEvent.press(whyButton));

  expect(
    view.getByText("Policy score 95/100 — not a probability"),
  ).toBeTruthy();
  expect(view.getByText(/CRITICAL · Secret code requested/)).toBeTruthy();
  expect(
    view.getByText(
      "Automated text assessment; not live provider verification.",
    ),
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

  expect(view.getByLabelText("Status: Assessment unavailable")).toBeTruthy();
  expect(view.queryByText(/safe|genuine/i)).toBeNull();
  expect(view.queryByText(/Policy score/)).toBeNull();
});

test("labels a null successful assessment as inconclusive and explicitly not safe", async () => {
  const view = await render(
    <TextFraudRiskCard
      preview={{
        ...fraudulent,
        class: null,
        score: null,
        reasons: [],
        reason_codes: [],
        summary: "No decisive rule matched.",
      }}
    />,
  );

  expect(
    view.getByLabelText(
      "Status: Inconclusive — no reliable fraud classification",
    ),
  ).toBeTruthy();
  expect(
    view.getByText(
      "The available evidence did not support a decisive result. This is not a genuine or safe verdict.",
    ),
  ).toBeTruthy();
});
