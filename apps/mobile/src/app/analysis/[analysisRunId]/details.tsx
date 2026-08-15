import { useQuery } from "@tanstack/react-query";
import { Redirect, useLocalSearchParams } from "expo-router";
import { Text } from "react-native";

import { AnalysisDetailsView } from "@/components/analysis-result";
import {
  AppCard,
  InlineAlert,
  RetryState,
  ScreenShell,
  SkeletonBlock,
  uiStyles,
} from "@/components/ui";
import { getAnalysis } from "@/lib/analysis-client";
import { useAuth } from "@/state/auth-context";
import { useIsOnline } from "@/state/network-context";

export default function AnalysisDetailsScreen() {
  const { analysisRunId } = useLocalSearchParams<{ analysisRunId: string }>();
  const { request, status } = useAuth();
  const online = useIsOnline();
  const validId = typeof analysisRunId === "string" && analysisRunId.length > 0;
  const analysis = useQuery({
    queryKey: ["analysis", analysisRunId],
    queryFn: () => getAnalysis(request, analysisRunId ?? ""),
    enabled: validId && status === "authenticated" && online,
    retry: 1,
  });

  if (status === "restoring") {
    return (
      <ScreenShell title="Analysis details">
        <SkeletonBlock label="Restoring secure session" />
      </ScreenShell>
    );
  }
  if (status !== "authenticated") return <Redirect href="/(auth)/login" />;
  return (
    <ScreenShell
      title="Analysis details"
      subtitle="Technical evidence and limitations are kept here so the main result stays clear."
    >
      {!validId ? (
        <InlineAlert
          tone="error"
          title="Details unavailable"
          message="This analysis link is invalid."
        />
      ) : !online ? (
        <AppCard>
          <Text style={uiStyles.cardTitle}>Details unavailable offline</Text>
          <Text style={uiStyles.muted}>
            Reconnect to load the immutable evidence details.
          </Text>
        </AppCard>
      ) : analysis.isPending ? (
        <SkeletonBlock label="Loading analysis details" />
      ) : analysis.isError ? (
        <RetryState
          message={analysis.error.message}
          onRetry={() => void analysis.refetch()}
        />
      ) : analysis.data ? (
        <AnalysisDetailsView result={analysis.data} />
      ) : null}
    </ScreenShell>
  );
}
