import { apiRequest, ApiError } from "@/lib/api";
import { AuthSessionManager } from "@/lib/auth-session";
import {
  clearRefreshToken,
  readRefreshToken,
  writeRefreshToken,
} from "@/lib/token-vault";
import type { Envelope, SessionData } from "@/types/api";

jest.mock("@/lib/api", () => ({
  apiRequest: jest.fn(),
  ApiError: class MockApiError extends Error {
    readonly status: number;
    readonly code: string;

    constructor(
      message: string,
      mockStatus: number,
      mockCode = "REQUEST_FAILED",
    ) {
      super(message);
      this.status = mockStatus;
      this.code = mockCode;
    }
  },
}));
jest.mock("@/lib/token-vault");

const mockedApi = jest.mocked(apiRequest);
const mockedRead = jest.mocked(readRefreshToken);
const mockedWrite = jest.mocked(writeRefreshToken);
const mockedClear = jest.mocked(clearRefreshToken);
const session: Envelope<SessionData> = {
  data: {
    access_token: "fixture-access-token",
    refresh_token: "fixture-refresh-token",
    csrf_token: null,
    expires_in: 900,
    user: {
      id: "00000000-0000-4000-8000-000000000001",
      email: "ama@example.test",
      full_name: "Ama Mensah",
      phone_e164: null,
      roles: ["USER"],
      status: "ACTIVE",
      must_change_password: false,
    },
  },
  meta: {},
};

beforeEach(() => jest.clearAllMocks());

test("auth smoke stores the refresh token after login", async () => {
  mockedApi.mockResolvedValue(session);
  const manager = new AuthSessionManager();

  await expect(
    manager.login({ email: "ama@example.test", password: "secret" }),
  ).resolves.toEqual(session.data.user);
  expect(mockedApi).toHaveBeenCalledWith(
    "/api/v1/auth/login",
    expect.objectContaining({ method: "POST" }),
  );
  expect(mockedWrite).toHaveBeenCalledWith("fixture-refresh-token");
});

test("coalesces concurrent session restoration", async () => {
  mockedRead.mockResolvedValue("stored-refresh");
  mockedApi.mockResolvedValue(session);
  const manager = new AuthSessionManager();

  const [first, second] = await Promise.all([
    manager.restore(),
    manager.restore(),
  ]);
  expect(first).toEqual(session.data.user);
  expect(second).toEqual(session.data.user);
  expect(mockedApi).toHaveBeenCalledTimes(1);
});

test("returns signed out when there is no stored refresh token", async () => {
  mockedRead.mockResolvedValue(null);
  await expect(new AuthSessionManager().restore()).resolves.toBeNull();
  expect(mockedApi).not.toHaveBeenCalled();
});

test("refreshes once and retries an authorized request after 401", async () => {
  mockedRead.mockResolvedValue("stored-refresh");
  mockedApi
    .mockResolvedValueOnce(session)
    .mockRejectedValueOnce(new ApiError("Expired access", 401))
    .mockResolvedValueOnce(session)
    .mockResolvedValueOnce({ data: { ok: true }, meta: {} });
  const manager = new AuthSessionManager();
  await manager.login({ email: "ama@example.test", password: "secret" });

  await expect(manager.authorizedRequest("/api/v1/me")).resolves.toEqual({
    data: { ok: true },
    meta: {},
  });
  expect(mockedApi).toHaveBeenCalledTimes(4);
});

test("logout without a stored token remains local", async () => {
  mockedRead.mockResolvedValue(null);
  await new AuthSessionManager().logout();
  expect(mockedApi).not.toHaveBeenCalled();
  expect(mockedClear).toHaveBeenCalled();
});

test("reports a partial session instead of faking success", async () => {
  mockedApi.mockResolvedValue({
    ...session,
    data: { ...session.data, refresh_token: null },
  });
  const manager = new AuthSessionManager();

  await expect(
    manager.login({ email: "ama@example.test", password: "secret" }),
  ).rejects.toMatchObject({ code: "PARTIAL_SESSION" });
});

test("clears an invalid stored session", async () => {
  mockedRead.mockResolvedValue("expired-refresh");
  mockedApi.mockRejectedValue(new ApiError("Expired", 401));
  const manager = new AuthSessionManager();

  await expect(manager.restore()).rejects.toThrow("Expired");
  expect(mockedClear).toHaveBeenCalled();
});

test("clears local state even when remote logout fails", async () => {
  mockedRead.mockResolvedValue("stored-refresh");
  mockedApi.mockRejectedValue(new ApiError("Offline", 0));
  const manager = new AuthSessionManager();

  await expect(manager.logout()).rejects.toThrow("Offline");
  expect(mockedClear).toHaveBeenCalled();
});
