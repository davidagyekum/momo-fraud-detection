import { afterEach, describe, expect, it, vi } from "vitest";
import { requestEnvelope, requestPrivateFile, savePrivateFile } from "./api";
import type { ApiError, Fetcher } from "./api";
import { envelope, jsonResponse } from "../test/responses";

describe("requestEnvelope", () => {
  it("adds credentials and an in-memory bearer token", async () => {
    const fetcher = vi.fn(() =>
      Promise.resolve(jsonResponse(envelope({ ok: true }))),
    ) as Fetcher;
    const result = await requestEnvelope<{ ok: boolean }>(
      fetcher,
      "/me",
      { method: "GET" },
      "access-test-only",
    );
    expect(result.data.ok).toBe(true);
    const call = vi.mocked(fetcher).mock.calls[0];
    expect(call?.[0]).toBe("/api/v1/me");
    expect(call?.[1]?.credentials).toBe("include");
    expect(new Headers(call?.[1]?.headers).get("Authorization")).toBe(
      "Bearer access-test-only",
    );
  });

  it("maps safe API errors with the request id", async () => {
    const fetcher = vi.fn(() =>
      Promise.resolve(
        jsonResponse(
          {
            error: { code: "NO_ACCESS", message: "Access denied." },
            meta: { request_id: "request-denied" },
          },
          403,
        ),
      ),
    ) as Fetcher;
    await expect(
      requestEnvelope(fetcher, "/admin/users"),
    ).rejects.toMatchObject({
      status: 403,
      code: "NO_ACCESS",
      requestId: "request-denied",
    } satisfies Partial<ApiError>);
  });

  it("maps transport failures without leaking implementation details", async () => {
    const fetcher = vi.fn(() =>
      Promise.reject(new TypeError("offline")),
    ) as Fetcher;
    await expect(requestEnvelope(fetcher, "/me")).rejects.toMatchObject({
      status: 0,
      code: "NETWORK_ERROR",
    } satisfies Partial<ApiError>);
  });

  it("uses a generic message for non-JSON server failures", async () => {
    const fetcher = vi.fn(() =>
      Promise.resolve(new Response("gateway", { status: 502 })),
    ) as Fetcher;
    await expect(requestEnvelope(fetcher, "/ready")).rejects.toMatchObject({
      status: 502,
      code: "REQUEST_FAILED",
      message: "The service is temporarily unavailable.",
    } satisfies Partial<ApiError>);
  });
});

describe("private file handling", () => {
  afterEach(() => vi.restoreAllMocks());

  it("requests private bytes with the access token", async () => {
    const fetcher = vi.fn(() =>
      Promise.resolve(new Response("safe", { status: 200 })),
    ) as Fetcher;
    const blob = await requestPrivateFile(
      fetcher,
      "/reports/id/download",
      "token-test",
    );
    expect(await blob.text()).toBe("safe");
    const init = vi.mocked(fetcher).mock.calls[0]?.[1];
    expect(new Headers(init?.headers).get("Authorization")).toBe(
      "Bearer token-test",
    );
  });

  it("generates a safe browser download filename", () => {
    const createObjectURL = vi
      .spyOn(URL, "createObjectURL")
      .mockReturnValue("blob:test");
    const revokeObjectURL = vi
      .spyOn(URL, "revokeObjectURL")
      .mockImplementation(() => undefined);
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => undefined);
    const createElement = vi.spyOn(document, "createElement");
    savePrivateFile(new Blob(["safe"]), "../unsafe report.pdf");
    const anchor = createElement.mock.results.find(
      (result) => result.value instanceof HTMLAnchorElement,
    )?.value as HTMLAnchorElement | undefined;
    expect(anchor?.download).toBe(".._unsafe_report.pdf");
    expect(click).toHaveBeenCalledOnce();
    expect(createObjectURL).toHaveBeenCalledOnce();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:test");
  });

  it("rejects unauthorised private bytes", async () => {
    const fetcher = vi.fn(() =>
      Promise.resolve(
        jsonResponse({ error: { code: "NO_ACCESS", message: "Denied." } }, 403),
      ),
    ) as Fetcher;
    await expect(
      requestPrivateFile(fetcher, "/reports/id/download", "token-test"),
    ).rejects.toMatchObject({ status: 403, code: "NO_ACCESS" });
  });
});
