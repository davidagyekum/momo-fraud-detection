import { router } from "expo-router";

import { EmptyState, ScreenShell } from "@/components/ui";

export default function HistoryScreen() {
  return (
    <ScreenShell
      title="Your history"
      subtitle="Only transactions owned by your account will appear here."
    >
      <EmptyState
        title="No receipt checks yet"
        message="History retrieval is introduced in the transactions phase. This shell does not fabricate sample results."
        actionLabel="Start a receipt check"
        onAction={() => router.push("/(tabs)/upload")}
      />
    </ScreenShell>
  );
}
