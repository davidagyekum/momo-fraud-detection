import type { SessionData } from "../types/api";

export const adminSession: SessionData = {
  access_token: "access-token-for-test-only",
  refresh_token: null,
  csrf_token: null,
  expires_in: 900,
  user: {
    id: "00000000-0000-4000-8000-000000000001",
    full_name: "Ada Admin",
    email: "ada@example.test",
    roles: ["ADMIN"],
    status: "ACTIVE",
  },
};

export function jsonResponse(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json",
      "X-Request-ID": "request-test",
    },
  });
}

export function envelope(data: unknown): unknown {
  return { data, meta: { request_id: "request-test" } };
}
