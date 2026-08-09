# MoMo-FDVS staff portal

React, TypeScript and Vite workspace for authorised administrators and investigators.

P05 implements the secure session lifecycle, role-aware application shell, reusable component foundation and honest inactive routes. Operational dashboards and staff workflows are implemented only in their owning later phases.

## Runtime

- Node.js `24.14.0`
- npm `10.9.0`

## Development

```text
npm install
npm run dev
npm run verify
```

The development server proxies `/api` to `http://localhost:8000`. `VITE_API_BASE_URL` is public build configuration and must never contain credentials or secrets.

## Browser session security

The access token is held only in memory. The rotating refresh credential remains in a secure HTTP-only cookie. The readable CSRF cookie is sent back as `X-CSRF-Token` for refresh/logout requests. No token is stored in local storage, session storage, IndexedDB or a browser-readable persistent store.
