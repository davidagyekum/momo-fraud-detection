# P03 mobile token-storage contract

This contract applies to the Expo/React Native client implemented from P04 onward.

## Storage rules

- Keep the short-lived access token in application memory. Do not persist it.
- Store the rotated refresh token only with `expo-secure-store`, using a service-specific key.
- Never store access, refresh, reset or CSRF tokens in AsyncStorage, SQLite, application logs,
  analytics payloads, crash reports, screenshots or Redux/query persistence.
- Delete the SecureStore refresh token after logout, refresh-family reuse detection, account
  disablement, password change/reset, or an unrecoverable refresh response.
- Request mobile token responses with `X-Client-Type: mobile`. Browser clients must omit that
  header and use the HTTP-only refresh cookie instead.

## Session lifecycle

1. Login or registration returns an access token, refresh token and CSRF token to the mobile
   client. The mobile client persists only the refresh token.
2. On cold start, the client reads the refresh token from SecureStore and exchanges it for a new
   access/refresh pair. It immediately replaces the stored refresh value after a successful
   rotation.
3. API calls use `Authorization: Bearer <access-token>` from memory. A single coordinated refresh
   may run after an authentication failure; concurrent retries must share that refresh result.
4. Logout sends the refresh token to `/api/v1/auth/logout`, then deletes the SecureStore value even
   if the network request fails.

SecureStore protects device-at-rest storage but does not make a compromised device trustworthy.
Tokens must remain redacted from diagnostics, and the API remains responsible for expiry,
revocation, role validation and object ownership.
