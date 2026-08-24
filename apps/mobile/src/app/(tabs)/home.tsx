import { router } from "expo-router";
import { Text, View } from "react-native";

import {
  AppButton,
  AppCard,
  ScreenShell,
  StatusBadge,
  uiStyles,
} from "@/components/ui";
import { useAuth } from "@/state/auth-context";

export default function HomeScreen() {
  const { user } = useAuth();
  const firstName = user?.full_name.split(" ")[0] || "there";
  return (
    <ScreenShell
      title={`Hello, ${firstName}`}
      subtitle="Check a screenshot without confusing fraud risk with transaction verification."
    >
      <AppCard>
        <Text style={uiStyles.cardTitle}>Two independent results</Text>
        <View style={uiStyles.stack}>
          <View>
            <StatusBadge label="Fraud risk" tone="warning" />
            <Text style={uiStyles.muted}>
              A model assessment with reasons and a recorded model version.
            </Text>
          </View>
          <View>
            <StatusBadge label="Transaction verification" tone="info" />
            <Text style={uiStyles.muted}>
              A separate comparison against imported reference transactions. It
              is not a live MNO connection.
            </Text>
          </View>
        </View>
        <AppButton
          label="Start a screenshot check"
          onPress={() => router.push("/(tabs)/upload")}
        />
        <AppButton
          label="View check history"
          onPress={() => router.push("/(tabs)/history")}
          variant="secondary"
        />
      </AppCard>
      <AppCard>
        <Text style={uiStyles.cardTitle}>Private by design</Text>
        <Text style={uiStyles.muted}>
          Uploaded screenshots use protected API access and are never exposed
          through a public static URL.
        </Text>
      </AppCard>
    </ScreenShell>
  );
}
