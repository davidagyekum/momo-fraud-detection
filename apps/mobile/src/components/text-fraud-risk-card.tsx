import type { ReactNode } from "react";
import { StyleSheet, Text, View } from "react-native";

import { AppCard, InlineAlert, StatusBadge, uiStyles } from "@/components/ui";
import type { OCRTextFraudPreview } from "@/lib/ocr-client";
import { palette, spacing, typeScale } from "@/theme/tokens";

function previewTitle(preview: OCRTextFraudPreview): string {
  if (preview.class === "FRAUDULENT") return "High fraud risk";
  if (preview.class === "SUSPICIOUS") return "Suspicious message";
  if (preview.status === "UNAVAILABLE") return "Text assessment unavailable";
  return "No decisive text signal";
}

function previewTone(
  preview: OCRTextFraudPreview,
): "error" | "info" | "warning" {
  if (preview.class === "FRAUDULENT") return "error";
  if (preview.class === "SUSPICIOUS") return "warning";
  return "info";
}

function safetyMessage(preview: OCRTextFraudPreview): string | null {
  if (preview.class === "FRAUDULENT") {
    return "Do not share a PIN, OTP or security code, and do not send money based only on this message. Verify through an official provider channel.";
  }
  if (preview.class === "SUSPICIOUS") {
    return "Pause before acting. Confirm the message through an official provider channel or a contact you already trust.";
  }
  return null;
}

export function TextFraudRiskCard({
  preview,
  footer,
}: {
  preview: OCRTextFraudPreview;
  footer?: ReactNode;
}) {
  const safety = safetyMessage(preview);
  const title = previewTitle(preview);

  return (
    <AppCard>
      <View
        accessible
        accessibilityLabel={`Preliminary message-risk preview. ${title}. ${preview.summary}`}
        accessibilityLiveRegion="polite"
        style={styles.heading}
      >
        <Text accessibilityRole="header" style={uiStyles.cardTitle}>
          Message-risk preview
        </Text>
        <StatusBadge label={title} tone={previewTone(preview)} />
      </View>

      <Text style={uiStyles.body}>{preview.summary}</Text>
      {preview.score !== null ? (
        <Text style={styles.score}>
          Policy score {Math.round(preview.score)}/100 — not a probability
        </Text>
      ) : null}

      {safety ? (
        <InlineAlert
          tone={previewTone(preview)}
          title="What to do now"
          message={safety}
        />
      ) : null}
      {footer ? <View style={styles.footer}>{footer}</View> : null}

      {preview.reasons.length > 0 ? (
        <View style={styles.reasons}>
          <Text style={styles.sectionTitle}>Why this appeared</Text>
          {preview.reasons.map((reason) => (
            <View key={reason.code} style={styles.reason}>
              <Text style={styles.reasonTitle}>
                {reason.severity} · {reason.title}
              </Text>
              <Text style={styles.reasonSummary}>{reason.summary}</Text>
            </View>
          ))}
        </View>
      ) : null}
      <Text style={styles.disclaimer}>{preview.disclaimer}</Text>
    </AppCard>
  );
}

const styles = StyleSheet.create({
  heading: { gap: spacing.sm, alignItems: "flex-start" },
  score: {
    color: palette.ink,
    fontSize: typeScale.caption,
    fontWeight: "700",
  },
  reasons: { gap: spacing.md },
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
