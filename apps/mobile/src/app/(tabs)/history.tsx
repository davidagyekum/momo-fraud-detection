import { useQuery } from "@tanstack/react-query";
import { type Href, router } from "expo-router";
import { useState } from "react";
import { View } from "react-native";

import { TransactionHistoryView } from "@/components/transaction-history";
import { AppButton, ScreenShell, uiStyles } from "@/components/ui";
import { listTransactions } from "@/lib/history-client";
import { useAuth } from "@/state/auth-context";
import { useIsOnline } from "@/state/network-context";
import type { RiskBand } from "@/types/analysis";

export default function HistoryScreen() {
  const { request } = useAuth();
  const online = useIsOnline();
  const [band, setBand] = useState<RiskBand | undefined>();
  const [page, setPage] = useState(1);
  const selectBand = (nextBand: RiskBand | undefined) => {
    setPage(1);
    setBand(nextBand);
  };
  const history = useQuery({
    queryKey: ["transaction-history", page, band],
    queryFn: () => listTransactions(request, { page, page_size: 20, band }),
    enabled: online,
    staleTime: 0,
    retry: 1,
  });
  return (
    <ScreenShell
      title="Your history"
      subtitle="Only transactions owned by your account appear here."
    >
      <View style={uiStyles.row}>
        <AppButton
          label="All checks"
          onPress={() => selectBand(undefined)}
          variant={band === undefined ? "primary" : "secondary"}
        />
        <AppButton
          label="High risk"
          onPress={() => selectBand("high_risk")}
          variant={band === "high_risk" ? "primary" : "secondary"}
        />
        <AppButton
          label="Inconclusive"
          onPress={() => selectBand("inconclusive")}
          variant={band === "inconclusive" ? "primary" : "secondary"}
        />
      </View>
      <TransactionHistoryView
        items={history.data?.items ?? []}
        pending={online && history.isPending}
        error={history.isError ? history.error.message : null}
        onRetry={() => void history.refetch()}
        onOpen={(transactionId) =>
          router.push({
            pathname: "/transaction/[transactionId]",
            params: { transactionId },
          } as unknown as Href)
        }
      />
      {history.data && history.data.total_pages > 1 ? (
        <View style={uiStyles.row}>
          <AppButton
            label="Previous page"
            onPress={() => setPage((value) => Math.max(1, value - 1))}
            disabled={page === 1}
            variant="secondary"
          />
          <AppButton
            label="Next page"
            onPress={() =>
              setPage((value) => Math.min(history.data.total_pages, value + 1))
            }
            disabled={page >= history.data.total_pages}
            variant="secondary"
          />
        </View>
      ) : null}
      <AppButton
        label="Start a receipt check"
        onPress={() => router.push("/(tabs)/upload")}
      />
    </ScreenShell>
  );
}
