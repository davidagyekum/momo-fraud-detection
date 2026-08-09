# MoMo-FDVS mobile application

Expo SDK 57, React Native and TypeScript client for end users. P04 implements the secure authentication lifecycle, profile management, accessible UI states and the five-tab application shell. Receipt capture, history retrieval and notifications are deliberately labelled inactive until their owning phases.

## Runtime and configuration

- Node.js `24.14.0` and npm `10.9.0` are mandatory.
- Copy `.env.example` to an ignored `.env` only when the API is not reachable at the development default.
- Android Emulator defaults to `http://10.0.2.2:8000`; other development targets default to `http://localhost:8000`.
- `EXPO_PUBLIC_API_URL` is a public build-time value. Never place credentials or secrets in any `EXPO_PUBLIC_*` variable.

## Commands

```text
npm install
npm run start
npm run lint
npm run typecheck
npm run test:ci
npm run build:web
```

## Session security

The access token exists only in process memory. The rotating mobile refresh token is stored through Expo SecureStore using device-only accessibility and is deleted on logout or rejected restoration. On platforms where SecureStore is unavailable, the refresh token falls back to volatile process memory rather than browser or unencrypted persistent storage.

The API must return a refresh token for a mobile session. If it does not, the client reports an explicit partial-session error and does not claim a successful sign-in.
