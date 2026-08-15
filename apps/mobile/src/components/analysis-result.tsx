import { Text, View } from "react-native";

import { AppCard, InlineAlert, StatusBadge, uiStyles } from "@/components/ui";
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
  const imageModelUnavailable =
    result.evidence_summary.image_model.status === "UNAVAILABLE";
  return (
    <View style={uiStyles.stack}>
      {result.status === "PARTIAL" ? (
        <InlineAlert
          tone="warning"
          title="Partial analysis"
          message="Some evidence was unavailable. Review the limitations before acting."
        />
      ) : null}

      <AppCard>
        <Text style={uiStyles.cardTitle}>Fraud risk assessment</Text>
        <StatusBadge
          label={riskLabels[result.risk.band]}
          tone={result.risk.band === "low_risk" ? "success" : "warning"}
        />
        <Text style={uiStyles.body}>{result.risk.summary}</Text>
        {result.risk.score !== null ? (
          <Text style={uiStyles.muted}>
            Risk score: {Math.round(result.risk.score * 100)}%. This is model
            evidence, not proof of fraud.
          </Text>
        ) : null}
        {result.risk.reasons.map((reason) => (
          <Text key={reason.code} style={uiStyles.body}>
            • {reason.title}
          </Text>
        ))}
      </AppCard>

      <AppCard>
        <Text style={uiStyles.cardTitle}>Transaction verification</Text>
        {result.verification ? (
          <>
            <StatusBadge
              label={result.verification.label}
              tone={
                result.verification.status === "VERIFIED"
                  ? "success"
                  : "warning"
              }
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

      <AppCard>
        <Text style={uiStyles.cardTitle}>Evidence availability</Text>
        <Text style={uiStyles.body}>
          Deterministic image checks:{" "}
          {evidenceLabel(result.evidence_summary.deterministic_image.status)}
        </Text>
        <Text style={uiStyles.body}>
          {imageModelUnavailable
            ? "Image model unavailable"
            : `Image model: ${evidenceLabel(result.evidence_summary.image_model.status)}`}
        </Text>
        <Text style={uiStyles.body}>
          Structured model:{" "}
          {evidenceLabel(result.evidence_summary.structured_model.status)}
        </Text>
        <Text style={uiStyles.muted}>
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
              <Text key={`${item}-${index}`} style={uiStyles.muted}>
                • {item.replaceAll("_", " ")}
              </Text>
            ),
          )}
        </AppCard>
      ) : null}
    </View>
  );
}
