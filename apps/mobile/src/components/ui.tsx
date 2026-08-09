import { Image } from "expo-image";
import {
  type ComponentProps,
  type PropsWithChildren,
  useId,
  useState,
} from "react";
import {
  ActivityIndicator,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  type TextInputProps,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useIsOnline } from "@/state/network-context";
import {
  minTouchTarget,
  palette,
  radius,
  spacing,
  typeScale,
} from "@/theme/tokens";

export function ScreenShell({
  children,
  title,
  subtitle,
}: PropsWithChildren<{ title: string; subtitle?: string }>) {
  const insets = useSafeAreaInsets();
  const online = useIsOnline();
  return (
    <ScrollView
      contentInsetAdjustmentBehavior="automatic"
      automaticallyAdjustKeyboardInsets
      keyboardShouldPersistTaps="handled"
      style={styles.screen}
      contentContainerStyle={{
        paddingTop: Math.max(insets.top, spacing.lg),
        paddingBottom: Math.max(insets.bottom, spacing.xxl),
        paddingHorizontal: spacing.lg,
        gap: spacing.md,
      }}
    >
      {!online && (
        <InlineAlert
          tone="warning"
          title="You are offline"
          message="Reconnect to submit or refresh information."
        />
      )}
      <View style={{ gap: spacing.sm }}>
        <Text accessibilityRole="header" style={styles.title} allowFontScaling>
          {title}
        </Text>
        {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
      </View>
      {children}
    </ScrollView>
  );
}

export function AppButton({
  label,
  onPress,
  loading = false,
  disabled = false,
  variant = "primary",
}: {
  label: string;
  onPress: () => void;
  loading?: boolean;
  disabled?: boolean;
  variant?: "primary" | "secondary" | "danger";
}) {
  const backgroundColor =
    variant === "primary"
      ? palette.forest
      : variant === "danger"
        ? palette.red
        : palette.surface;
  const color = variant === "secondary" ? palette.forestDark : palette.surface;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ busy: loading, disabled: disabled || loading }}
      disabled={disabled || loading}
      onPress={onPress}
      style={({ pressed }) => [
        styles.button,
        {
          backgroundColor,
          borderColor:
            variant === "secondary" ? palette.forest : backgroundColor,
        },
        pressed && styles.pressed,
        (disabled || loading) && styles.disabled,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={color} />
      ) : (
        <Text style={[styles.buttonText, { color }]}>{label}</Text>
      )}
    </Pressable>
  );
}

export function LabeledInput({
  label,
  error,
  hint,
  ...props
}: TextInputProps & {
  label: string;
  error?: string | undefined;
  hint?: string | undefined;
}) {
  const inputId = useId();
  return (
    <View style={{ gap: spacing.xs }}>
      <Text nativeID={`${inputId}-label`} style={styles.label}>
        {label}
      </Text>
      <TextInput
        {...props}
        accessibilityLabel={label}
        accessibilityHint={hint}
        aria-labelledby={`${inputId}-label`}
        style={[styles.input, error ? styles.inputError : null, props.style]}
        placeholderTextColor={palette.muted}
      />
      {error ? (
        <Text accessibilityLiveRegion="polite" style={styles.errorText}>
          {error}
        </Text>
      ) : hint ? (
        <Text style={styles.hint}>{hint}</Text>
      ) : null}
    </View>
  );
}

export function PasswordInput(
  props: Omit<ComponentProps<typeof LabeledInput>, "secureTextEntry">,
) {
  const [visible, setVisible] = useState(false);
  return (
    <View style={{ gap: spacing.xs }}>
      <LabeledInput
        {...props}
        secureTextEntry={!visible}
        autoCapitalize="none"
      />
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={visible ? "Hide password" : "Show password"}
        onPress={() => setVisible((value) => !value)}
        style={styles.textAction}
      >
        <Text style={styles.link}>
          {visible ? "Hide password" : "Show password"}
        </Text>
      </Pressable>
    </View>
  );
}

export function AppCard({ children }: PropsWithChildren) {
  return <View style={styles.card}>{children}</View>;
}

export function InlineAlert({
  tone,
  title,
  message,
}: {
  tone: "info" | "warning" | "error";
  title: string;
  message: string;
}) {
  const colors =
    tone === "error"
      ? [palette.redSoft, palette.red]
      : tone === "warning"
        ? [palette.amberSoft, palette.amber]
        : [palette.blueSoft, palette.blue];
  return (
    <View
      accessibilityRole="alert"
      style={[
        styles.alert,
        { backgroundColor: colors[0], borderColor: colors[1] },
      ]}
    >
      <Text style={[styles.alertTitle, { color: colors[1] }]}>{title}</Text>
      <Text style={{ color: palette.ink }}>{message}</Text>
    </View>
  );
}

export function StatusBadge({
  label,
  tone = "info",
}: {
  label: string;
  tone?: "info" | "success" | "warning";
}) {
  const backgroundColor =
    tone === "success"
      ? palette.mint
      : tone === "warning"
        ? palette.amberSoft
        : palette.blueSoft;
  return (
    <View
      accessibilityLabel={`Status: ${label}`}
      style={[styles.badge, { backgroundColor }]}
    >
      <Text style={styles.badgeText}>● {label}</Text>
    </View>
  );
}

export function SkeletonBlock({ label = "Loading" }: { label?: string }) {
  return (
    <View
      accessibilityLabel={label}
      accessibilityRole="progressbar"
      style={styles.skeleton}
    />
  );
}

export function EmptyState({
  title,
  message,
  actionLabel,
  onAction,
}: {
  title: string;
  message: string;
  actionLabel?: string;
  onAction?: () => void;
}) {
  return (
    <AppCard>
      <Text style={styles.cardTitle}>{title}</Text>
      <Text style={styles.subtitle}>{message}</Text>
      {actionLabel && onAction ? (
        <AppButton label={actionLabel} onPress={onAction} variant="secondary" />
      ) : null}
    </AppCard>
  );
}

export function RetryState({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <AppCard>
      <InlineAlert tone="error" title="Could not load" message={message} />
      <AppButton label="Retry" onPress={onRetry} variant="secondary" />
    </AppCard>
  );
}

export function ConfirmationDialog({
  visible,
  title,
  message,
  confirmLabel,
  destructive = false,
  onConfirm,
  onCancel,
}: {
  visible: boolean;
  title: string;
  message: string;
  confirmLabel: string;
  destructive?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={onCancel}
    >
      <View style={styles.modalBackdrop}>
        <View accessibilityViewIsModal style={styles.modal}>
          <Text accessibilityRole="header" style={styles.cardTitle}>
            {title}
          </Text>
          <Text style={styles.subtitle}>{message}</Text>
          <AppButton
            label={confirmLabel}
            onPress={onConfirm}
            variant={destructive ? "danger" : "primary"}
          />
          <AppButton label="Cancel" onPress={onCancel} variant="secondary" />
        </View>
      </View>
    </Modal>
  );
}

export function SecureImagePreview({
  authorizedUri,
  accessibilityLabel,
}: {
  authorizedUri?: string;
  accessibilityLabel: string;
}) {
  if (!authorizedUri)
    return (
      <EmptyState
        title="Private image unavailable"
        message="The protected receipt preview could not be loaded."
      />
    );
  return (
    <Image
      source={{ uri: authorizedUri }}
      accessibilityLabel={accessibilityLabel}
      style={{ width: "100%", aspectRatio: 0.75, borderRadius: radius.md }}
      contentFit="contain"
    />
  );
}

export const uiStyles = StyleSheet.create({
  stack: { gap: spacing.md },
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    flexWrap: "wrap",
  },
  link: {
    color: palette.forestDark,
    fontSize: typeScale.body,
    fontWeight: "700",
  },
  body: { color: palette.ink, fontSize: typeScale.body, lineHeight: 24 },
  muted: { color: palette.muted, fontSize: typeScale.body, lineHeight: 24 },
  cardTitle: {
    color: palette.ink,
    fontSize: 19,
    lineHeight: 26,
    fontWeight: "700",
  },
});

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: palette.canvas },
  title: {
    color: palette.ink,
    fontSize: typeScale.display,
    lineHeight: 42,
    fontWeight: "800",
  },
  subtitle: { color: palette.muted, fontSize: typeScale.body, lineHeight: 24 },
  button: {
    minHeight: minTouchTarget,
    borderRadius: radius.md,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  buttonText: { fontSize: typeScale.body, fontWeight: "700" },
  pressed: { opacity: 0.78 },
  disabled: { opacity: 0.48 },
  label: { color: palette.ink, fontSize: typeScale.body, fontWeight: "700" },
  input: {
    minHeight: minTouchTarget,
    borderWidth: 1,
    borderColor: palette.border,
    borderRadius: radius.sm,
    backgroundColor: palette.surface,
    color: palette.ink,
    fontSize: typeScale.body,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  inputError: { borderColor: palette.red, borderWidth: 2 },
  errorText: { color: palette.red, fontSize: typeScale.caption },
  hint: { color: palette.muted, fontSize: typeScale.caption },
  textAction: {
    minHeight: minTouchTarget,
    alignSelf: "flex-start",
    justifyContent: "center",
  },
  link: {
    color: palette.forestDark,
    fontSize: typeScale.body,
    fontWeight: "700",
  },
  card: {
    backgroundColor: palette.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: palette.border,
    padding: spacing.lg,
    gap: spacing.md,
  },
  cardTitle: {
    color: palette.ink,
    fontSize: 19,
    lineHeight: 26,
    fontWeight: "700",
  },
  alert: {
    borderWidth: 1,
    borderRadius: radius.md,
    padding: spacing.md,
    gap: spacing.xs,
  },
  alertTitle: { fontSize: typeScale.body, fontWeight: "800" },
  badge: {
    alignSelf: "flex-start",
    borderRadius: radius.pill,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
  },
  badgeText: { color: palette.ink, fontWeight: "700" },
  skeleton: {
    height: 96,
    borderRadius: radius.md,
    backgroundColor: palette.border,
  },
  modalBackdrop: {
    flex: 1,
    justifyContent: "center",
    padding: spacing.lg,
    backgroundColor: "rgba(3, 14, 9, 0.62)",
  },
  modal: {
    backgroundColor: palette.surface,
    borderRadius: radius.lg,
    padding: spacing.lg,
    gap: spacing.md,
  },
});
