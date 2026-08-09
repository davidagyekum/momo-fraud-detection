# P04 Session Plan — Mobile Shell and Authentication

- Base: `main` at `3a4f4ea50df3aacdedf6094e3108c453fca092cc`
- Branch: `codex/p04-mobile-shell`
- Scope: P04-T001 through P04-T010 only

## Plan

1. Scaffold an Expo Router + React Native + TypeScript application with Node 22/npm 10 pins,
   strict TypeScript, ESLint, tests and repository verification integration.
2. Implement reusable semantic tokens and accessible primitives for screens, forms, status,
   loading, empty, retry, confirmation and private-image placeholders.
3. Implement the auth stack and authenticated five-tab shell: restore, login, register,
   forgot/reset password, home, history, upload placeholder, notifications and profile.
4. Implement typed API errors, React Query, network awareness, coordinated token refresh and
   Expo SecureStore refresh-token persistence with access tokens held in memory only.
5. Verify form accessibility, offline/error/session-expiry behavior, responsive Android layout,
   component tests, auth smoke tests, Expo export/startup and prohibited-token-storage checks.

No camera/gallery upload, receipt persistence, OCR, analysis, notification backend, history
backend or staff portal behavior is included in P04. Those routes show honest empty/not-yet-
available states until their owning phases.
