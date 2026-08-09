import { zodResolver } from "@hookform/resolvers/zod";
import { Link, Redirect, router } from "expo-router";
import { Controller, useForm } from "react-hook-form";
import { Text, View } from "react-native";
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
import { registerSchema } from "@/lib/validation";
import { useAuth } from "@/state/auth-context";

type Values = z.infer<typeof registerSchema>;

export default function RegisterScreen() {
  const { status, register } = useAuth();
  const { control, handleSubmit, setError, formState } = useForm<Values>({
    resolver: zodResolver(registerSchema),
    defaultValues: { full_name: "", email: "", password: "" },
  });
  if (status === "authenticated") return <Redirect href="/(tabs)/home" />;
  const submit = handleSubmit(async (values) => {
    try {
      await register(values);
      router.replace("/(tabs)/home");
    } catch (error) {
      setError("root", {
        message:
          error instanceof Error ? error.message : "Registration failed.",
      });
    }
  });
  return (
    <ScreenShell
      title="Create account"
      subtitle="Your receipts and reports remain visible only to your account."
    >
      {formState.errors.root?.message ? (
        <InlineAlert
          tone="error"
          title="Could not create account"
          message={formState.errors.root.message}
        />
      ) : null}
      <AppCard>
        <View style={uiStyles.stack}>
          <Controller
            control={control}
            name="full_name"
            render={({ field, fieldState }) => (
              <LabeledInput
                label="Full name"
                value={field.value}
                onChangeText={field.onChange}
                onBlur={field.onBlur}
                error={fieldState.error?.message}
                autoComplete="name"
              />
            )}
          />
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
                hint="At least 12 characters."
                autoComplete="new-password"
              />
            )}
          />
          <AppButton
            label="Create account"
            onPress={() => void submit()}
            loading={formState.isSubmitting}
          />
        </View>
      </AppCard>
      <Text style={uiStyles.body}>
        Already registered?{" "}
        <Link href="/(auth)/login" style={uiStyles.link}>
          Sign in
        </Link>
      </Text>
    </ScreenShell>
  );
}
