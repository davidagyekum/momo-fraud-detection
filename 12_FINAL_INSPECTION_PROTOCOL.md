# 12 — Final Independent Inspection Protocol

## 1. Purpose

This protocol defines the handoff from Codex implementation to an independent repository inspection. It prevents a vague “finished” claim and makes the repair loop efficient.

An inspection is performed against an **exact pushed commit SHA**. A branch name alone is insufficient because it can move.

## 2. Owner handoff

Provide:

- GitHub repository in `owner/repository` form;
- target branch;
- pull-request number or URL when available;
- exact final commit SHA;
- base SHA/branch;
- Codex `FINAL_HANDOFF.md`;
- CI run/status at that SHA;
- staging API/admin URLs when deployed;
- mobile build identifier/download mechanism where appropriate;
- safe test-account creation instructions;
- known external blockers;
- any private evidence that cannot be placed in Git, described without revealing secrets.

Do not send passwords, API keys or database credentials in chat. Use safe test accounts or credential-entry instructions.

## 3. Inspection scope

### A. Repository integrity

- exact SHA exists remotely;
- work described in handoff exists;
- no unexpected generated/binary/private data;
- no secret patterns;
- branch/PR history coherent;
- status/decision/changelog current.

### B. Requirements traceability

- every MUST requirement has implementation path and test;
- no “Done” without evidence;
- scope matches Chapter Three;
- no live-MNO claim;
- risk/verification separation throughout.

### C. Architecture

- monorepo/modules match intended layers;
- Flask app factory/blueprints/services/repositories/policies;
- no controller-heavy ML/SQL;
- private storage abstraction;
- worker/job safety;
- generated API contract/client;
- configuration/secrets separation.

### D. Database

- migrations;
- constraints/multiplicities;
- active version uniqueness;
- immutable evidence;
- OCR correction history;
- reference import and verification;
- model/rule/template versions;
- case decision separation;
- audit;
- indexes;
- retention/backup documentation.

### E. API and access control

- auth/refresh/reset;
- RBAC;
- ownership/IDOR;
- state transitions;
- idempotency;
- validation/error envelope;
- private file/report access;
- staff actions/audit;
- pagination/export limits.

### F. Mobile UI

- auth;
- upload;
- OCR review;
- analysis progress;
- risk/verification result;
- evidence;
- history/report;
- fraud report;
- notifications/profile;
- secure token storage;
- loading/error/offline/accessibility.

### G. Admin/investigator UI

- role-aware shell;
- dashboard;
- transactions;
- cases/reasoned decision;
- users/roles;
- reference import;
- templates/rules/models;
- reports/audit/status;
- responsiveness/accessibility;
- private evidence access.

### H. OCR/image/ML/verification

- reproducible OCR;
- field confidence/correction;
- deterministic evidence;
- data manifest/splits;
- no leakage;
- actual metrics;
- artifact hashes/version registry;
- unavailable-model behaviour;
- verification field comparisons;
- risk reconstruction/reasons;
- limitations.

### I. Security/privacy

- upload controls;
- private storage;
- secret/client-bundle safety;
- auth/session;
- CSRF/CORS;
- XSS/export;
- model deserialisation;
- logs/redaction;
- staff access audit;
- dependency/secret scans.

### J. Tests/CI/performance/deployment

- test commands/results;
- clean migration;
- coverage;
- E2E;
- security;
- performance;
- staging smoke;
- image/build/migration identifiers;
- rollback.

### K. Documentation/academic evidence

- implemented diagrams match code;
- no crisscrossing/invalid multiplicities in final exported diagrams;
- wireframes distinguished from actual interfaces;
- Chapter Four screenshots/evaluation available;
- no unsupported claims.

## 4. Inspection methods

Depending on available access, the reviewer may:

- fetch repository files at the exact SHA;
- inspect PR diff and issue/CI results;
- search for code patterns, TODOs, secrets and endpoints;
- compare migrations/models/API/UI/tests;
- review screenshots/reports;
- run the repository locally when files/runtime access is available;
- exercise staging with safe credentials;
- inspect model/dataset reports and hashes.

A repository-only review cannot prove a deployment is reachable or that private artifacts exist; those items require the corresponding evidence.

## 5. Finding severity

### BLOCKER

- repository cannot be reproduced/run;
- primary user journey absent;
- destructive data loss;
- false implementation/deployment claim;
- final SHA not pushed.

### CRITICAL

- cross-user/staff bypass;
- public private receipt/reference data;
- committed live secret;
- plaintext passwords/tokens;
- arbitrary untrusted model execution;
- invalid destructive migration;
- fraud/verification outputs fundamentally wrong.

### HIGH

- major requirement missing;
- OCR/analysis/case flow broken;
- no version/evidence traceability;
- model/data leakage or fabricated metrics;
- no safe partial state;
- reference verification misrepresented as live;
- tests/CI not reproducible.

### MEDIUM

- important edge case;
- incomplete accessibility/error state;
- weak audit/test coverage;
- performance problem;
- documentation/schema mismatch.

### LOW

- maintainability;
- minor UX/copy;
- optimisation;
- non-critical documentation improvement.

## 6. Finding format

```markdown
### FINDING-ID — Title

**Severity:** High  
**Requirement(s):** FR-...  
**Location:** `path/to/file.py:L10-L42`  
**Evidence:** What was observed and how it was verified.  
**Impact:** What can go wrong.  
**Required correction:** Exact expected behaviour.  
**Acceptance test:** Command/scenario that proves the fix.  
**Suggested Codex phase:** Audit fix N.
```

Findings must distinguish:

- verified defect;
- probable defect requiring runtime confirmation;
- missing evidence;
- improvement.

## 7. Inspection report structure

1. Executive verdict.
2. Reviewed repository/branch/SHA.
3. Evidence available/unavailable.
4. Requirement completion summary.
5. Findings by severity.
6. Security/privacy assessment.
7. OCR/ML/data-methodology assessment.
8. UI/UX assessment.
9. Test/CI/deployment assessment.
10. Release recommendation.
11. Codex repair prompt.
12. Reinspection requirements.

## 8. Repair loop

For each finding Codex must:

1. reproduce/confirm;
2. map to requirement;
3. create `codex/audit-fix-NN-...`;
4. implement code/schema/docs as needed;
5. add regression test;
6. run relevant and full verification;
7. update traceability/status/changelog;
8. commit/push;
9. provide a finding-by-finding resolution table and new SHA.

A documentation-only change does not resolve a code/security defect.

## 9. Reinspection

Provide the new exact SHA. The reviewer verifies:

- the original finding;
- regression test;
- no introduced regression;
- CI status;
- changed requirements/docs;
- new deployment when needed.

The report marks each finding:

- Resolved;
- Partially resolved;
- Not resolved;
- Not verifiable;
- Accepted risk by owner.

## 10. Final acceptance

Recommend acceptance only when:

- no blocker/critical remains;
- high findings are resolved or explicitly accepted with mitigation;
- clean-clone/full verification evidence exists;
- final product journeys work;
- private data is protected;
- analytical claims are reproducible and limited to their evidence;
- exact final SHA is pushed;
- handoff and Chapter Four evidence are complete.

## 11. Important operational note

The reviewer does not automatically monitor GitHub or perform background work. After each desired milestone or final Codex session, the owner must provide the repository/branch/SHA or return with the handoff. The structured handoff keeps that message very short.
