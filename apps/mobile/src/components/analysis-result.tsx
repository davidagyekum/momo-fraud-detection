import { Text, View } from "react-native";

import { AppCard, InlineAlert, StatusBadge, uiStyles } from "@/components/ui";
import { verificationTone } from "@/lib/verification-client";
import type { AnalysisResult, RiskBand } from "@/types/analysis";

const riskLabels: Record<RiskBand, string> = {
  low_risk: "Low risk",
  medium_risk: "Medium risk",
  high_risk: "High risk",
  inconclusive: "Inconclusive",
};

function evidenceLabel(status: string): string {
  return status.toLowerCase().replaceAll("_", " ");
}

export function AnalysisResultView({ result }: { result: AnalysisResult }) {
  const degraded = result.risk.component_status === "DEGRADED";
  const conclusive = result.risk.conclusion_status === "CONCLUSIVE";
  const bandLabel = riskLabels[result.risk.band]
    .toLowerCase()
    .replace(" risk", "");
  return (
    <View style={uiStyles.stack}>
      <AppCard>
        <Text style={uiStyles.cardTitle}>Fraud risk assessment</Text>
        <StatusBadge
          label={riskLabels[result.risk.band]}
          tone={
            result.risk.band === "low_risk"
              ? "success"
              : result.risk.band === "high_risk"
                ? "error"
                : "warning"
          }
        />
        <Text style={uiStyles.body}>{result.risk.summary}</Text>
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
        <Text style={uiStyles.cardTitle}>Evidence availability</Text>
        <Text style={uiStyles.body} selectable>
          Risk conclusion: {evidenceLabel(result.risk.conclusion_status)}
        </Text>
        <Text style={uiStyles.body} selectable>
          Component availability: {evidenceLabel(result.risk.component_status)}
        </Text>
        <Text style={uiStyles.body} selectable>
          Deterministic image checks:{" "}
          {evidenceLabel(result.evidence_summary.deterministic_image.status)}
        </Text>
        <Text style={uiStyles.body} selectable>
          {imageModelUnavailable
            ? "Image model unavailable"
            : `Image model: ${evidenceLabel(result.evidence_summary.image_model.status)}`}
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
              <Text key={`${item}-${index}`} style={uiStyles.muted} selectable>
                • {item.replaceAll("_", " ")}
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
          OCR pipeline: {result.versions.ocr_pipeline_version ?? "Unavailable"}
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
    </View>
  );
}
