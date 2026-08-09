# Security and private-data policy

MoMo-FDVS processes potentially sensitive financial evidence. Treat receipts, OCR output, reference transactions, user profiles, case notes, authentication material, and private datasets as restricted or confidential data.

## Do not commit

- real receipt images or unmasked transaction/reference data;
- `.env` files, passwords, access/refresh/reset tokens, or private keys;
- database, storage, email, notification, or monitoring credentials;
- private/raw datasets or unapproved personal identifiers;
- large model artifacts such as `.keras`, `.joblib`, `.pkl`, or `.h5` files;
- reports, screenshots, or logs containing personal information.

Use `.env.example`, safe synthetic fixtures, private storage, and documented artifact hashes instead.

## Reporting a suspected issue

Do not place secrets, live credentials, exploit payloads, or private receipts in a public issue. Contact the project owner through an approved private channel and include only the minimum safe reproduction information: affected revision, component, impact, and redacted steps.

If a credential may have been exposed, revoke or rotate it first, preserve relevant audit evidence, and then investigate the repository history and affected services.

## Current deployment state

No deployment exists during P00. Security claims must be supported by test or deployment evidence at an exact commit SHA. The complete security requirements are in `08_SECURITY_PRIVACY_AUDIT_SPEC.md`.

