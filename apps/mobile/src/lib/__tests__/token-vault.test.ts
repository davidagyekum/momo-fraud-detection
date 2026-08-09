import * as SecureStore from "expo-secure-store";

import {
  clearRefreshToken,
  readRefreshToken,
  writeRefreshToken,
} from "@/lib/token-vault";

const secureStore = jest.mocked(SecureStore);

beforeEach(() => {
  jest.clearAllMocks();
  secureStore.isAvailableAsync.mockResolvedValue(true);
});

test("stores only the refresh token in SecureStore", async () => {
  await writeRefreshToken("refresh-secret");

  expect(secureStore.setItemAsync).toHaveBeenCalledWith(
    "momo_fdvs_refresh_token_v1",
    "refresh-secret",
    expect.objectContaining({
      keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
    }),
  );
});

test("reads and clears the secure refresh token", async () => {
  secureStore.getItemAsync.mockResolvedValue("saved-token");
  await expect(readRefreshToken()).resolves.toBe("saved-token");
  await clearRefreshToken();
  expect(secureStore.deleteItemAsync).toHaveBeenCalledWith(
    "momo_fdvs_refresh_token_v1",
  );
});

test("uses memory only when SecureStore is unavailable", async () => {
  secureStore.isAvailableAsync.mockResolvedValue(false);
  await writeRefreshToken("volatile-token");
  await expect(readRefreshToken()).resolves.toBe("volatile-token");
  await clearRefreshToken();
  await expect(readRefreshToken()).resolves.toBeNull();
  expect(secureStore.setItemAsync).not.toHaveBeenCalled();
});
