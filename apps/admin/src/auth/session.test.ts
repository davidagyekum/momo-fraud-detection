import { afterEach, describe, expect, it, vi } from "vitest";
import type { Fetcher } from "../lib/api";
import { ApiError } from "../lib/api";
import { adminSession, envelope, jsonResponse } from "../test/responses";
import { PortalSession } from "./session";

function requestUrl(input: RequestInfo | URL): string {
  if (typeof input === "string") return input;
  return input instanceof URL ? input.href : input.url;
}

describe("PortalSession", () => {
  afterEach(() => vi.restoreAllMocks());

  it("stays anonymous when no readable CSRF session cookie exists", async () => {
    const fetcher = vi.fn() as unknown as Fetcher;
    const session = new PortalSession(fetcher, () => "");
    await session.restore();
    expect(session.getSnapshot()).toEqual({
      phase: "anonymous",
      user: null,
      message: null,
    });
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("signs in without requesting a browser-readable refresh token", async () => {
    const fetcher = vi.fn(() =>
      Promise.resolve(jsonResponse(envelope(adminSession))),
    ) as Fetcher;
    const session = new PortalSession(
      fetcher,
      () => "momo_fdvs_csrf=csrf-test",
    );
    const user = await session.signIn("ada@example.test", "password-test-only");
    expect(user.roles).toEqual(["ADMIN"]);
    expect(session.getSnapshot().phase).toBe("authenticated");
    const [url, init] = vi.mocked(fetcher).mock.calls[0] ?? [];
    expect(url).toBe("/api/v1/auth/login");
    expect(new Headers(init?.headers).has("X-Client-Type")).toBe(false);
  });

  it("restores with the double-submit CSRF header", async () => {
    const fetcher = vi.fn(() =>
      Promise.resolve(jsonResponse(envelope(adminSession))),
    ) as Fetcher;
    const session = new PortalSession(
      fetcher,
      () => "momo_fdvs_csrf=bound%2Bcsrf",
    );
    await session.restore();
    const init = vi.mocked(fetcher).mock.calls[0]?.[1];
    expect(new Headers(init?.headers).get("X-CSRF-Token")).toBe("bound+csrf");
    expect(session.getSnapshot().user?.email).toBe("ada@example.test");
  });

  it("coordinates one refresh for concurrent protected requests", async () => {
    let refreshCount = 0;
    const fetcher = vi.fn(async (input: RequestInfo | URL) => {
      const url = requestUrl(input);
      if (url.endsWith("/auth/refresh")) {
        refreshCount += 1;
        await Promise.resolve();
        return jsonResponse(envelope(adminSession));
      }
      return jsonResponse(envelope({ path: url }));
    }) as Fetcher;
    const session = new PortalSession(
      fetcher,
      () => "momo_fdvs_csrf=csrf-test",
    );
    const [first, second] = await Promise.all([
      session.request<{ path: string }>("/first"),
      session.request<{ path: string }>("/second"),
    ]);
    expect(refreshCount).toBe(1);
    expect(first.data.path).toBe("/api/v1/first");
    expect(second.data.path).toBe("/api/v1/second");
  });

  it("rotates and retries a protected request once after 401", async () => {
    let protectedCalls = 0;
    const refreshed = {
      ...adminSession,
      access_token: "rotated-access-test-only",
    };
    const fetcher = vi.fn((input: RequestInfo | URL) => {
      const url = requestUrl(input);
      if (url.endsWith("/auth/login"))
        return Promise.resolve(jsonResponse(envelope(adminSession)));
      if (url.endsWith("/auth/refresh"))
        return Promise.resolve(jsonResponse(envelope(refreshed)));
      protectedCalls += 1;
      return Promise.resolve(
        protectedCalls === 1
          ? jsonResponse(
              { error: { code: "TOKEN_EXPIRED", message: "Expired." } },
              401,
            )
          : jsonResponse(envelope({ ok: true })),
      );
    }) as Fetcher;
    const session = new PortalSession(
      fetcher,
      () => "momo_fdvs_csrf=csrf-test",
    );
    await session.signIn("ada@example.test", "password-test-only");
    const result = await session.request<{ ok: boolean }>("/me");
    expect(result.data.ok).toBe(true);
    const protectedHeaders = vi
      .mocked(fetcher)
      .mock.calls.filter(([url]) => requestUrl(url).endsWith("/me"))
      .map(([, init]) => new Headers(init?.headers).get("Authorization"));
    expect(protectedHeaders).toEqual([
      "Bearer access-token-for-test-only",
      "Bearer rotated-access-test-only",
    ]);
  });

  it("expires the client session when refresh fails", async () => {
    const fetcher = vi.fn(() =>
      Promise.resolve(
        jsonResponse(
          { error: { code: "SESSION_REVOKED", message: "Revoked." } },
          401,
        ),
      ),
    ) as Fetcher;
    const session = new PortalSession(
      fetcher,
      () => "momo_fdvs_csrf=csrf-test",
    );
    await expect(session.request("/me")).rejects.toBeInstanceOf(ApiError);
    expect(session.getSnapshot()).toMatchObject({
      phase: "expired",
      user: null,
    });
  });

  it("sends CSRF on logout and clears memory even when the request fails", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(envelope(adminSession)))
      .mockResolvedValueOnce(
        jsonResponse(
          { error: { code: "NETWORK", message: "Unavailable." } },
          503,
        ),
      ) as Fetcher;
    const session = new PortalSession(
      fetcher,
      () => "momo_fdvs_csrf=csrf-test",
    );
    await session.signIn("ada@example.test", "password-test-only");
    await expect(session.signOut()).rejects.toBeInstanceOf(ApiError);
    expect(session.getSnapshot().phase).toBe("anonymous");
    const logoutInit = vi.mocked(fetcher).mock.calls[1]?.[1];
    expect(new Headers(logoutInit?.headers).get("X-CSRF-Token")).toBe(
      "csrf-test",
    );
  });

  it("notifies active subscribers and supports a successful protected request and logout", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(envelope(adminSession)))
      .mockResolvedValueOnce(jsonResponse(envelope({ ok: true })))
      .mockResolvedValueOnce(
        jsonResponse(envelope({ accepted: true })),
      ) as Fetcher;
    const session = new PortalSession(
      fetcher,
      () => "momo_fdvs_csrf=csrf-test",
    );
    const listener = vi.fn();
    const unsubscribe = session.subscribe(listener);
    await session.signIn("ada@example.test", "password-test-only");
    expect(session.accessTokenForDownload()).toBe("access-token-for-test-only");
    expect((await session.request<{ ok: boolean }>("/me")).data.ok).toBe(true);
    await session.signOut();
    expect(session.getSnapshot().phase).toBe("anonymous");
    expect(listener).toHaveBeenCalledTimes(2);
    unsubscribe();
  });

  it("rejects private downloads without a current access token", () => {
    const session = new PortalSession(vi.fn(), () => "");
    expect(() => session.accessTokenForDownload()).toThrow(ApiError);
  });

  it("downloads private evidence only after bearer authentication", async () => {
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:private");
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => undefined);
    const fetcher = vi.fn((input: RequestInfo | URL) => {
      const url = requestUrl(input);
      return Promise.resolve(
        url.endsWith("/auth/login")
          ? jsonResponse(envelope(adminSession))
          : new Response("private-report", { status: 200 }),
      );
    }) as Fetcher;
    const session = new PortalSession(
      fetcher,
      () => "momo_fdvs_csrf=csrf-test",
    );
    await session.signIn("ada@example.test", "password-test-only");
    await session.download("/reports/id/download", "case-report.pdf");
    expect(click).toHaveBeenCalledOnce();
    const downloadInit = vi.mocked(fetcher).mock.calls[1]?.[1];
    expect(new Headers(downloadInit?.headers).get("Authorization")).toBe(
      "Bearer access-token-for-test-only",
    );
  });
});
