# P05 Session Plan

## Scope lock

- Phase: P05 — administrator and investigator web portal shell
- Branch: `codex/p05-admin-shell`
- Base: merged P04 commit `9e7594bb79ecd5805f3417d617fcef4c011669dd`
- Prerequisite: P03 authentication/RBAC API is complete; P04 is merged as PR #5.
- Requirement focus: `FR-AUTH-003`, client portions of `FR-ADM-001`, `FR-ADM-005`, `FR-ADM-006`, `FR-ADM-007`, `NFR-SEC-002`, `NFR-USE-002`, and `NFR-COMP-001`.

P05 creates the secure, role-aware portal workspace and reusable web UI foundation. It does not implement dashboard aggregates, transaction/case workflows, registries, imports, reports, audit search, or system readiness owned by P08/P15/P16. Those routes must identify themselves as inactive or empty rather than fabricate data.

## Implementation plan

1. Scaffold a pinned React, TypeScript and Vite app with React Router, TanStack Query, React Hook Form and Zod.
2. Implement a memory-only access-token session with secure HTTP-only refresh-cookie rotation, double-submit CSRF support, coordinated refresh, one retry after 401, session expiry and logout.
3. Add route-level staff and permission guards. ADMIN receives the full shell; INVESTIGATOR receives Dashboard, Transactions, Cases, Reports and Profile/Security only.
4. Build the visual system from the accepted P05 concepts and implement reusable tables, filters, pagination, dialogs, drawers, forms, semantic badges, chart containers, skeletons, empty/error/permission states and authenticated downloads.
5. Add every required shell route plus no-access, not-found and global-error routes without crossing into later feature behavior.
6. Add unit/component coverage, role/session tests, a real local API browser smoke, responsive/keyboard QA and production build verification.
7. Register P05 verification in repository scripts/CI, update traceability/status/evidence, then commit, push and merge through a reviewed pull request.

## Planned verification

- Prettier, ESLint and strict TypeScript
- Vitest unit/component tests with coverage
- Production Vite build
- Portal token-storage/secret policy
- Backend regression and migration drift check
- Browser login/session/logout smoke against the local test API
- ADMIN and INVESTIGATOR navigation/permission checks
- Keyboard/focus and 1280x720, 1366x768, 1440x900 and 768x1024 responsive checks
- Concept-to-render comparison using the saved design references

