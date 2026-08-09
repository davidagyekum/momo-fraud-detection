import { appConfig } from "./config";
import type { ApiEnvelope, ApiErrorBody } from "../types/api";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly requestId: string | null;
  readonly details: Record<string, string[]>;

  constructor(options: {
    status: number;
    code: string;
    message: string;
    requestId?: string | null;
    details?: Record<string, string[]>;
  }) {
    super(options.message);
    this.name = "ApiError";
    this.status = options.status;
    this.code = options.code;
    this.requestId = options.requestId ?? null;
    this.details = options.details ?? {};
  }
}

function buildUrl(path: string): string {
  return `${appConfig.apiBaseUrl}${path.startsWith("/") ? path : `/${path}`}`;
}

async function parseBody(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    return null;
  }
  return response.json() as Promise<unknown>;
}

function errorFromResponse(response: Response, body: unknown): ApiError {
  const candidate = (body ?? {}) as ApiErrorBody;
  return new ApiError({
    status: response.status,
    code: candidate.error?.code ?? "REQUEST_FAILED",
    message:
      candidate.error?.message ??
      (response.status >= 500
        ? "The service is temporarily unavailable."
        : "The request could not be completed."),
    requestId:
      candidate.meta?.request_id ?? response.headers.get("X-Request-ID"),
    details: candidate.error?.details ?? {},
  });
}

export type Fetcher = (
  input: RequestInfo | URL,
  init?: RequestInit,
) => Promise<Response>;

export async function requestEnvelope<T>(
  fetcher: Fetcher,
  path: string,
  init: RequestInit = {},
  accessToken?: string | null,
): Promise<ApiEnvelope<T>> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body !== undefined && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  let response: Response;
  try {
    response = await fetcher(buildUrl(path), {
      ...init,
      credentials: "include",
      headers,
    });
  } catch (error) {
    throw new ApiError({
      status: 0,
      code: "NETWORK_ERROR",
      message:
        error instanceof Error ? error.message : "The network request failed.",
    });
  }

  const body = await parseBody(response);
  if (!response.ok) {
    throw errorFromResponse(response, body);
  }
  return body as ApiEnvelope<T>;
}

export async function requestPrivateFile(
  fetcher: Fetcher,
  path: string,
  accessToken: string,
): Promise<Blob> {
  const response = await fetcher(buildUrl(path), {
    credentials: "include",
    headers: {
      Accept: "application/octet-stream,application/pdf,image/*",
      Authorization: `Bearer ${accessToken}`,
    },
  });
  if (!response.ok) {
    throw errorFromResponse(response, await parseBody(response));
  }
  return response.blob();
}

export function savePrivateFile(blob: Blob, suggestedName: string): void {
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = suggestedName.replace(/[^a-zA-Z0-9._-]/g, "_");
  anchor.rel = "noopener";
  anchor.click();
  URL.revokeObjectURL(objectUrl);
}
