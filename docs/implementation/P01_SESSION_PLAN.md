# P01 session plan

Base: merged P00 commit `41741877cce2a2efd69240c77707c55a7961bd0f`  
Branch: `codex/p01-api-infrastructure`

1. Establish only the specified monorepo boundaries; defer UI, auth, receipt and ML features to their phases.
2. Implement the Flask factory and versioned system contract with safe request correlation, errors, logging and CORS.
3. Add PostgreSQL readiness, an empty Alembic baseline, Docker Compose and a Tesseract-equipped non-root API image.
4. Generate and drift-check OpenAPI from schemas, then run formatting, lint, typing, tests and repository security checks.
5. Record any host-tool blocker honestly before publishing the P01 review branch.

