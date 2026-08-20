import { render } from "@testing-library/react-native";

import {
  AnalysisDetailsView,
  AnalysisResultView,
} from "@/components/analysis-result";
import type { AnalysisResult } from "@/types/analysis";

const partialResult = {
  id: "run-1",
  transaction_id: "tx-1",
  analysis_mode: "combined",
  ocr_result_id: "ocr-result-id",
  ocr_confirmation_id: "confirmation-id",
  status: "PARTIAL",
  risk: {
    status: "INCONCLUSIVE",
    band: "inconclusive",
    conclusion_status: "INCONCLUSIVE",
    component_status: "DEGRADED",
    class: null,
    score: null,
    summary: "Insufficient independent signals for a fraud classification.",
    reasons: [
      {
        code: "MISSING_IMAGE_MODEL",
        title: "Image model unavailable",
        severity: "MEDIUM",
      },
    ],
    missing_signals: ["image_model"],
    limitations: ["No promoted image classifier is available."],
    policy_version: "risk-policy-v1",
    disclaimer:
      "This is an automated risk assessment, not a final legal determination.",
  },
  verification: {
    status: "MISMATCH",
    label: "Mismatch found",
    basis: "STORED_IMPORTED_RECORD",
    summary: "Confirmed receipt fields differ from the stored reference.",
    reference_transaction_id: null,
    candidate_method: "reference",
    verifier_version: "verifier-v1",
    rule_set_version: "demo-1",
    field_comparisons: {},
    matched_field_count: 2,
    mismatched_field_count: 1,
    warnings: [],
    disclaimer: "This is not live MNO verification.",
  },
  evidence_summary: {
    deterministic_image: {
      status: "COMPLETED",
      reason_codes: ["IMAGE_READABLE"],
    },
    image_model: {
      status: "UNAVAILABLE",
      reason_code: "MODEL_NOT_PROMOTED",
      model_version: null,
    },
    structured_model: {
      status: "UNAVAILABLE",
      reason_code: "MODEL_NOT_PROMOTED",
      model_version: null,
    },
    text_fraud: {
      status: "SUCCESS",
      class: null,
      policy_score: null,
      score_is_probability: false,
      reason_codes: [],
      evidence_quality: "HIGH",
      ruleset_version: "ghana-momo-obvious-scam-rules-v1",
      limitations: ["ABSENCE_OF_RULE_MATCH_IS_NOT_PROOF_OF_GENUINENESS"],
    },
    automated_evidence_immutable: true,
  },
  ocr_review: {
    status: "CONFIRMED",
    ocr_result_id: "ocr-result-id",
    confirmed_field_count: 10,
    correction_count: 1,
    schema_version: "ocr-fields-v1",
  },
  versions: {
    policy_version: "risk-policy-v1",
    policy_sha256: null,
    rule_set_version: "demo-1",
    ocr_pipeline_version: "ocr-v1",
    ocr_engine_version: "tesseract",
    image_forensics_version: "image-v1",
    image_model_version: null,
    structured_model_version: null,
    text_fraud_schema_version: "momo-text-fraud-assessment-v1",
    text_fraud_ruleset_version: "ghana-momo-obvious-scam-rules-v1",
  },
  progress: {
    current_stage: null,
    completed_stage_count: 8,
    total_stage_count: 8,
    stages: [],
  },
  evidence_url: "/api/v1/analyses/run-1/evidence",
  created_at: "2026-08-15T12:00:00Z",
  completed_at: "2026-08-15T12:00:01Z",
} as AnalysisResult;

test("keeps the owner result concise and separates risk from verification", async () => {
  const view = await render(<AnalysisResultView result={partialResult} />);
  expect(view.getByLabelText("Status: Inconclusive")).toBeTruthy();
  expect(view.getByText("Transaction verification")).toBeTruthy();
  expect(view.getByText("Fraud risk assessment")).toBeTruthy();
  expect(view.getByLabelText("Status: Mismatch found")).toBeTruthy();
  expect(view.queryByText(/verified genuine|confirmed fraud|safe/i)).toBeNull();
  expect(view.queryByText(/risk score/i)).toBeNull();
  expect(view.queryByText("Confirmed OCR review")).toBeNull();
  expect(view.queryByText("Evidence availability")).toBeNull();
  expect(view.queryByText("Limitations and missing signals")).toBeNull();
});

test("moves technical evidence and limitations into the details view", async () => {
  const view = await render(<AnalysisDetailsView result={partialResult} />);
  expect(view.getByText("OCR evidence")).toBeTruthy();
  expect(view.getByText(/10 confirmed fields.*1 correction/i)).toBeTruthy();
  expect(view.getByText("Image evidence")).toBeTruthy();
  expect(view.getByText("Component availability")).toBeTruthy();
  expect(view.getAllByText(/Image model unavailable/i).length).toBeGreaterThan(
    0,
  );
  expect(view.getByText("Limitations and missing signals")).toBeTruthy();
  expect(view.getByText("Evidence versions")).toBeTruthy();
});

test("renders a categorical high-risk result without inventing a score", async () => {
  const highRisk = {
    ...partialResult,
    status: "COMPLETED",
    risk: {
      ...partialResult.risk,
      status: "AVAILABLE",
      band: "high_risk",
      conclusion_status: "CONCLUSIVE",
      component_status: "COMPLETE",
      class: "FRAUDULENT",
      summary: "Multiple recorded signals require review.",
      reasons: [
        {
          code: "REFERENCE_MISMATCH",
          title: "Reference mismatch",
          severity: "HIGH",
        },
      ],
      missing_signals: [],
    },
  } as AnalysisResult;
  const view = await render(<AnalysisResultView result={highRisk} />);
  expect(view.getByLabelText("Status: High risk")).toBeTruthy();
  expect(
    view.getByText("Multiple recorded signals require review."),
  ).toBeTruthy();
  expect(view.queryByText(/Reference mismatch/)).toBeNull();
  expect(view.queryByText(/risk score/i)).toBeNull();
});

test("keeps a partial high-risk conclusion above degraded component copy", async () => {
  const highRisk = {
    ...partialResult,
    risk: {
      ...partialResult.risk,
      status: "PARTIAL",
      band: "high_risk",
      class: "FRAUDULENT",
      conclusion_status: "CONCLUSIVE",
      component_status: "DEGRADED",
      summary: "Strong scam-language indicators require immediate caution.",
      reasons: [
        {
          code: "PIN_OR_OTP_REQUEST",
          title: "Secret code requested",
          severity: "CRITICAL",
        },
      ],
    },
  } as AnalysisResult;

  const view = await render(<AnalysisResultView result={highRisk} />);
  expect(view.getByLabelText("Status: High risk")).toBeTruthy();
  expect(view.getByText("Some components unavailable")).toBeTruthy();
  expect(
    view.getByText(
      "The high fraud-risk conclusion remains valid. Review unavailable components below.",
    ),
  ).toBeTruthy();
  expect(view.queryByText(/persisted result is inconclusive/i)).toBeNull();
});
