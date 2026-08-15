import { useMutation, useQuery } from "@tanstack/react-query";
import { type Href, Redirect, router, useLocalSearchParams } from "expo-router";
import { useRef, useState } from "react";

import { AnalysisResultView } from "@/components/analysis-result";
import {
  AppButton,
  AppCard,
  InlineAlert,
  RetryState,
  ScreenShell,
  SkeletonBlock,
  uiStyles,
} from "@/components/ui";
import { pollAnalysis } from "@/lib/analysis-client";
import {
  createAnalysisReport,
  createEngagementKey,
  saveAndShareReport,
} from "@/lib/engagement-client";
import { useAuth } from "@/state/auth-context";
import { useIsOnline } from "@/state/network-context";
import { Text } from "react-native";

function readableError(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "The analysis result could not be loaded.";
}

export default function AnalysisScreen() {
  const { analysisRunId } = useLocalSearchParams<{ analysisRunId: string }>();
  const { request, response, status } = useAuth();
  const online = useIsOnline();
  const reportKey = useRef(createEngagementKey("report"));
  const [reportMessage, setReportMessage] = useState<string | null>(null);
  const validId = typeof analysisRunId === "string" && analysisRunId.length > 0;
  const analysis = useQuery({
    queryKey: ["analysis", analysisRunId],
    queryFn: ({ signal }) =>
      pollAnalysis(request, analysisRunId ?? "", { signal }),
    enabled: validId && status === "authenticated" && online,
    retry: 1,
    staleTime: 0,
  });
  const report = useMutation({
    mutationFn: async (transactionId: string) => {
      const artifact = await createAnalysisReport(
        request,
        transactionId,
        reportKey.current,
      );
      return saveAndShareReport(response, artifact);
    },
    onSuccess: (delivery) =>
      setReportMessage(
        delivery === "downloaded"
          ? "The private report was downloaded."
          : "The private report is ready in the device share sheet.",
      ),
    onError: (error) => setReportMessage(readableError(error)),
  });

  if (status === "restoring") {
    return (
      <ScreenShell title="Receipt analysis">
        <SkeletonBlock label="Restoring secure session" />
      </ScreenShell>
    );
  }
  if (status !== "authenticated") return <Redirect href="/(auth)/login" />;
  return (
    <ScreenShell
      title="Receipt analysis"
      subtitle="Fraud risk and transaction verification are separate evidence results."
    >
      {!validId ? (
        <InlineAlert
          tone="error"
          title="Analysis unavailable"
          message="This analysis link is invalid."
        />
      ) : !online ? (
        <AppCard>
          <Text style={uiStyles.cardTitle}>Analysis paused</Text>
          <Text style={uiStyles.muted}>
            Reconnect to resume this stored analysis run.
          </Text>
        </AppCard>
      ) : analysis.isPending ? (
        <AppCard>
          <SkeletonBlock label="Running receipt analysis" />
          <Text style={uiStyles.muted}>
            Checking confirmed receipt evidence and stored reference data…
          </Text>
        </AppCard>
      ) : analysis.isError ? (
        <RetryState
          message={readableError(analysis.error)}
          onRetry={() => void analysis.refetch()}
        />
      ) : analysis.data ? (
        <AnalysisResultView result={analysis.data} />
      ) : null}
      {analysis.data ? (
        <>
          <AppButton
            label="View analysis details"
            onPress={() =>
              router.push({
                pathname: "/analysis/[analysisRunId]/details",
                params: { analysisRunId: analysis.data.id },
              } as unknown as Href)
            }
          />
          <AppButton
            label="Save or share report"
            onPress={() => report.mutate(analysis.data.transaction_id)}
            loading={report.isPending}
            disabled={!online}
            variant="secondary"
          />
          {analysis.data.risk.band !== "low_risk" ||
          analysis.data.verification?.status === "MISMATCH" ? (
            <AppButton
              label="Report suspicious transaction"
              onPress={() =>
                router.push({
                  pathname: "/fraud-report/[transactionId]",
                  params: { transactionId: analysis.data.transaction_id },
                } as unknown as Href)
              }
              variant="secondary"
            />
          ) : null}
          {reportMessage ? (
            <InlineAlert
              tone={report.isError ? "error" : "info"}
              title={report.isError ? "Report unavailable" : "Report ready"}
              message={reportMessage}
            />
          ) : null}
          <AppButton
            label="Open transaction history"
            onPress={() =>
              router.push({
                pathname: "/transaction/[transactionId]",
                params: { transactionId: analysis.data.transaction_id },
              } as unknown as Href)
            }
            variant="secondary"
          />
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
