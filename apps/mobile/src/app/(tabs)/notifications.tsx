import { EmptyState, ScreenShell } from "@/components/ui";

export default function NotificationsScreen() {
  return (
    <ScreenShell
      title="Notifications"
      subtitle="Analysis and review updates for your own transactions will appear here."
    >
      <EmptyState
        title="You are all caught up"
        message="Notification delivery is not connected in P04. No placeholder alerts are shown."
      />
    </ScreenShell>
  );
}
