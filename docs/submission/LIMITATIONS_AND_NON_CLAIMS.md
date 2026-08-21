# Final Limitations and Non-Claims

This document is part of the final academic submission record. It prevents local prototype evidence from being restated as deployment, provider confirmation, model generalisation or full-specification completion.

## Submission classification

- The artifact is a locally verified academic prototype submission candidate.
- It is not certified, production-ready, production-deployed, regulator-approved or suitable for consequential decisions without authorised human/provider review.
- Packaging completion does not retroactively complete outstanding product requirements. At freeze time, traceability records `89 / 108` MUST and `6 / 12` SHOULD requirements complete.

## Hosted deployment and CI

- No hosted, staging or production deployment exists or is claimed. Accepted runtime evidence is local HTTP Docker Compose only.
- Non-local HTTPS, managed secrets, external monitoring/rate-limit evidence, hosted smoke tests and production rollback were not demonstrated.
- GitHub Actions jobs could not obtain hosted runners because of the recorded account/billing lock (`B-CI-001`). The workflows remain in the repository, but hosted CI is unverified.
- A clean local four-service release, migration head and readiness probe are evidence of local reproducibility only.

## Mobile and browser compatibility

- The accepted mobile journey uses the Expo web export in a Chromium-based local browser.
- Responsive evidence exists at 360x800, 390x844, 768x1024 and 1440x900.
- Final native Android and iOS device automation was not performed. Camera/gallery permissions, secure storage and physical-device networking therefore have implementation/test evidence but not a final native-device acceptance run.
- A complete evergreen Chrome/Edge/Firefox/Safari compatibility matrix was not executed.
- The host Node/npm versions used by some final frontend gates differ from the repository pins; exact pinned Docker builds remain the stronger build evidence where recorded.

## Transaction verification

- Verification uses authorised stored/imported reference records only.
- There is no live MTN, Telecel, AT Money, bank or other MNO/provider integration.
- `VERIFIED` means that confirmed fields matched a stored/imported record under the versioned prototype comparison policy. It does not mean an operator confirmed settlement.
- `UNVERIFIED` or `NOT_ATTEMPTED` is not evidence of fraud. A `MISMATCH` is separate evidence and does not overwrite the fraud-risk result.

## Image and structured models

- The P12 controlled image model failed its configured acceptance threshold: held-out macro F1 was `0.333333` against a minimum of `0.85`. Its artifact remains uncommitted, inactive and unavailable; no tamper probability is fabricated.
- Deterministic recompression, residual, metadata, duplicate and layout signals are supporting evidence, not proof that an image was manipulated.
- The P11 structured pipeline passed a tiny controlled-synthetic held-out set of three rows. That is pipeline-correctness evidence, not provider-wide accuracy, calibration or production generalisation.
- The current accepted release reports image and structured classifiers as not activated and `full_analysis_available=false`. Partial/degraded component state is preserved honestly.
- No model was trained, promoted or activated during P0.1-P0.3, P1 or this submission freeze.

## Data and evaluation

- Real/supervisor-approved representative receipt data and a production reference source were not supplied.
- Controlled and synthetic data do not cover all real Ghanaian Mobile Money providers, devices, message layouts or fraud techniques.
- The controlled OCR result of 20/20 declared fields across five fixtures is not a provider-wide 100% accuracy claim.
- Locked-test partitions remained sealed and unavailable for the final completion and freeze. No locked-test metric is claimed.
- The controlled-real suspicious class lacks enough independent groups for representative leakage-safe validation/test slices.
- No broadly approved tampered-image derivative slice exists for representative OCR/image robustness evaluation.

## Performance, recovery and dependency evidence

- Formal p50/p95 load evidence, the 25-concurrent-analysis target and the 100,000-record scalability target remain unproven.
- A non-production backup/restore rehearsal was not completed, although backup/rollback procedures are documented.
- Mobile production audit evidence retains `B-SEC-002`: 9 moderate and 15 high transitive Expo/Metro/React Native toolchain advisories. The repository does not apply npm's breaking forced downgrade.
- Local security and ownership gates passed at the recorded accepted SHA, but no external penetration test or non-local environment assessment is claimed.

## Remaining product-scope gaps

The status table keeps P14-P19 in review because original scope items remain partial, including:

- explicit history date-range filtering;
- complete user/template/rule management UI and automatic high-risk case creation;
- complete audit/analytics filtering;
- formal performance/load evidence;
- native-device and multi-browser acceptance;
- hosted HTTPS deployment and restore rehearsal.

These gaps do not invalidate the demonstrated OCR-first academic prototype, but they must remain visible to an examiner and cannot be described as completed implementation.

## Appropriate conclusion

The defensible conclusion is: **the repository contains a working, locally tested, evidence-preserving academic prototype whose primary screenshot-risk journey is submission-ready within the stated boundaries.** It does not establish live provider verification, production readiness, representative model accuracy or completion of every original requirement.
