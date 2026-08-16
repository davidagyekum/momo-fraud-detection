# PR19 Security Acceptance

The local security gate is `python scripts/verify_security.py`. It runs 31 backend security scenarios with zero skips, the administrator browser policy, mobile secure-token policy, and the repository secret/prohibited-artifact scan.

Covered boundaries include hostile receipt validation, ownership and assigned-investigator access, role enforcement, refresh/CSRF controls, immutable automated evidence, private report access, audit events, safe API errors, and client-side token persistence policy. Raw images and generated reports are not public static files.

## Dependency advisory B-SEC-002

The administrator production install reports zero known vulnerabilities. The mobile production audit currently reports 24 transitive advisories (9 moderate and 15 high) through Expo/Metro/React Native tooling, principally `image-size`. npm offers only forced, breaking framework downgrades rather than a compatible supported fix. PR19 therefore does not run `npm audit fix --force` or misrepresent this as resolved.

Impact is bounded: the affected tooling executes during controlled development/export, not as an internet-facing server in the mobile runtime image. This is still an open upstream dependency risk. The owner must monitor supported Expo/React Native releases, upgrade when a compatible patched dependency is available, rerun mobile tests/export/audit, and close B-SEC-002 only with recorded evidence.

## Remaining deployment boundary

The acceptance environment is local HTTP. Non-local release still requires HTTPS, external secret management, rate-limit/monitoring verification, a backup/restore rehearsal, and environment-specific penetration and dependency checks.

