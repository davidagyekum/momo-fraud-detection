import { useQuery } from "@tanstack/react-query";
import { type Href, Redirect, router, useLocalSearchParams } from "expo-router";
import { Text } from "react-native";

import {
  AppButton,
  AppCard,
  InlineAlert,
  RetryState,
  ScreenShell,
  SecureImagePreview,
  SkeletonBlock,
  StatusBadge,
  uiStyles,
} from "@/components/ui";
import { fetchPrivateThumbnail } from "@/lib/receipt-client";
import { useAuth } from "@/state/auth-context";

export default function PrivateReceiptScreen() {
  const { transactionId } = useLocalSearchParams<{ transactionId: string }>();
  const { response, status } = useAuth();
  const validId = typeof transactionId === "string" && transactionId.length > 0;
  const preview = useQuery({
    queryKey: ["private-receipt", transactionId],
    queryFn: () => fetchPrivateThumbnail(response, transactionId ?? ""),
    enabled: validId && status === "authenticated",
    staleTime: 0,
    gcTime: 0,
    retry: 1,
  });

  if (status === "restoring") {
    return (
      <ScreenShell title="Private receipt">
        <SkeletonBlock label="Restoring secure session" />
      </ScreenShell>
    );
  }
  if (status !== "authenticated") return <Redirect href="/(auth)/login" />;

  return (
    <ScreenShell
      title="Private receipt"
      subtitle="This protected preview is fetched only after the API checks your session and ownership."
    >
      {!validId ? (
        <InlineAlert
          tone="error"
          title="Receipt unavailable"
          message="The receipt link is invalid. Return to uploads and try again."
        />
      ) : preview.isPending ? (
        <AppCard>
          <SkeletonBlock label="Loading private receipt" />
          <Text style={uiStyles.muted}>
            Authorising and loading the private preview…
          </Text>
        </AppCard>
      ) : preview.isError ? (
        <RetryState
          message={preview.error.message}
          onRetry={() => void preview.refetch()}
        />
      ) : (
        <AppCard>
          <StatusBadge label="Private evidence" tone="success" />
          <SecureImagePreview
            authorizedUri={preview.data}
            accessibilityLabel="Private uploaded receipt"
          />
          <InlineAlert
            tone="info"
            title="Upload complete"
            message="This is a protected thumbnail. OCR and fraud analysis are separate later steps."
          />
        </AppCard>
      )}
      <AppButton
        label="Review extracted details"
        onPress={() =>
          router.push({
            pathname: "/ocr/[transactionId]",
            params: { transactionId },
          } as unknown as Href)
        }
        disabled={!validId}
      />
      <AppButton
        label="Back to upload"
        onPress={() => router.back()}
        variant="secondary"
      />
    </ScreenShell>
  );
}
