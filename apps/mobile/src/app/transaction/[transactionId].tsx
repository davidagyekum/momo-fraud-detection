import { useQuery } from "@tanstack/react-query";
import { type Href, Redirect, router, useLocalSearchParams } from "expo-router";
import { Text } from "react-native";

import {
  AppButton,
  AppCard,
  InlineAlert,
  RetryState,
  ScreenShell,
  SkeletonBlock,
  StatusBadge,
  uiStyles,
} from "@/components/ui";
import { getTransaction } from "@/lib/history-client";
import { useAuth } from "@/state/auth-context";
import { useIsOnline } from "@/state/network-context";

export default function TransactionDetailScreen() {
  const { transactionId } = useLocalSearchParams<{ transactionId: string }>();
  const { request, status } = useAuth();
  const online = useIsOnline();
  const validId = typeof transactionId === "string" && transactionId.length > 0;
  const detail = useQuery({
    queryKey: ["transaction", transactionId],
    queryFn: () => getTransaction(request, transactionId ?? ""),
    enabled: validId && status === "authenticated" && online,
    staleTime: 0,
    retry: 1,
  });
  if (status === "restoring")
    return (
      <ScreenShell title="Receipt details">
        <SkeletonBlock label="Restoring secure session" />
      </ScreenShell>
    );
  if (status !== "authenticated") return <Redirect href="/(auth)/login" />;
  return (
    <ScreenShell
      title="Receipt details"
      subtitle="Only your persisted transaction and immutable analysis records are shown."
    >
      {!validId ? (
        <InlineAlert
          tone="error"
          title="Receipt unavailable"
          message="This receipt link is invalid."
        />
      ) : !online ? (
        <AppCard>
          <Text style={uiStyles.cardTitle}>Details unavailable offline</Text>
          <Text style={uiStyles.muted}>
            Reconnect to load this private record.
          </Text>
        </AppCard>
      ) : detail.isPending ? (
        <SkeletonBlock label="Loading receipt details" />
      ) : detail.isError ? (
        <RetryState
          message={detail.error.message}
          onRetry={() => void detail.refetch()}
        />
      ) : detail.data ? (
        <>
          <AppCard>
            <Text style={uiStyles.cardTitle}>
              {detail.data.provider_code
                ? `${detail.data.provider_code} receipt`
                : "Receipt"}
            </Text>
            <StatusBadge
              label={`Transaction: ${detail.data.status.toLowerCase().replaceAll("_", " ")}`}
            />
            {detail.data.display_reference_masked ? (
              <Text style={uiStyles.body}>
                Reference: {detail.data.display_reference_masked}
              </Text>
            ) : null}
            <Text style={uiStyles.muted}>
              {detail.data.confirmed_field_coverage.status === "NOT_REQUIRED"
                ? "Field confirmation was not required for this screenshot-only analysis."
                : `${detail.data.confirmed_field_coverage.field_count} confirmed fields · ${detail.data.confirmed_field_coverage.correction_count} corrections`}
            </Text>
          </AppCard>
          {detail.data.analysis_runs.length === 0 ? (
            <InlineAlert
              tone="info"
              title="No analysis yet"
              message="Complete OCR review to start an analysis."
            />
          ) : (
            detail.data.analysis_runs.map((run, index) => (
              <AppCard key={run.id}>
                <Text style={uiStyles.cardTitle}>
                  {index === 0 ? "Latest analysis" : "Prior analysis"}
                </Text>
                <StatusBadge
                  label={`Risk: ${run.band.toLowerCase().replaceAll("_", " ")}`}
                  tone="warning"
                />
                <Text style={uiStyles.body}>
                  Verification:{" "}
                  {run.verification_status?.toLowerCase() ?? "unverified"}
                </Text>
                <AppButton
                  label={
                    index === 0 ? "Open latest analysis" : "Open prior analysis"
                  }
                  onPress={() =>
                    router.push({
                      pathname: "/analysis/[analysisRunId]",
                      params: { analysisRunId: run.id },
                    } as unknown as Href)
                  }
                  variant="secondary"
                />
              </AppCard>
            ))
          )}
        </>
      ) : null}
      <AppButton
        label="Back to history"
        onPress={() => router.replace("/(tabs)/history")}
        variant="secondary"
      />
    </ScreenShell>
  );
}
