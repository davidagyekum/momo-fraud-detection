import { Redirect } from "expo-router";
import { ActivityIndicator, Text, View } from "react-native";

import { useAuth } from "@/state/auth-context";
import { palette, spacing, typeScale } from "@/theme/tokens";

export default function SessionGate() {
  const { status } = useAuth();
  if (status === "authenticated") return <Redirect href="/(tabs)/home" />;
  if (status === "signed-out") return <Redirect href="/(auth)/login" />;
  return (
    <View
      accessibilityLabel="Restoring your secure session"
      style={{
        flex: 1,
        alignItems: "center",
        justifyContent: "center",
        gap: spacing.md,
        backgroundColor: palette.canvas,
      }}
    >
      <View
        style={{
          width: 72,
          height: 72,
          borderRadius: 24,
          backgroundColor: palette.forest,
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <Text
          style={{
            color: palette.surface,
            fontSize: typeScale.title,
            fontWeight: "900",
          }}
        >
          MF
        </Text>
      </View>
      <Text
        style={{
          color: palette.ink,
          fontSize: typeScale.title,
          fontWeight: "800",
        }}
      >
        MoMo-FDVS
      </Text>
      <ActivityIndicator color={palette.forest} />
    </View>
  );
}
