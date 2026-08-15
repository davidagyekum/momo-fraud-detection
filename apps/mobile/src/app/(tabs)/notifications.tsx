import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type Href, router } from "expo-router";
import { Text } from "react-native";

import {
  AppButton,
  AppCard,
  EmptyState,
  RetryState,
  ScreenShell,
  SkeletonBlock,
  StatusBadge,
  uiStyles,
} from "@/components/ui";
import {
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from "@/lib/engagement-client";
import { useAuth } from "@/state/auth-context";
import { useIsOnline } from "@/state/network-context";
import type { AppNotification } from "@/types/engagement";

function targetHref(notification: AppNotification): Href | null {
  const target = notification.target;
  if (!target) return null;
  if (target.type === "ANALYSIS") {
    return {
      pathname: "/analysis/[analysisRunId]",
      params: { analysisRunId: target.id },
    } as unknown as Href;
  }
  if (target.type === "TRANSACTION") {
    return {
      pathname: "/transaction/[transactionId]",
      params: { transactionId: target.id },
    } as unknown as Href;
  }
  if (target.type === "CASE") {
    return {
      pathname: "/case/[caseId]",
      params: { caseId: target.id },
    } as unknown as Href;
  }
  return null;
}

export default function NotificationsScreen() {
  const { request } = useAuth();
  const online = useIsOnline();
  const queryClient = useQueryClient();
  const notifications = useQuery({
    queryKey: ["notifications"],
    queryFn: () => listNotifications(request),
    enabled: online,
    staleTime: 10_000,
  });
  const refresh = () =>
    queryClient.invalidateQueries({ queryKey: ["notifications"] });
  const readOne = useMutation({
    mutationFn: (id: string) => markNotificationRead(request, id),
    onSuccess: refresh,
  });
  const readAll = useMutation({
    mutationFn: () => markAllNotificationsRead(request),
    onSuccess: refresh,
  });
  const unread =
    notifications.data?.items.filter((item) => !item.read_at).length ?? 0;
  return (
    <ScreenShell
      title="Notifications"
      subtitle="Analysis and review updates for your own transactions will appear here."
    >
      {notifications.isPending ? (
        <SkeletonBlock label="Loading notifications" />
      ) : notifications.isError ? (
        <RetryState
          message={notifications.error.message}
          onRetry={() => void notifications.refetch()}
        />
      ) : notifications.data?.items.length === 0 ? (
        <EmptyState
          title="You are all caught up"
          message="Analysis and investigation updates will appear here."
        />
      ) : (
        <>
          <AppCard>
            <Text style={uiStyles.cardTitle}>Inbox</Text>
            <StatusBadge
              label={`${unread} unread`}
              tone={unread > 0 ? "warning" : "success"}
            />
            <AppButton
              label="Mark all as read"
              onPress={() => readAll.mutate()}
              disabled={unread === 0 || !online}
              loading={readAll.isPending}
              variant="secondary"
            />
          </AppCard>
          {notifications.data?.items.map((item) => {
            const href = targetHref(item);
            return (
              <AppCard key={item.id}>
                <Text style={uiStyles.cardTitle}>{item.title}</Text>
                {!item.read_at ? (
                  <StatusBadge label="Unread" tone="warning" />
                ) : null}
                <Text style={uiStyles.body} selectable>
                  {item.message}
                </Text>
                <Text style={uiStyles.muted} selectable>
                  {new Date(item.created_at).toLocaleString()}
                </Text>
                {!item.read_at ? (
                  <AppButton
                    label="Mark as read"
                    onPress={() => readOne.mutate(item.id)}
                    loading={readOne.isPending && readOne.variables === item.id}
                    variant="secondary"
                  />
                ) : null}
                {href ? (
                  <AppButton
                    label="Open update"
                    onPress={() => {
                      if (!item.read_at) readOne.mutate(item.id);
                      router.push(href);
                    }}
                    variant="secondary"
                  />
                ) : null}
              </AppCard>
            );
          })}
        </>
      )}
    </ScreenShell>
  );
}
