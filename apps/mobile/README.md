# MoMo-FDVS mobile application

Expo SDK 57, React Native and TypeScript client for end users. P04 implements the secure authentication lifecycle, profile management, accessible UI states and five-tab shell. P06 adds private receipt capture, preview, upload and protected-preview reopening. P07 adds the OCR review and correction workflow. History and notifications remain inactive until their owning phases.

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

## Receipt capture and privacy

- Camera permission is requested when the camera action is chosen; gallery permission is requested only when the gallery action is chosen.
- JPEG, PNG and WebP images up to 10 MB are accepted. Client checks improve feedback, but the API independently validates all untrusted bytes.
- Multipart boundaries are set by the native/web runtime. Every retry reuses the selection's idempotency key.
- Protected thumbnails are fetched with the in-memory access token and represented only as an in-memory preview URI. Raw object keys and other users' duplicate details are never exposed.
- Image-quality and duplicate notices are not fraud results and are not transaction-verification results.

## OCR review

- A successful upload opens an owner-only OCR review route. The client first reuses an existing OCR result and otherwise starts one request with a stable idempotency key.
- The private receipt preview can be enlarged. Extracted fields remain editable and show plain-language confidence and validation guidance.
- Every changed field requires a reason before confirmation. The server preserves the original OCR result and creates a separate immutable confirmation record.
- Offline, loading, retry, partial-OCR, permission-denied and confirmation states are explicit.
- OCR extracts receipt text only. It does not prove authenticity, query a mobile-network operator, determine transaction verification or assign fraud risk.
