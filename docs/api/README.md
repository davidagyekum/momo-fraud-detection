# API contract workflow

The committed contract is `packages/api-client/openapi.json`. It is generated from the registered Flask-Smorest schemas:

```powershell
py -3.12 scripts/export_openapi.py
py -3.12 scripts/export_openapi.py --check
```

Do not edit the JSON snapshot manually. Client-visible changes must update schemas, regenerate this document, update generated consumers and add contract tests.

