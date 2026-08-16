import { useQuery } from "@tanstack/react-query";
import { Redirect, useLocalSearchParams } from "expo-router";
import { Text } from "react-native";

import {
  AppCard,
  InlineAlert,
  RetryState,
  ScreenShell,
  SkeletonBlock,
  StatusBadge,
  uiStyles,
} from "@/components/ui";
import { getFraudReport } from "@/lib/engagement-client";
import { useAuth } from "@/state/auth-context";
import { useIsOnline } from "@/state/network-context";

function readable(value: string): string {
  return value.toLowerCase().replaceAll("_", " ");
}

export default function CaseStatusScreen() {
  const { caseId } = useLocalSearchParams<{ caseId: string }>();
  const { request, status } = useAuth();
  const online = useIsOnline();
  const validId = typeof caseId === "string" && caseId.length > 0;
  const fraudCase = useQuery({
    queryKey: ["owner-case", caseId],
    queryFn: () => getFraudReport(request, caseId ?? ""),
    enabled: validId && status === "authenticated" && online,
    retry: 1,
    staleTime: 0,
  });

  if (status === "restoring") {
    return (
      <ScreenShell title="Investigation status">
        <SkeletonBlock label="Restoring secure session" />
      </ScreenShell>
    );
  }
  if (status !== "authenticated") return <Redirect href="/(auth)/login" />;
  return (
    <ScreenShell
      title="Investigation status"
      subtitle="Human review is recorded separately and never rewrites the automated analysis."
    >
      {!validId ? (
        <InlineAlert
          tone="error"
          title="Case unavailable"
          message="This case link is invalid."
        />
      ) : fraudCase.isPending ? (
        <SkeletonBlock label="Loading investigation status" />
      ) : fraudCase.isError ? (
        <RetryState
          message={fraudCase.error.message}
          onRetry={() => void fraudCase.refetch()}
        />
      ) : fraudCase.data ? (
        <>
          <AppCard>
            <Text style={uiStyles.cardTitle}>Your report</Text>
            <StatusBadge label={readable(fraudCase.data.status)} />
            <Text style={uiStyles.body} selectable>
              Category: {readable(fraudCase.data.category)}
            </Text>
            <Text style={uiStyles.muted} selectable>
              Opened {new Date(fraudCase.data.opened_at).toLocaleString()}
            </Text>
          </AppCard>
          <AppCard>
            <Text style={uiStyles.cardTitle}>Updates</Text>
            {fraudCase.data.timeline.length > 0 ? (
              fraudCase.data.timeline.map((event) => (
                <Text key={event.id} style={uiStyles.body} selectable>
                  • {readable(event.event_type)} ·{" "}
                  {new Date(event.created_at).toLocaleString()}
                </Text>
              ))
            ) : (
              <Text style={uiStyles.muted}>No public status updates yet.</Text>
            )}
          </AppCard>
        </>
      ) : null}
    </ScreenShell>
  );
}
