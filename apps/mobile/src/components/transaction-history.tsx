import { Pressable, Text, View } from "react-native";

import {
  AppCard,
  EmptyState,
  RetryState,
  SkeletonBlock,
  StatusBadge,
  uiStyles,
} from "@/components/ui";
import type { RiskBand } from "@/types/analysis";
import type { TransactionSummary } from "@/types/history";
import { riskTone } from "@/lib/fraud-risk-presentation";
import { verificationTone } from "@/lib/verification-client";

const riskLabels: Record<RiskBand, string> = {
  low_risk: "Low risk",
  medium_risk: "Medium risk",
  high_risk: "High risk",
  inconclusive: "Inconclusive",
};

function readableStatus(value: string): string {
  return value
    .toLowerCase()
    .replaceAll("_", " ")
    .replace(/^./, (letter) => letter.toUpperCase());
}

export function TransactionHistoryView({
  items,
  pending = false,
  error,
  onRetry,
  onOpen,
}: {
  items: TransactionSummary[];
  pending?: boolean;
  error?: string | null;
  onRetry?: () => void;
  onOpen: (transactionId: string) => void;
}) {
  if (pending) return <SkeletonBlock label="Loading check history" />;
  if (error && onRetry) return <RetryState message={error} onRetry={onRetry} />;
  if (items.length === 0) {
    return (
      <EmptyState
        title="No screenshot checks found"
        message="Upload a screenshot to begin a check."
      />
    );
  }
  return (
    <View style={uiStyles.stack}>
      {items.map((item) => (
        <AppCard key={item.id}>
          <Text style={uiStyles.cardTitle}>
            {item.provider_code
              ? `${item.provider_code} screenshot check`
              : "Screenshot check"}
          </Text>
          <Text style={uiStyles.muted}>
            {new Date(item.created_at).toLocaleString()}
          </Text>
          {item.display_reference_masked ? (
            <Text style={uiStyles.body}>
              Reference: {item.display_reference_masked}
            </Text>
          ) : null}
          {item.latest_analysis ? (
            <View style={uiStyles.stack}>
              <StatusBadge
                label={`Risk: ${riskLabels[item.latest_analysis.band]}`}
                tone={riskTone(item.latest_analysis.band)}
              />
              <StatusBadge
                label={`Verification: ${readableStatus(item.latest_analysis.verification_status ?? "UNVERIFIED")}`}
                tone={verificationTone(
                  item.latest_analysis.verification_status ?? "UNVERIFIED",
                )}
              />
            </View>
          ) : (
            <Text style={uiStyles.muted}>Analysis has not been completed.</Text>
          )}
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Open check details"
            onPress={() => onOpen(item.id)}
          >
            <Text style={uiStyles.link}>Open details</Text>
          </Pressable>
        </AppCard>
      ))}
    </View>
  );
}
