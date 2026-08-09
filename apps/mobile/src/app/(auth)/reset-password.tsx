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
  PasswordInput,
  ScreenShell,
  uiStyles,
} from "@/components/ui";
import { apiRequest } from "@/lib/api";
import { resetPasswordSchema } from "@/lib/validation";

type Values = z.infer<typeof resetPasswordSchema>;

export default function ResetPasswordScreen() {
  const { control, handleSubmit, setError, formState } = useForm<Values>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: { token: "", new_password: "" },
  });
  const submit = handleSubmit(async (values) => {
    try {
      await apiRequest("/api/v1/auth/reset-password", {
        method: "POST",
        body: JSON.stringify(values),
      });
    } catch (error) {
      setError("root", {
        message: error instanceof Error ? error.message : "Reset failed.",
      });
    }
  });
  return (
    <ScreenShell
      title="Choose new password"
      subtitle="Reset tokens are sensitive. They are sent only to the API and never stored on this device."
    >
      {formState.isSubmitSuccessful ? (
        <InlineAlert
          tone="info"
          title="Password changed"
          message="You can now sign in with your new password."
        />
      ) : null}
      {formState.errors.root?.message ? (
        <InlineAlert
          tone="error"
          title="Could not reset password"
          message={formState.errors.root.message}
        />
      ) : null}
      <AppCard>
        <View style={uiStyles.stack}>
          <Controller
            control={control}
            name="token"
            render={({ field, fieldState }) => (
              <LabeledInput
                label="Reset token"
                value={field.value}
                onChangeText={field.onChange}
                onBlur={field.onBlur}
                error={fieldState.error?.message}
                autoCapitalize="none"
              />
            )}
          />
          <Controller
            control={control}
            name="new_password"
            render={({ field, fieldState }) => (
              <PasswordInput
                label="New password"
                value={field.value}
                onChangeText={field.onChange}
                onBlur={field.onBlur}
                error={fieldState.error?.message}
                autoComplete="new-password"
              />
            )}
          />
          <AppButton
            label="Change password"
            onPress={() => void submit()}
            loading={formState.isSubmitting}
          />
        </View>
      </AppCard>
      <Text style={uiStyles.body}>
        <Link href="/(auth)/login" style={uiStyles.link}>
          Return to sign in
        </Link>
      </Text>
    </ScreenShell>
  );
}
