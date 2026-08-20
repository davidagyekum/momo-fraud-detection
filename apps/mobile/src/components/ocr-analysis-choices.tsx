import { Text, View } from "react-native";

import { TextFraudRiskCard } from "@/components/text-fraud-risk-card";
import { AppButton, InlineAlert, uiStyles } from "@/components/ui";
import type { OCRTextFraudPreview } from "@/lib/ocr-client";
import { spacing } from "@/theme/tokens";

export function OCRAnalysisChoices({
  preview,
  online,
  saving,
  saveError,
  comparisonExpanded,
  onSave,
  onToggleComparison,
}: {
  preview: OCRTextFraudPreview;
  online: boolean;
  saving: boolean;
  saveError: string | null;
  comparisonExpanded: boolean;
  onSave: () => void;
  onToggleComparison: () => void;
}) {
  return (
    <TextFraudRiskCard
      preview={preview}
      footer={
        <View style={{ gap: spacing.md }}>
          <View style={{ gap: spacing.xs }}>
            <Text style={uiStyles.cardTitle}>Save this assessment</Text>
            <Text style={uiStyles.body}>
              Save the screenshot-based fraud-risk result now. A transaction
              reference, amount, date and receipt status are not required.
            </Text>
          </View>
          {saveError ? (
            <InlineAlert
              tone="error"
              title="Risk result not saved"
              message={saveError}
            />
          ) : null}
          <AppButton
            label="Save screenshot risk result"
            onPress={onSave}
            loading={saving}
            disabled={!online}
            accessibilityHint="Saves this screenshot assessment and opens its persisted result"
          />
          <AppButton
            label={
              comparisonExpanded
                ? "Hide optional transaction comparison"
                : "Compare with a transaction record (optional)"
            }
            onPress={onToggleComparison}
            variant="secondary"
            accessibilityHint="Shows or hides fields used only for stored or imported reference comparison"
            accessibilityState={{ expanded: comparisonExpanded }}
          />
        </View>
      }
    />
  );
}
