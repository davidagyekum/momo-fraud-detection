# P06 receipt-upload verification evidence

Date: 2026-08-10  
Branch: `codex/p06-receipt-upload`  
Base: `1d7891fd2087a8f5412d864a66dafc939b967a60`

## Implemented boundary

- Expo ImagePicker camera/gallery selection with runtime permission handling.
- Local preview, replace/remove confirmation, format/size guidance and explicit offline/retry states.
- USER-only multipart `POST /api/v1/transactions` with a required idempotency key.
- Strict JPEG/PNG/WebP extension, decode, byte, dimension, pixel, frame and trailing-payload checks that ignore client MIME.
- Byte-identical private original, SHA-256, 64-bit perceptual dHash, quality signals and an EXIF-normalised metadata-stripped JPEG thumbnail.
- Atomic transaction/receipt/derivative/idempotency/audit persistence with cleanup after controlled storage and database failures.
- Owner or ADMIN/INVESTIGATOR private streaming with generated filenames, validated content type, `nosniff` and `private, no-store` caching.

Quality and duplicate signals are not fraud risk and are not transaction-verification results.

## Measured evidence

- Backend: 65 tests passed; 90.16% total coverage; Ruff and strict mypy passed.
- P06 focused hostile/private suite: 17 tests passed.
- Mobile: 37 Jest tests passed; 86.70% statements, 68.25% branches, 88.88% functions and 90.84% lines across security-critical libraries.
- Mobile strict TypeScript, ESLint, Prettier and Expo static web export passed; the private dynamic route was emitted.
- Live local flow created transaction `b71e8ce1-8f37-4ca4-a6a1-24128b951d16` with status `UPLOADED`, then returned a 20,177-byte authenticated JPEG thumbnail with `nosniff` and private no-store caching.
- Chrome exercised registration, authenticated Home navigation and the Start-a-receipt-check transition to `/upload`; meaningful DOM rendered and relevant console warning/error logs were empty.

## Browser evidence limitation

Chrome's `Page.captureScreenshot` command timed out at five seconds on repeated attempts, including after reload and on a different route. DOM, URL, interaction and console evidence succeeded, but no P06 screenshot is claimed. Because the project owner explicitly selected Chrome, no different browser surface was substituted.

## Dependency audit limitation

`npm audit --omit=dev --audit-level=high` reports 8 moderate and 15 high transitive findings in the supported Expo 57/React Native 0.86 toolchain. The high findings trace to `image-size` through Metro; GitHub's reviewed advisories currently list no patched `image-size` release. npm proposes breaking downgrades to Expo 53 or React Native 0.72, so no force-fix was applied. B-SEC-002 records the owner, impact, safe fallback and next action. The API does not use Metro for uploaded receipts and applies its own hostile-image boundary.
