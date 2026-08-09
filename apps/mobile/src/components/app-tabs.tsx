import { NativeTabs } from "expo-router/unstable-native-tabs";

import { palette } from "@/theme/tokens";

export default function AppTabs() {
  return (
    <NativeTabs
      backgroundColor={palette.surface}
      indicatorColor={palette.mint}
      iconColor={{ default: palette.muted, selected: palette.forestDark }}
      labelStyle={{
        default: { color: palette.muted },
        selected: { color: palette.forestDark, fontWeight: "700" },
      }}
      labelVisibilityMode="labeled"
      backBehavior="history"
    >
      <NativeTabs.Trigger name="home" accessibilityLabel="Home tab">
        <NativeTabs.Trigger.Label>Home</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon
          sf={{ default: "house", selected: "house.fill" }}
          md="home"
        />
      </NativeTabs.Trigger>
      <NativeTabs.Trigger name="history" accessibilityLabel="History tab">
        <NativeTabs.Trigger.Label>History</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon sf="clock.arrow.circlepath" md="history" />
      </NativeTabs.Trigger>
      <NativeTabs.Trigger name="upload" accessibilityLabel="Upload or scan tab">
        <NativeTabs.Trigger.Label>Scan</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon sf="plus.viewfinder" md="document_scanner" />
      </NativeTabs.Trigger>
      <NativeTabs.Trigger
        name="notifications"
        accessibilityLabel="Notifications tab"
      >
        <NativeTabs.Trigger.Label>Alerts</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon
          sf={{ default: "bell", selected: "bell.fill" }}
          md="notifications"
        />
      </NativeTabs.Trigger>
      <NativeTabs.Trigger name="profile" accessibilityLabel="Profile tab">
        <NativeTabs.Trigger.Label>Profile</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon
          sf={{ default: "person", selected: "person.fill" }}
          md="person"
        />
      </NativeTabs.Trigger>
    </NativeTabs>
  );
}
