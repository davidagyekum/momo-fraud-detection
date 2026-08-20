import { render } from "@testing-library/react-native";

import { OCRAnalysisChoices } from "@/components/ocr-analysis-choices";
import type { OCRTextFraudPreview } from "@/lib/ocr-client";

const preview: OCRTextFraudPreview = {
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

test("makes screenshot persistence primary and reference comparison optional", async () => {
  const onSave = jest.fn();
  const onToggleComparison = jest.fn();
  const view = await render(
    <OCRAnalysisChoices
      preview={preview}
      online
      saving={false}
      saveError={null}
      comparisonExpanded={false}
      onSave={onSave}
      onToggleComparison={onToggleComparison}
    />,
  );

  expect(
    view.getByRole("button", { name: "Save screenshot risk result" }),
  ).toBeTruthy();
  const compare = view.getByRole("button", {
    name: "Compare with a transaction record (optional)",
  });

  expect(view.getByLabelText("Status: High fraud risk")).toBeTruthy();
  expect(view.queryByText(/required to continue/i)).toBeNull();
  expect(compare.props.accessibilityState).toMatchObject({ expanded: false });

  expect(onSave).not.toHaveBeenCalled();
  expect(onToggleComparison).not.toHaveBeenCalled();
});

test("announces save failures and the expanded comparison state", async () => {
  const view = await render(
    <OCRAnalysisChoices
      preview={preview}
      online={false}
      saving={false}
      saveError="Reconnect and try again."
      comparisonExpanded
      onSave={jest.fn()}
      onToggleComparison={jest.fn()}
    />,
  );

  expect(view.getByText("Risk result not saved")).toBeTruthy();
  expect(view.getByText("Reconnect and try again.")).toBeTruthy();
  expect(
    view.getByRole("button", { name: "Save screenshot risk result" }).props
      .accessibilityState,
  ).toMatchObject({ disabled: true });
  expect(
    view.getByRole("button", { name: "Hide optional transaction comparison" })
      .props.accessibilityState,
  ).toMatchObject({ expanded: true });
});
