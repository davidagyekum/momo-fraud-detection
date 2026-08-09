# MoMo-FDVS API

P01 provides the Flask application factory, versioned system endpoints, generated OpenAPI contract, PostgreSQL readiness probe, structured logging, strict CORS and Alembic baseline.

Domain models and protected product endpoints begin in P02 and P03.

Direct dependencies are declared in `pyproject.toml`. `requirements-runtime.lock` and `requirements-dev.lock` pin the fully resolved P01 environments used by Docker and local verification.
