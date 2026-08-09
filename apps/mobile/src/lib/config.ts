import { Platform } from "react-native";

const developmentBaseUrl = Platform.select({
  android: "http://10.0.2.2:8000",
  default: "http://localhost:8000",
});

export const API_BASE_URL = (
  process.env.EXPO_PUBLIC_API_URL ?? developmentBaseUrl
).replace(/\/$/, "");
