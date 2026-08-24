import { type ReactNode, useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import {
  AppButton,
  AppCard,
  InlineAlert,
  StatusBadge,
  uiStyles,
} from "@/components/ui";
import {
  evidenceRowsForPreview,
  riskPresentation,
} from "@/lib/fraud-risk-presentation";
import type { OCRTextFraudPreview } from "@/lib/ocr-client";
import { palette, spacing, typeScale } from "@/theme/tokens";

export function TextFraudRiskCard({
  preview,
  footer,
}: {
  preview: OCRTextFraudPreview;
  footer?: ReactNode;
}) {
  const [detailsVisible, setDetailsVisible] = useState(false);
  const presentation = riskPresentation(preview);
  const evidenceRows = evidenceRowsForPreview(preview);

  return (
    <AppCard>
      <View
        accessible
        accessibilityLabel={`Preliminary message-risk preview. ${presentation.title}. ${presentation.subtitle}`}
        accessibilityLiveRegion={
          preview.class === "FRAUDULENT" ? "assertive" : "polite"
        }
        accessibilityRole={preview.class === "FRAUDULENT" ? "alert" : undefined}
        style={styles.heading}
      >
        <Text accessibilityRole="header" style={uiStyles.cardTitle}>
          Message-risk preview
        </Text>
        <StatusBadge label={presentation.title} tone={presentation.tone} />
      </View>

      <Text selectable style={styles.subtitle}>
        {presentation.subtitle}
      </Text>
      {presentation.guidance ? (
        <InlineAlert
          tone={presentation.tone}
          title="What to do now"
          message={presentation.guidance}
        />
      ) : null}
      {footer ? <View style={styles.footer}>{footer}</View> : null}

      <View style={styles.evidence}>
        <Text style={styles.sectionTitle}>Evidence summary</Text>
        {evidenceRows.map((row) => (
          <View key={row.label} style={styles.evidenceRow}>
            <Text selectable style={styles.evidenceLabel}>
              {row.label}
            </Text>
            <Text selectable style={styles.evidenceValue}>
              {row.value}
            </Text>
          </View>
        ))}
      </View>

      <AppButton
        label={detailsVisible ? "Hide result details" : "Why this result?"}
        onPress={() => setDetailsVisible((visible) => !visible)}
        variant="secondary"
        accessibilityState={{ expanded: detailsVisible }}
        accessibilityHint="Shows or hides detailed rule reasons, score, disclaimer and versions."
      />
      {detailsVisible ? (
        <View style={styles.reasons}>
          {preview.score !== null ? (
            <Text selectable style={styles.score}>
              Policy score {Math.round(preview.score)}/100: not a probability
            </Text>
          ) : null}
          {preview.reasons.length > 0 ? (
            <>
              <Text style={styles.sectionTitle}>Detailed rule reasons</Text>
              {preview.reasons.map((reason) => (
                <View key={reason.code} style={styles.reason}>
                  <Text selectable style={styles.reasonTitle}>
                    {reason.severity} · {reason.title}
                  </Text>
                  <Text selectable style={styles.reasonSummary}>
                    {reason.summary}
                  </Text>
                </View>
              ))}
            </>
          ) : null}
          <Text selectable style={styles.disclaimer}>
            {preview.disclaimer}
          </Text>
          <Text selectable style={styles.disclaimer}>
            Assessment schema: {preview.schema_version}
          </Text>
          <Text selectable style={styles.disclaimer}>
            Fraud ruleset: {preview.ruleset_version}
          </Text>
        </View>
      ) : null}
    </AppCard>
  );
}

const styles = StyleSheet.create({
  heading: { gap: spacing.sm, alignItems: "flex-start" },
  subtitle: {
    color: palette.ink,
    fontSize: typeScale.body,
    lineHeight: 24,
    fontWeight: "700",
  },
  score: {
    color: palette.ink,
    fontSize: typeScale.caption,
    fontWeight: "700",
  },
  reasons: { gap: spacing.md },
  evidence: { gap: spacing.sm },
  evidenceRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: palette.border,
    paddingBottom: spacing.sm,
  },
  evidenceLabel: {
    color: palette.muted,
    fontSize: typeScale.caption,
    fontWeight: "700",
  },
  evidenceValue: {
    flex: 1,
    color: palette.ink,
    fontSize: typeScale.caption,
    fontWeight: "700",
    textAlign: "right",
  },
  sectionTitle: {
    color: palette.ink,
    fontSize: typeScale.body,
    fontWeight: "800",
  },
  reason: { gap: spacing.xs },
  reasonTitle: {
    color: palette.ink,
    fontSize: typeScale.body,
    fontWeight: "700",
  },
  reasonSummary: {
    color: palette.muted,
    fontSize: typeScale.body,
    lineHeight: 24,
  },
  disclaimer: {
    color: palette.muted,
    fontSize: typeScale.caption,
    lineHeight: 19,
  },
  footer: {
    gap: spacing.md,
    borderTopWidth: 1,
    borderTopColor: palette.border,
    paddingTop: spacing.md,
  },
});
