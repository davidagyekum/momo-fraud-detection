# Final Submission Freeze Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan.

**Goal:** Freeze an exact, pushed, repository-safe academic submission candidate whose evidence index and limitations match the implemented MoMo-FDVS prototype.

**Architecture:** Treat the Git commit as the only source of packaged files. A small Python packager will read the exact `HEAD` tree, reject unsafe paths/extensions and oversized entries, generate a per-file SHA-256 manifest inside a deterministic ZIP, and verify the ZIP independently. Submission Markdown will be the human entry point; `docs/evidence/EVIDENCE_MANIFEST.csv` will remain the machine-readable academic evidence index.

**Tech Stack:** Python 3.12 standard library, Git, Markdown, CSV, JSON, existing repository verification scripts.

**Spec:** `FINAL_COMPLETION_OVERRIDE.md`, `13_DOCUMENTATION_AND_CHAPTER4_EVIDENCE.md`, `12_FINAL_INSPECTION_PROTOCOL.md`, and the current `IMPLEMENTATION_STATUS.md`.

## Global Constraints

- Do not change product behavior, database schema, API contracts, model state, or risk policy during this freeze.
- Package only files tracked at an exact Git commit; never package the working tree, ignored files, untracked files, `.env`, private storage, credentials, raw/private datasets, model binaries, caches, build output, or browser state.
- Do not claim hosted deployment, hosted CI success, native Android/iOS device validation, live MNO verification, or an active/accepted image model.
- Preserve the rejected P12 image-model metric as a limitation: held-out macro F1 `0.333333`; artifact inactive/unavailable.
- Preserve risk and stored/imported-record verification as separate outcomes.
- Do not access locked-test data and do not execute model training.
- Do not mark original aspirational requirements complete merely because the submission package is complete.
- Use fictitious, synthetic, redacted, or aggregate evidence only.
- Build the final ZIP only after the freeze commit is clean and pushed; write the ZIP and checksum beneath ignored `output/submission/`.

## Task 1: Add package safety tests

**Files:**

- Create: `scripts/tests/test_build_submission_package.py`
- Create: `scripts/build_submission_package.py`

- [ ] Write failing unit tests for path traversal, private/secret path rejection, forbidden model/archive extensions, size limits, deterministic timestamps/order, manifest hashing, and verification failure after tampering.
- [ ] Run `py -3.12 -m unittest scripts.tests.test_build_submission_package -v` and confirm the initial behavioral tests fail for missing implementation.
- [ ] Implement pure path-policy, manifest, deterministic ZIP-writing, and ZIP-verification helpers using only the Python standard library.
- [ ] Implement the CLI with `build` and `verify` commands. `build` must read bytes through `git show <sha>:<path>` from `git ls-tree -r --name-only <sha>`, require a clean exact `HEAD`, and embed `FINAL_SUBMISSION_PACKAGE_MANIFEST.json`.
- [ ] Ensure verification rejects duplicate names, unsafe archive names, missing/unlisted files, digest/size drift, a manifest/commit mismatch, or a package containing a denied path/extension.
- [ ] Re-run the focused unit tests and require zero failures/skips.

## Task 2: Create the submission entry point and limitations record

**Files:**

- Create: `docs/submission/README.md`
- Create: `docs/submission/LIMITATIONS_AND_NON_CLAIMS.md`
- Create: `docs/submission/SUBMISSION_ARTIFACT_POLICY.md`
- Modify: `README.md`

- [ ] Make `docs/submission/README.md` the examiner/reviewer entry point with exact scope, run/verify links, evidence navigation, final SHA placeholder policy, and a concise acceptance statement.
- [ ] Record hosted deployment/CI, native-device, live-MNO, inactive image-model, structured-model, performance, restore-rehearsal, compatibility, and locked-test/training limitations in one authoritative non-claims document.
- [ ] Describe the tracked-files-only package policy, generated manifest schema, deterministic build, verification command, exclusions, and derived-artifact handling.
- [ ] Replace README's obsolete early-phase status and planned-only language with the current locally accepted prototype status and direct links to the submission entry point and run guide.
- [ ] Search all new submission prose for unsupported words such as `production-ready`, `deployed`, `live verified`, and unconditional `all requirements complete`.

## Task 3: Reconcile Chapter Four and the evidence manifest

**Files:**

- Create: `docs/submission/CHAPTER4_EVIDENCE_INDEX.md`
- Modify: `docs/evidence/EVIDENCE_MANIFEST.csv`
- Modify: `requirements_traceability.csv`

- [ ] Inventory every safe evidence file referenced by current P0.1, P0.2, P0.3, P1, PR18/PR19 acceptance, model evaluation, security, migration, E2E, architecture, and UI records.
- [ ] Add manifest rows for the current final-completion evidence and final QA/release evidence without rewriting historical rows or replacing their recorded SHAs.
- [ ] Mark local-only, browser-web-only, synthetic/controlled, inactive-model, or hosted-unverified scope in the `notes` field.
- [ ] Create a Chapter Four index that distinguishes implemented evidence, historical evidence, unmet/partially evidenced requirements, proposed wireframes, and actual UI screenshots.
- [ ] Update traceability evidence paths/notes only where the freeze adds a stronger index or limitation reference; do not inflate completion counts.
- [ ] Validate the CSV headers, row widths, Boolean columns, unique evidence IDs, referenced file existence, and safe-for-submission flags with a script/test.

## Task 4: Record the freeze decision and current state

**Files:**

- Modify: `DECISION_LOG.md`
- Modify: `CHANGELOG.md`
- Modify: `IMPLEMENTATION_STATUS.md`

- [ ] Add a decision that the submission artifact is generated only from an exact pushed Git tree, with a dynamic internal manifest and ignored external ZIP/checksum.
- [ ] Record the documentation/package freeze in the changelog.
- [ ] Change the current phase to final submission candidate frozen only after all checks pass.
- [ ] Keep hosted CI/deployment, native-device, live-MNO, image-model, performance, compatibility, backup/restore, and dependency limitations explicit.
- [ ] Leave original phase/requirement completion statuses truthful; final packaging is not retroactive implementation.

## Task 5: Verify the repository-safe package implementation

**Files:**

- Verify: `scripts/build_submission_package.py`
- Verify: all documentation and manifest files changed above

- [ ] Run focused packaging unit tests.
- [ ] Run `py -3.12 scripts/check_secrets.py`.
- [ ] Run the registered backend, mobile, administrator, ML, security, E2E, migration, and release verification commands required by the current authority, sequentially to avoid host memory pressure.
- [ ] Record exact commands, counts, failures, skips, durations, environment, and any reused immutable browser evidence. Never replace a failed command with an unsupported green claim.
- [ ] Inspect `git diff --check`, the full diff, status, current migration head, and generated contract drift.

## Task 6: Commit and push the freeze implementation

**Files:**

- Create: `docs/handoffs/2026-08-21-final-submission-freeze.md`
- Modify: session records above with the exact implementation SHA once available

- [ ] Complete the session handoff with base SHA, work branch, commands/results, limitations, changed files, and the next owner action.
- [ ] Commit the coherent implementation as `docs(submission): freeze academic submission candidate`.
- [ ] Push `codex/audit-fix-40-final-completion` and prove local/remote equality.
- [ ] If documentation needs the resulting commit identity, make one final documentation-only evidence commit, re-run documentation/package checks, push, and use that final SHA.

## Task 7: Build and independently verify the final exact-SHA artifact

**Files:**

- Generate (ignored): `output/submission/momo-fdvs-academic-submission-<short-sha>.zip`
- Generate (ignored): `output/submission/momo-fdvs-academic-submission-<short-sha>.zip.sha256`

- [ ] Require a clean worktree and a pushed `HEAD` equal to the tracked remote branch.
- [ ] Build the ZIP from exact `HEAD` twice into separate temporary outputs and require identical SHA-256 hashes.
- [ ] Run the independent package `verify` command against the final ZIP.
- [ ] Inspect the archive for denied path prefixes/extensions, `.env` variants, unexpected binaries, and manifest/file-count mismatch.
- [ ] Record the final branch, base SHA, head SHA, ZIP path, ZIP SHA-256, file count, package size, verification results, and limitations in the final response.

## Plan Review

- [ ] Every mutable file and generated artifact is named.
- [ ] Tests precede implementation for the packager.
- [ ] The exact-SHA problem is resolved by building after the final pushed commit.
- [ ] Derived ZIPs remain ignored and recoverable from the pushed source commit.
- [ ] No task weakens privacy, evidence immutability, risk/verification separation, or model/deployment honesty.
- [ ] No locked test, model training, private data, external account, deployment, or destructive operation is required.
