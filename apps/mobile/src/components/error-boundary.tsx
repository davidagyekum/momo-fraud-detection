import { Component, type ErrorInfo, type PropsWithChildren } from "react";
import { Text, View } from "react-native";

import { AppButton } from "@/components/ui";
import { palette, spacing, typeScale } from "@/theme/tokens";

type State = { failed: boolean };

export class AppErrorBoundary extends Component<PropsWithChildren, State> {
  state: State = { failed: false };

  static getDerivedStateFromError(): State {
    return { failed: true };
  }

  componentDidCatch(_error: Error, _info: ErrorInfo) {
    // Production telemetry is introduced with the observability phase.
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <View
        style={{
          flex: 1,
          justifyContent: "center",
          padding: spacing.lg,
          backgroundColor: palette.canvas,
        }}
      >
        <Text
          accessibilityRole="header"
          style={{
            fontSize: typeScale.title,
            fontWeight: "700",
            color: palette.ink,
          }}
        >
          MoMo-FDVS needs a restart
        </Text>
        <Text
          style={{
            marginVertical: spacing.md,
            fontSize: typeScale.body,
            color: palette.muted,
          }}
        >
          An unexpected app error occurred. Your receipt data was not submitted.
        </Text>
        <AppButton
          label="Try again"
          onPress={() => this.setState({ failed: false })}
        />
      </View>
    );
  }
}
