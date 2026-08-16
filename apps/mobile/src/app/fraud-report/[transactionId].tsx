import { useMutation } from "@tanstack/react-query";
import { type Href, Redirect, router, useLocalSearchParams } from "expo-router";
import { useRef, useState } from "react";
import { Text } from "react-native";

import {
  AppButton,
  AppCard,
  InlineAlert,
  LabeledInput,
  ScreenShell,
  SkeletonBlock,
  uiStyles,
} from "@/components/ui";
import {
  createEngagementKey,
  createFraudReport,
} from "@/lib/engagement-client";
import { useAuth } from "@/state/auth-context";
import { useIsOnline } from "@/state/network-context";

const categories = [
  ["PAYMENT_NOT_RECEIVED", "Payment not received"],
  ["UNKNOWN_TRANSACTION", "Unknown transaction"],
  ["ALTERED_RECEIPT", "Receipt may be altered"],
  ["OTHER", "Other concern"],
] as const;

export default function FraudReportScreen() {
  const { transactionId } = useLocalSearchParams<{ transactionId: string }>();
  const { request, status } = useAuth();
  const online = useIsOnline();
  const key = useRef(createEngagementKey("case"));
  const [category, setCategory] = useState<string>("PAYMENT_NOT_RECEIVED");
  const [description, setDescription] = useState("");
  const validId = typeof transactionId === "string" && transactionId.length > 0;
  const submission = useMutation({
    mutationFn: () =>
      createFraudReport(request, transactionId ?? "", key.current, {
        category,
        ...(description.trim() ? { description: description.trim() } : {}),
      }),
    onSuccess: (fraudCase) =>
      router.replace({
        pathname: "/case/[caseId]",
        params: { caseId: fraudCase.id },
      } as unknown as Href),
  });

  if (status === "restoring") {
    return (
      <ScreenShell title="Report transaction">
        <SkeletonBlock label="Restoring secure session" />
      </ScreenShell>
    );
  }
  if (status !== "authenticated") return <Redirect href="/(auth)/login" />;
  return (
    <ScreenShell
      title="Report transaction"
      subtitle="Send this analysed transaction to the investigation queue. Your automated result will remain unchanged."
    >
      {!validId ? (
        <InlineAlert
          tone="error"
          title="Transaction unavailable"
          message="This transaction link is invalid."
        />
      ) : (
        <AppCard>
          <Text style={uiStyles.cardTitle}>What concerns you?</Text>
          {categories.map(([value, label]) => (
            <AppButton
              key={value}
              label={`${category === value ? "Selected: " : ""}${label}`}
              onPress={() => setCategory(value)}
              variant={category === value ? "primary" : "secondary"}
            />
          ))}
          <LabeledInput
            label="Additional details (optional)"
            value={description}
            onChangeText={setDescription}
            multiline
            maxLength={4000}
            hint="Do not include PINs, OTPs or passwords."
          />
          {submission.isError ? (
            <InlineAlert
              tone="error"
              title="Could not submit report"
              message={submission.error.message}
            />
          ) : null}
          <AppButton
            label="Submit for investigation"
            onPress={() => submission.mutate()}
            loading={submission.isPending}
            disabled={!online || !validId}
          />
        </AppCard>
      )}
    </ScreenShell>
  );
}
