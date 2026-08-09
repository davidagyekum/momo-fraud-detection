import { Redirect } from "expo-router";

import AppTabs from "@/components/app-tabs";
import { useAuth } from "@/state/auth-context";

export default function TabsLayout() {
  const { status } = useAuth();
  if (status === "restoring") return <Redirect href="/" />;
  if (status !== "authenticated") return <Redirect href="/(auth)/login" />;
  return <AppTabs />;
}
