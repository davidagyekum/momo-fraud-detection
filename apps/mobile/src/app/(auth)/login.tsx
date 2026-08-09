import { zodResolver } from "@hookform/resolvers/zod";
import { Link, Redirect, router } from "expo-router";
import { Controller, useForm } from "react-hook-form";
import { Pressable, Text, View } from "react-native";
import { z } from "zod";

import {
  AppButton,
  AppCard,
  InlineAlert,
  LabeledInput,
  PasswordInput,
  ScreenShell,
  uiStyles,
} from "@/components/ui";
import { loginSchema } from "@/lib/validation";
import { useAuth } from "@/state/auth-context";

type LoginValues = z.infer<typeof loginSchema>;

export default function LoginScreen() {
  const { status, login, restoreError, retryRestore } = useAuth();
  const { control, handleSubmit, setError, formState } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });
  if (status === "authenticated") return <Redirect href="/(tabs)/home" />;

  const submit = handleSubmit(async (values) => {
    try {
      await login(values);
      router.replace("/(tabs)/home");
    } catch (error) {
      setError("root", {
        message: error instanceof Error ? error.message : "Sign in failed.",
      });
    }
  });

  return (
    <ScreenShell
      title="Welcome back"
      subtitle="Sign in to review your own MoMo receipt checks."
    >
      {restoreError ? (
        <InlineAlert
          tone="warning"
          title="Session was not restored"
          message={restoreError}
        />
      ) : null}
      {formState.errors.root?.message ? (
        <InlineAlert
          tone="error"
          title="Sign in failed"
          message={formState.errors.root.message}
        />
      ) : null}
      <AppCard>
        <View style={uiStyles.stack}>
          <Controller
            control={control}
            name="email"
            render={({ field, fieldState }) => (
              <LabeledInput
                label="Email"
                value={field.value}
                onChangeText={field.onChange}
                onBlur={field.onBlur}
                error={fieldState.error?.message}
                keyboardType="email-address"
                autoCapitalize="none"
                autoComplete="email"
                returnKeyType="next"
              />
            )}
          />
          <Controller
            control={control}
            name="password"
            render={({ field, fieldState }) => (
              <PasswordInput
                label="Password"
                value={field.value}
                onChangeText={field.onChange}
                onBlur={field.onBlur}
                error={fieldState.error?.message}
                autoComplete="current-password"
                onSubmitEditing={() => void submit()}
              />
            )}
          />
          <AppButton
            label="Sign in"
            onPress={() => void submit()}
            loading={formState.isSubmitting}
          />
        </View>
      </AppCard>
      <Pressable
        accessibilityRole="link"
        onPress={() => router.push("/(auth)/forgot-password")}
        style={{ minHeight: 48, justifyContent: "center" }}
      >
        <Text style={uiStyles.link}>Forgot password?</Text>
      </Pressable>
      {restoreError ? (
        <AppButton
          label="Retry session restore"
          onPress={() => void retryRestore()}
          variant="secondary"
        />
      ) : null}
      <Text style={uiStyles.body}>
        New to MoMo-FDVS?{" "}
        <Link href="/(auth)/register" style={uiStyles.link}>
          Create an account
        </Link>
      </Text>
    </ScreenShell>
  );
}
