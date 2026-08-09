import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { router } from "expo-router";
import { useEffect, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { Text, View } from "react-native";
import { z } from "zod";

import {
  AppButton,
  AppCard,
  ConfirmationDialog,
  InlineAlert,
  LabeledInput,
  RetryState,
  ScreenShell,
  SkeletonBlock,
  StatusBadge,
  uiStyles,
} from "@/components/ui";
import { profileSchema } from "@/lib/validation";
import { useAuth } from "@/state/auth-context";
import type { Envelope, User } from "@/types/api";

type Values = z.infer<typeof profileSchema>;

export default function ProfileScreen() {
  const auth = useAuth();
  const queryClient = useQueryClient();
  const [confirmLogout, setConfirmLogout] = useState(false);
  const profile = useQuery({
    queryKey: ["me"],
    queryFn: () => auth.request<Envelope<User>>("/api/v1/me"),
  });
  const { control, handleSubmit, reset, setError, formState } = useForm<Values>(
    {
      resolver: zodResolver(profileSchema),
      defaultValues: {
        full_name: auth.user?.full_name ?? "",
        phone_e164: auth.user?.phone_e164 ?? "",
      },
    },
  );

  useEffect(() => {
    if (profile.data?.data)
      reset({
        full_name: profile.data.data.full_name,
        phone_e164: profile.data.data.phone_e164 ?? "",
      });
  }, [profile.data, reset]);

  const updateProfile = useMutation({
    mutationFn: (values: Values) =>
      auth.request<Envelope<User>>("/api/v1/me", {
        method: "PATCH",
        body: JSON.stringify({
          full_name: values.full_name,
          phone_e164: values.phone_e164 || null,
        }),
      }),
    onSuccess: (response) => {
      auth.updateUser(response.data);
      queryClient.setQueryData(["me"], response);
    },
    onError: (error) =>
      setError("root", {
        message:
          error instanceof Error ? error.message : "Profile update failed.",
      }),
  });

  const logout = async () => {
    setConfirmLogout(false);
    try {
      await auth.logout();
    } finally {
      router.replace("/(auth)/login");
    }
  };

  return (
    <ScreenShell
      title="Profile"
      subtitle="Manage your account and secure session."
    >
      {profile.isLoading ? (
        <>
          <SkeletonBlock />
          <SkeletonBlock />
        </>
      ) : profile.isError ? (
        <RetryState
          message={profile.error.message}
          onRetry={() => void profile.refetch()}
        />
      ) : null}
      {profile.data ? (
        <>
          <AppCard>
            <View style={uiStyles.row}>
              <StatusBadge label={profile.data.data.status} tone="success" />
              <Text style={uiStyles.muted}>{profile.data.data.email}</Text>
            </View>
            <Text style={uiStyles.muted}>
              Roles: {profile.data.data.roles.join(", ")}
            </Text>
          </AppCard>
          {formState.errors.root?.message ? (
            <InlineAlert
              tone="error"
              title="Could not save profile"
              message={formState.errors.root.message}
            />
          ) : null}
          {updateProfile.isSuccess ? (
            <InlineAlert
              tone="info"
              title="Profile saved"
              message="Your account details are up to date."
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
                name="phone_e164"
                render={({ field, fieldState }) => (
                  <LabeledInput
                    label="Phone (optional)"
                    value={field.value}
                    onChangeText={field.onChange}
                    onBlur={field.onBlur}
                    error={fieldState.error?.message}
                    keyboardType="phone-pad"
                    hint="International format, for example +233241234567."
                  />
                )}
              />
              <AppButton
                label="Save profile"
                onPress={() =>
                  void handleSubmit((values) => updateProfile.mutate(values))()
                }
                loading={updateProfile.isPending}
              />
            </View>
          </AppCard>
        </>
      ) : null}
      <AppButton
        label="Sign out"
        onPress={() => setConfirmLogout(true)}
        variant="danger"
      />
      <ConfirmationDialog
        visible={confirmLogout}
        title="Sign out?"
        message="The refresh token will be revoked where possible and removed from secure device storage."
        confirmLabel="Sign out"
        destructive
        onConfirm={() => void logout()}
        onCancel={() => setConfirmLogout(false)}
      />
    </ScreenShell>
  );
}
