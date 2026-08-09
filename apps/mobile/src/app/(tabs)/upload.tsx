import { Text } from "react-native";

import {
  AppButton,
  AppCard,
  InlineAlert,
  ScreenShell,
  uiStyles,
} from "@/components/ui";

export default function UploadScreen() {
  return (
    <ScreenShell
      title="Upload or scan"
      subtitle="Receipt capture and hostile-file validation arrive in the dedicated upload phase."
    >
      <InlineAlert
        tone="info"
        title="Not active in P04"
        message="No image is selected, uploaded, or analysed from this shell."
      />
      <AppCard>
        <Text style={uiStyles.cardTitle}>Before analysis</Text>
        <Text style={uiStyles.muted}>
          The completed flow will validate extension, decoded image content,
          dimensions and size, then hash the private receipt for duplicate
          checks.
        </Text>
        <AppButton
          label="Camera coming in P06"
          onPress={() => undefined}
          disabled
        />
        <AppButton
          label="Gallery coming in P06"
          onPress={() => undefined}
          disabled
          variant="secondary"
        />
      </AppCard>
    </ScreenShell>
  );
}
