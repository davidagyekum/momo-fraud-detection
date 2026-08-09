const configuredBase = import.meta.env.VITE_API_BASE_URL?.trim() || "/api/v1";

if (
  !configuredBase.startsWith("/") &&
  !configuredBase.startsWith("http://") &&
  !configuredBase.startsWith("https://")
) {
  throw new Error(
    "VITE_API_BASE_URL must be an absolute URL or root-relative path.",
  );
}

export const appConfig = Object.freeze({
  apiBaseUrl: configuredBase.replace(/\/$/, ""),
  environment: import.meta.env.VITE_APP_ENVIRONMENT?.trim() || "Local",
});
