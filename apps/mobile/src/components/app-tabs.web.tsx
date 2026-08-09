import { Slot, usePathname, useRouter } from "expo-router";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { minTouchTarget, palette, spacing, typeScale } from "@/theme/tokens";

const tabs = [
  { name: "home", title: "Home", glyph: "⌂" },
  { name: "history", title: "History", glyph: "↶" },
  { name: "upload", title: "Scan", glyph: "+" },
  { name: "notifications", title: "Alerts", glyph: "!" },
  { name: "profile", title: "Profile", glyph: "○" },
] as const;

export default function AppTabsWeb() {
  const pathname = usePathname();
  const router = useRouter();
  return (
    <View style={styles.shell}>
      <View style={styles.content}>
        <Slot />
      </View>
      <View role="tablist" aria-label="Main" style={styles.tabBar}>
        {tabs.map((tab) => {
          const selected =
            pathname.endsWith(`/${tab.name}`) || pathname === `/${tab.name}`;
          return (
            <Pressable
              key={tab.name}
              accessibilityRole="tab"
              accessibilityLabel={`${tab.title} tab`}
              accessibilityState={{ selected }}
              onPress={() => router.replace(`/(tabs)/${tab.name}`)}
              style={({ pressed }) => [styles.tab, pressed && styles.pressed]}
            >
              <Text
                aria-hidden
                style={[styles.glyph, selected && styles.selected]}
              >
                {tab.glyph}
              </Text>
              <Text style={[styles.label, selected && styles.selected]}>
                {tab.title}
              </Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  shell: { flex: 1, minHeight: 0, backgroundColor: palette.canvas },
  content: { flex: 1, minHeight: 0 },
  tabBar: {
    minHeight: 64,
    flexDirection: "row",
    backgroundColor: palette.surface,
    borderTopColor: palette.border,
    borderTopWidth: 1,
  },
  tab: {
    flex: 1,
    minWidth: 0,
    minHeight: minTouchTarget,
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: spacing.xs,
  },
  glyph: {
    color: palette.muted,
    fontSize: typeScale.title,
    lineHeight: 26,
    fontWeight: "800",
  },
  label: {
    color: palette.muted,
    fontSize: 11,
    lineHeight: 14,
    fontWeight: "700",
  },
  selected: { color: palette.forestDark },
  pressed: { backgroundColor: palette.mint },
});
