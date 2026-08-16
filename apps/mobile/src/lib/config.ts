import { Platform } from "react-native";

const developmentBaseUrl = Platform.select({
  android: "http://10.0.2.2:8000",
  default: "http://localhost:8000",
});

export function resolveApiBaseUrl(
  configuredUrl: string | undefined,
  developmentUrl: string,
  isProductionWeb: boolean,
): string {
  return (configuredUrl ?? (isProductionWeb ? "" : developmentUrl)).replace(
    /\/$/,
    "",
  );
}

export const API_BASE_URL = resolveApiBaseUrl(
  process.env.EXPO_PUBLIC_API_URL,
  developmentBaseUrl,
  Platform.OS === "web" && process.env.NODE_ENV === "production",
);
