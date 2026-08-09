import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Stack } from "expo-router";
import * as SplashScreen from "expo-splash-screen";
import { useEffect, useState } from "react";
import { StatusBar } from "expo-status-bar";

import { AppErrorBoundary } from "@/components/error-boundary";
import { AuthProvider, useAuth } from "@/state/auth-context";
import { NetworkProvider } from "@/state/network-context";
import { palette } from "@/theme/tokens";

void SplashScreen.preventAutoHideAsync();

function AppNavigator() {
  const { status } = useAuth();
  useEffect(() => {
    if (status !== "restoring") void SplashScreen.hideAsync();
  }, [status]);

  return (
    <>
      <StatusBar style="dark" />
      <Stack
        screenOptions={{
          headerShown: false,
          contentStyle: { backgroundColor: palette.canvas },
        }}
      >
        <Stack.Screen name="index" />
        <Stack.Screen name="(auth)" />
        <Stack.Screen name="(tabs)" />
      </Stack>
    </>
  );
}

export default function RootLayout() {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { retry: 2, staleTime: 30_000 },
          mutations: { retry: 0 },
        },
      }),
  );
  return (
    <AppErrorBoundary>
      <NetworkProvider>
        <QueryClientProvider client={queryClient}>
          <AuthProvider>
            <AppNavigator />
          </AuthProvider>
        </QueryClientProvider>
      </NetworkProvider>
    </AppErrorBoundary>
  );
}
