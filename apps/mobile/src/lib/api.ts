import { fetch } from "expo/fetch";

import { API_BASE_URL } from "@/lib/config";
import type { ErrorEnvelope } from "@/types/api";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code = "REQUEST_FAILED",
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function getErrorMessage(
  payload: ErrorEnvelope | null,
  status: number,
): string {
  return (
    payload?.error?.message ?? payload?.message ?? `Request failed (${status})`
  );
}

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
  accessToken?: string,
): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15_000);
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  headers.set("X-Client-Type", "mobile");
  if (init.body) headers.set("Content-Type", "application/json");
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers,
      signal: controller.signal,
    });
    const payload = (await response.json().catch(() => null)) as
      T | ErrorEnvelope | null;
    if (!response.ok) {
      const error = payload as ErrorEnvelope | null;
      throw new ApiError(
        getErrorMessage(error, response.status),
        response.status,
        error?.error?.code,
      );
    }
    return payload as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error instanceof Error && error.name === "AbortError") {
      throw new ApiError(
        "The request timed out. Check your connection and retry.",
        0,
        "TIMEOUT",
      );
    }
    throw new ApiError(
      "Unable to reach MoMo-FDVS. Check your connection and retry.",
      0,
      "NETWORK",
    );
  } finally {
    clearTimeout(timeout);
  }
}
