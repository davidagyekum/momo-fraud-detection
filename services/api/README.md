# MoMo-FDVS API

The Flask application factory exposes the versioned API, PostgreSQL persistence,
private evidence storage, OCR/image evidence services and the governed model registry.

## Structured model registry

P11 artifacts are trained in Google Colab and copied outside Git to
`STRUCTURED_MODEL_ROOT`. Only an active administrator can register, activate or
roll back a version. Registration and every activation verify the SHA-256 before
trusted joblib deserialisation. A model that misses its recorded acceptance gate
is registered as `FAILED` and cannot be activated.

```powershell
python -m flask --app momo_fdvs:create_app model-register-structured `
  --payload .local/model-artifacts/structured/structured_registry_payload.json `
  --actor-email admin@example.test
python -m flask --app momo_fdvs:create_app model-activate-structured `
  --model-id 00000000-0000-0000-0000-000000000000 `
  --actor-email admin@example.test --confirm
python -m flask --app momo_fdvs:create_app model-rollback-structured `
  --model-id 00000000-0000-0000-0000-000000000000 `
  --actor-email admin@example.test --confirm
```

The artifact and payload paths above are examples. Model binaries remain private
and ignored by Git. If no version is active, inference returns
`STRUCTURED_MODEL_NOT_ACTIVE`; it never fabricates a successful prediction.

## Image model registry

P12 uses a separate `IMAGE_MODEL_ROOT` and `private://image/...` URI namespace.
Before any trusted Keras load, the service verifies root containment, size,
SHA-256, the canonical 224×224 RGB preprocessing hash, and input/output shapes.
Registration, activation and rollback use the corresponding
`model-register-image`, `model-activate-image` and `model-rollback-image` commands
and require the same active ADMIN plus explicit confirmation policy.

Until the owner-approved Colab run returns a real `.keras` artifact and the
deployment runtime includes the pinned TensorFlow dependency, image inference
returns an explicit `IMAGE_MODEL_NOT_ACTIVE` or `IMAGE_MODEL_RUNTIME_UNAVAILABLE`
state with a null tamper probability.

Direct dependencies are declared in `pyproject.toml`. Runtime and development
lock files pin the complete tested environment used by Docker and verification.
