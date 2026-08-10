import { fetch } from "expo/fetch";

import { apiRequest, apiResponse } from "@/lib/api";

jest.mock("expo/fetch", () => ({ fetch: jest.fn() }));

const mockedFetch = jest.mocked(fetch);

beforeEach(() => jest.clearAllMocks());

test("adds mobile and authorization headers", async () => {
  mockedFetch.mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => ({ data: { ok: true } }),
  } as never);

  await expect(apiRequest("/api/v1/me", {}, "access-token")).resolves.toEqual({
    data: { ok: true },
  });
  const init = mockedFetch.mock.calls[0]?.[1];
  const headers = new Headers(init?.headers);
  expect(headers.get("X-Client-Type")).toBe("mobile");
  expect(headers.get("Authorization")).toBe("Bearer access-token");
});

test("surfaces the API error code and safe message", async () => {
  mockedFetch.mockResolvedValue({
    ok: false,
    status: 403,
    json: async () => ({
      error: { code: "FORBIDDEN", message: "Not permitted." },
    }),
  } as never);

  await expect(apiRequest("/api/v1/me")).rejects.toMatchObject({
    status: 403,
    code: "FORBIDDEN",
    message: "Not permitted.",
  });
});

test("converts transport failures into an explicit network state", async () => {
  mockedFetch.mockRejectedValue(new TypeError("connection refused"));
  await expect(apiRequest("/api/v1/me")).rejects.toMatchObject({
    status: 0,
    code: "NETWORK",
  });
});

test("lets the runtime set a multipart boundary", async () => {
  mockedFetch.mockResolvedValue({
    ok: true,
    status: 201,
    json: async () => ({ data: { ok: true } }),
  } as never);
  const form = new FormData();
  form.append("source", "GALLERY");

  await apiRequest("/api/v1/transactions", { method: "POST", body: form });
  const headers = new Headers(mockedFetch.mock.calls[0]?.[1]?.headers);
  expect(headers.get("Content-Type")).toBeNull();
});

test("returns a successful binary response without consuming it", async () => {
  const response = {
    ok: true,
    status: 200,
    headers: new Headers({ "Content-Type": "image/jpeg" }),
  } as never;
  mockedFetch.mockResolvedValue(response);
  await expect(
    apiResponse("/api/v1/transactions/id/receipt", {
      headers: { Accept: "image/jpeg" },
    }),
  ).resolves.toBe(response);
});
