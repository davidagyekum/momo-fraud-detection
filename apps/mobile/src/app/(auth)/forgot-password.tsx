import { zodResolver } from "@hookform/resolvers/zod";
import { Link } from "expo-router";
import { Controller, useForm } from "react-hook-form";
import { Text, View } from "react-native";
import { z } from "zod";

import {
  AppButton,
  AppCard,
  InlineAlert,
  LabeledInput,
  ScreenShell,
  uiStyles,
} from "@/components/ui";
import { apiRequest } from "@/lib/api";
import { forgotPasswordSchema } from "@/lib/validation";

type Values = z.infer<typeof forgotPasswordSchema>;

export default function ForgotPasswordScreen() {
  const { control, handleSubmit, setError, formState } = useForm<Values>({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: { email: "" },
  });
  const submit = handleSubmit(async (values) => {
    try {
      await apiRequest("/api/v1/auth/forgot-password", {
        method: "POST",
        body: JSON.stringify(values),
      });
    } catch (error) {
      setError("root", {
        message: error instanceof Error ? error.message : "Request failed.",
      });
    }
  });
  return (
    <ScreenShell
      title="Reset password"
      subtitle="If the account exists, the API will accept the request without revealing account status."
    >
      {formState.isSubmitSuccessful ? (
        <InlineAlert
          tone="info"
          title="Request accepted"
          message="Check your configured reset delivery channel. In local development, ask the API operator for the test token."
        />
      ) : null}
      {formState.errors.root?.message ? (
        <InlineAlert
          tone="error"
          title="Could not submit request"
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
              />
            )}
          />
          <AppButton
            label="Request reset"
            onPress={() => void submit()}
            loading={formState.isSubmitting}
          />
        </View>
      </AppCard>
      <Text style={uiStyles.body}>
        <Link href="/(auth)/reset-password" style={uiStyles.link}>
          I have a reset token
        </Link>
      </Text>
      <Text style={uiStyles.body}>
        <Link href="/(auth)/login" style={uiStyles.link}>
          Back to sign in
        </Link>
      </Text>
    </ScreenShell>
  );
}
