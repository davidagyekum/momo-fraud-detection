import { useState } from "react";
import { Text, View } from "react-native";

import {
  AppButton,
  AppCard,
  InlineAlert,
  StatusBadge,
  uiStyles,
} from "@/components/ui";
import { verificationTone } from "@/lib/verification-client";
import {
  highRiskSummaryFromReasonCodes,
  riskTone,
} from "@/lib/fraud-risk-presentation";
import type { AnalysisResult, RiskBand } from "@/types/analysis";

const riskLabels: Record<RiskBand, string> = {
  low_risk: "Low risk",
  medium_risk: "Medium risk",
  high_risk: "High fraud risk",
  inconclusive: "Inconclusive — no reliable fraud classification",
};

const INCONCLUSIVE_COPY =
  "The available evidence did not support a decisive result. This is not a genuine or safe verdict.";
const COUNTERFEIT_GUIDANCE =
  "Do not act on this message. Do not send money or disclose a PIN, OTP or security code. Verify through an official provider channel.";

function evidenceLabel(status: string): string {
  return status.toLowerCase().replaceAll("_", " ");
}

const friendlyEvidenceLabels: Record<string, string> = {
  IMAGE_MODEL_ARTIFACT_MISSING: "The optional image model is not available.",
  image_model: "The optional image model is not available.",
  NOT_APPLICABLE_SCREENSHOT_ONLY:
    "Structured transaction checks do not apply to screenshot-only analysis.",
  REFERENCE_VERIFICATION_NOT_APPLICABLE:
    "Stored-reference verification was not requested for this screenshot-only analysis.",
  DETERMINISTIC_IMAGE_SUPPORTING_ONLY:
    "Image checks provide supporting evidence only.",
  OCR_CONFIDENCE_LOW: "Some detected text had low OCR confidence.",
};

function friendlyEvidenceLabel(value: string): string {
  const knownLabel = friendlyEvidenceLabels[value];
  if (knownLabel) return knownLabel;
  if (!value.includes("_")) return value;
  const readable = evidenceLabel(value);
  return `${readable.charAt(0).toUpperCase()}${readable.slice(1)}.`;
}

export function AnalysisResultView({ result }: { result: AnalysisResult }) {
  const degraded = result.risk.component_status === "DEGRADED";
  const conclusive = result.risk.conclusion_status === "CONCLUSIVE";
  const bandLabel =
    result.risk.band === "high_risk"
      ? "high"
      : result.risk.band === "medium_risk"
        ? "medium"
        : result.risk.band === "low_risk"
          ? "low"
          : "inconclusive";
  const counterfeitTextEvidence =
    result.evidence_summary.text_fraud.class === "FRAUDULENT";
  const reasonCodes = result.risk.reasons.map((reason) => reason.code);
  const riskSummary =
    result.risk.band === "inconclusive"
      ? INCONCLUSIVE_COPY
      : result.risk.band === "high_risk"
        ? highRiskSummaryFromReasonCodes(reasonCodes)
        : result.risk.summary;
  return (
    <View style={uiStyles.stack}>
      <AppCard>
        <Text style={uiStyles.cardTitle}>Fraud risk assessment</Text>
        <StatusBadge
          label={riskLabels[result.risk.band]}
          tone={riskTone(result.risk.band)}
        />
        <Text selectable style={uiStyles.body}>
          {riskSummary}
        </Text>
        {counterfeitTextEvidence ? (
          <InlineAlert
            tone="error"
            title="What to do now"
            message={COUNTERFEIT_GUIDANCE}
          />
        ) : null}
      </AppCard>

      {degraded ? (
        <InlineAlert
          tone="warning"
          title={
            conclusive ? "Some components unavailable" : "Evidence incomplete"
          }
          message={
            conclusive
              ? `The ${bandLabel} fraud-risk conclusion remains valid. Review unavailable components below.`
              : "The available evidence was insufficient for a fraud-risk conclusion. Review unavailable components below."
          }
        />
      ) : null}

      <AppCard>
        <Text style={uiStyles.cardTitle}>Transaction verification</Text>
        {result.verification ? (
          <>
            <StatusBadge
              label={result.verification.label}
              tone={verificationTone(result.verification.status)}
            />
            <Text style={uiStyles.body}>{result.verification.summary}</Text>
            <Text style={uiStyles.muted}>{result.verification.disclaimer}</Text>
          </>
        ) : (
          <Text style={uiStyles.muted}>
            No stored reference comparison is available.
          </Text>
        )}
      </AppCard>
    </View>
  );
}

export function AnalysisDetailsView({ result }: { result: AnalysisResult }) {
  const [technicalDetailsVisible, setTechnicalDetailsVisible] = useState(false);
  const imageModelUnavailable =
    result.evidence_summary.image_model.status === "UNAVAILABLE";
  return (
    <View style={uiStyles.stack}>
      <AppCard>
        <Text style={uiStyles.cardTitle}>Why this risk result</Text>
        {result.risk.reasons.length > 0 ? (
          result.risk.reasons.map((reason) => (
            <Text key={reason.code} style={uiStyles.body} selectable>
              • {reason.title}
            </Text>
          ))
        ) : (
          <Text style={uiStyles.muted}>
            No additional risk reasons were recorded.
          </Text>
        )}
        <Text style={uiStyles.muted} selectable>
          {result.risk.disclaimer}
        </Text>
      </AppCard>

      <AppCard>
        <Text style={uiStyles.cardTitle}>Technical evidence and versions</Text>
        <Text style={uiStyles.muted}>
          Detailed OCR, component, limitation, and version information is
          available when you need it.
        </Text>
        <AppButton
          label={
            technicalDetailsVisible
              ? "Hide technical details"
              : "Show technical details"
          }
          accessibilityHint="Shows or hides the detailed evidence recorded for this analysis."
          accessibilityState={{ expanded: technicalDetailsVisible }}
          onPress={() => setTechnicalDetailsVisible((visible) => !visible)}
          variant="secondary"
        />
      </AppCard>

      {technicalDetailsVisible ? (
        <>
          <AppCard>
            <Text style={uiStyles.cardTitle}>OCR evidence</Text>
            {result.ocr_review.status === "NOT_REQUIRED" ? (
              <Text style={uiStyles.body} selectable>
                Field confirmation was not required for this screenshot-only
                analysis.
              </Text>
            ) : (
              <>
                <Text style={uiStyles.body} selectable>
                  {result.ocr_review.confirmed_field_count} confirmed fields;{" "}
                  {result.ocr_review.correction_count}{" "}
                  {result.ocr_review.correction_count === 1
                    ? "correction"
                    : "corrections"}
                  .
                </Text>
                <Text style={uiStyles.muted} selectable>
                  Confirmation schema: {result.ocr_review.schema_version}
                </Text>
              </>
            )}
          </AppCard>

          <AppCard>
            <Text style={uiStyles.cardTitle}>Image evidence</Text>
            <Text style={uiStyles.body} selectable>
              Deterministic image checks:{" "}
              {evidenceLabel(
                result.evidence_summary.deterministic_image.status,
              )}
            </Text>
            <Text style={uiStyles.body} selectable>
              {imageModelUnavailable
                ? "Image model unavailable"
                : `Image model: ${evidenceLabel(result.evidence_summary.image_model.status)}`}
            </Text>
          </AppCard>

          <AppCard>
            <Text style={uiStyles.cardTitle}>Component availability</Text>
            <Text style={uiStyles.body} selectable>
              Risk conclusion: {evidenceLabel(result.risk.conclusion_status)}
            </Text>
            <Text style={uiStyles.body} selectable>
              Overall availability:{" "}
              {evidenceLabel(result.risk.component_status)}
            </Text>
            <Text style={uiStyles.body} selectable>
              Structured model:{" "}
              {evidenceLabel(result.evidence_summary.structured_model.status)}
            </Text>
            <Text style={uiStyles.body} selectable>
              Message-risk rules:{" "}
              {evidenceLabel(result.evidence_summary.text_fraud.status)}
            </Text>
            <Text style={uiStyles.muted} selectable>
              Automated evidence is stored immutably for this run.
            </Text>
          </AppCard>

          {result.risk.missing_signals.length > 0 ||
          result.risk.limitations.length > 0 ? (
            <AppCard>
              <Text style={uiStyles.cardTitle}>
                Limitations and missing signals
              </Text>
              {[...result.risk.missing_signals, ...result.risk.limitations].map(
                (item, index) => (
                  <Text
                    key={`${item}-${index}`}
                    style={uiStyles.muted}
                    selectable
                  >
                    • {friendlyEvidenceLabel(item)}
                  </Text>
                ),
              )}
            </AppCard>
          ) : null}

          <AppCard>
            <Text style={uiStyles.cardTitle}>Evidence versions</Text>
            <Text style={uiStyles.muted} selectable>
              Policy: {result.versions.policy_version ?? "Unavailable"}
            </Text>
            <Text style={uiStyles.muted} selectable>
              OCR pipeline:{" "}
              {result.versions.ocr_pipeline_version ?? "Unavailable"}
            </Text>
            <Text style={uiStyles.muted} selectable>
              Verification rules:{" "}
              {result.versions.rule_set_version ?? "Unavailable"}
            </Text>
            <Text style={uiStyles.muted} selectable>
              Message-risk rules:{" "}
              {result.versions.text_fraud_ruleset_version ?? "Unavailable"}
            </Text>
          </AppCard>
        </>
      ) : null}
    </View>
  );
}
