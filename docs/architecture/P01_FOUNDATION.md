# P01 architecture foundation

The API process uses an application factory and unbound Flask extensions. Versioned controllers expose schema-backed responses under `/api/v1`; request hooks attach a UUID correlation ID and structured safe logging; dependency probes are isolated from response construction. SQLAlchemy owns the request-scoped session, and the error teardown rolls back failed units of work.

Core readiness requires PostgreSQL and private storage. OCR and both model slots are reported separately as analysis capabilities so a missing later-phase artifact never becomes a false healthy result.

