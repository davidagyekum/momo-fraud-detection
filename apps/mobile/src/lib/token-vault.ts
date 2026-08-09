import * as SecureStore from "expo-secure-store";

const REFRESH_STORAGE_SLOT = "momo_fdvs_refresh_token_v1";
let volatileRefreshToken: string | null = null;

async function secureStoreAvailable(): Promise<boolean> {
  return (
    typeof SecureStore.isAvailableAsync === "function" &&
    SecureStore.isAvailableAsync()
  );
}

export async function readRefreshToken(): Promise<string | null> {
  if (await secureStoreAvailable()) {
    return SecureStore.getItemAsync(REFRESH_STORAGE_SLOT);
  }
  return volatileRefreshToken;
}

export async function writeRefreshToken(token: string): Promise<void> {
  if (await secureStoreAvailable()) {
    await SecureStore.setItemAsync(REFRESH_STORAGE_SLOT, token, {
      keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
    });
    return;
  }
  volatileRefreshToken = token;
}

export async function clearRefreshToken(): Promise<void> {
  volatileRefreshToken = null;
  if (await secureStoreAvailable()) {
    await SecureStore.deleteItemAsync(REFRESH_STORAGE_SLOT);
  }
}
