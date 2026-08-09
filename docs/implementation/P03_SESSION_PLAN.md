# P03 Session Plan — Authentication, Ownership and RBAC

- Base: `main` at `0fa8d463eb74ef0f93597fb7cb13647a94ce83fa`
- Branch: `codex/p03-auth-rbac`
- Scope: P03-T001 through P03-T011 only

## Plan

1. Implement adaptive password hashing, short-lived signed access tokens, rotated hashed refresh sessions, reset-token hashing and non-enumerating auth services.
2. Add registration/login/refresh/logout/reset/current-user endpoints with secure web cookies, CSRF validation and configured rate limits.
3. Add central role/capability and transaction-ownership policies, followed by protected admin user-management endpoints.
4. Emit safe append-only authentication/privileged audit events and document the Expo SecureStore mobile token contract.
5. Generate OpenAPI, cover happy/expired/revoked/altered/role/IDOR/rate-limit/cookie-CSRF cases, and run PostgreSQL/Docker gates.

No receipt upload, OCR, model, case, dashboard or UI behaviour is included in P03.
