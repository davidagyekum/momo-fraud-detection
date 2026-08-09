# 10 — GitHub Workflow and Codex Session Protocol

## 1. Purpose

This workflow preserves work, limits repeated context, makes each Codex session reviewable and prevents token loss from re-explaining the project.

The repository files are persistent memory. Codex must read status/handoff documents instead of relying on a previous chat transcript.

## 2. Branch model

- `main`: stable/release-ready.
- `develop`: optional integration branch when the owner chooses PR-based integration before `main`.
- `codex/pNN-short-description`: one phase branch.
- `codex/audit-fix-NN-short-description`: fixes from an independent audit.
- `hotfix/...`: only for an actual deployed release issue.

One branch should have one coherent purpose. Do not combine unrelated phase work.

## 3. Starting a session

Codex must execute and report:

```bash
git remote -v
git fetch --all --prune
git status --short
git branch --show-current
git rev-parse HEAD
git log -5 --oneline
```

Then:

1. read root `AGENTS.md`;
2. read `IMPLEMENTATION_STATUS.md`;
3. read the last session handoff;
4. inspect open PR/issue context when available;
5. verify the intended base branch/SHA;
6. check for unrelated modifications;
7. select one phase/sub-phase;
8. state the plan and requirement IDs;
9. create/switch branch.

Do not begin by reinstalling/rebuilding everything without first understanding repository state.

## 4. Working-tree safety

- Never discard a user's uncommitted changes.
- Never run destructive clean/reset commands without explicit approval.
- If unrelated changes exist, stop and report or isolate safely.
- Do not rewrite history or force push.
- Do not use `git add .` blindly before reviewing files.
- Inspect `git diff --check`, `git diff --stat`, and staged diff.
- Do not commit caches, datasets, raw receipts, secrets, reports containing PII, build output or large model artifacts.

## 5. Commit policy

Prefer small coherent commits that leave the branch testable. A phase may contain several commits, for example:

1. schema/migration;
2. backend behaviour/tests;
3. client UI/tests;
4. documentation/traceability.

Conventional commit structure:

```text
type(scope): imperative summary

Optional body:
- why the change was required
- important compatibility/security decision
- migration or rollout note
```

Types:

- `feat`
- `fix`
- `refactor`
- `test`
- `docs`
- `build`
- `ci`
- `chore`
- `perf`
- `security`

No “final”, “stuff”, “updates”, or misleading success language.

## 6. Push policy

At the end of every productive session:

```bash
git status --short
git diff --check
git log --oneline <base>..HEAD
git push -u origin <branch>
```

Codex reports:

- remote;
- branch;
- base SHA;
- head SHA;
- push command;
- push result.

If GitHub authentication/network is unavailable:

- create local commits;
- do not claim push;
- include exact push command for the user;
- mark `Push status: BLOCKED`;
- retain a clean, committed worktree where possible.

## 7. Pull requests

Create/update a draft PR per phase when connector/CLI access permits.

PR title:

```text
[P07] OCR preprocessing, field extraction and review
```

PR description uses `templates/PR_DESCRIPTION.md` and includes:

- scope and requirements;
- architecture/data/API changes;
- screenshots;
- migrations;
- tests and counts;
- security/privacy notes;
- known limitations;
- exact verification commands;
- checklist.

Do not mark ready for review while required phase gates fail.

## 8. CI required checks

Recommended check names:

- `repo-policy`
- `backend-lint-type`
- `backend-tests`
- `database-migrations`
- `openapi-contract`
- `ml-data-tests`
- `admin-quality-build`
- `mobile-quality`
- `security-secrets-dependencies`
- `docker-build`
- `e2e-smoke` when environment permits

Protect `main`/`develop` with required checks and review when repository settings permit.

## 9. Persistent session memory files

### `IMPLEMENTATION_STATUS.md`

Current phase, completed phases, requirement counts, branch/SHA, blockers and exact next task.

### `DECISION_LOG.md`

Every architectural or scope decision with context, options and consequence.

### `CHANGELOG.md`

User-visible/system-level changes, not every code refactor.

### `requirements_traceability.csv`

Requirement mapping and real test evidence.

### `docs/handoffs/YYYY-MM-DD-PNN-session.md`

Completed session handoff using the template.

Codex updates these before commit. A chat-only summary is insufficient.

## 10. Session size and token preservation

A session should target:

- one phase, or
- one vertical slice with a clear acceptance test.

When a phase is too large:

1. divide it into `P07A`, `P07B`, etc. in the status file;
2. keep one branch or create clearly dependent branches;
3. finish a compilable/testable boundary;
4. commit and push;
5. document the next exact file/test/task.

Do not attempt the entire project in one uncontrolled change. Re-reading only the relevant specs plus status is preferred to pasting the full plan into every prompt.

## 11. Required pre-commit review

Codex must inspect:

- new/changed files;
- generated files;
- secrets/private-data patterns;
- dependency changes;
- migration;
- public API changes;
- access-control paths;
- tests;
- docs/traceability;
- TODO/FIXME.

It must explain any large binary, generated artifact or dependency addition.

## 12. Required session verification

Run phase-specific tests and at minimum:

```bash
python scripts/verify.py --quick
```

When the phase changes core integrations, run:

```bash
python scripts/verify.py --all
```

A failing unrelated pre-existing test must be:

- verified as pre-existing at base SHA;
- recorded with evidence;
- not silently ignored;
- fixed when reasonably within scope or added as a blocker.

## 13. Handoff report

Every session writes a handoff containing:

- date/time;
- phase and scope;
- requirement IDs;
- base branch/SHA;
- work branch;
- final head SHA;
- changed files;
- migrations;
- API/schema/UI changes;
- tests with commands/counts;
- screenshots/evidence;
- security/privacy impact;
- known failures/blockers;
- next exact task;
- worktree status;
- push/PR status.

Use exact facts. “Tests passed” must include the command and count/output summary.

## 14. Final handoff

P20 completes `templates/FINAL_HANDOFF.md` and commits it at the final SHA. It includes:

- exact repo/branch/PR/SHA;
- full architecture;
- feature matrix;
- migrations;
- API docs;
- model/dataset cards;
- test/security/performance results;
- staging URLs/build IDs;
- test-account creation instructions;
- limitations and external blockers;
- reproduction commands;
- file paths to Chapter Four evidence;
- Git status and CI state.

## 15. Independent review loop

After a pushed milestone/final SHA:

1. owner provides repository name, branch/PR and SHA;
2. reviewer fetches exact files/PR/CI evidence;
3. reviewer returns findings by severity, file and acceptance criterion;
4. owner gives findings to Codex using `prompts/REPAIR_AFTER_AUDIT_PROMPT.txt`;
5. Codex creates an audit-fix branch;
6. each finding is mapped to commit/test;
7. Codex pushes and produces a repair handoff;
8. reviewer rechecks the new exact SHA.

Do not “fix” by merely changing the documentation when code is wrong.

## 16. Merge policy

Before merge:

- phase exit criteria complete;
- required checks green;
- migration reviewed;
- traceability updated;
- no secret/private data;
- PR diff reviewed;
- conflicts resolved without dropping changes;
- approved destination branch.

Use merge strategy chosen by owner. Preserve meaningful commit history or squash with a complete PR summary. Tag releases from the actual merged commit.

## 17. GitHub issues/backlog

Import or recreate `backlog.csv` as issues/milestones when useful. Each issue contains:

- task ID/phase;
- requirement IDs;
- acceptance criteria;
- dependencies;
- test evidence;
- status.

Close an issue only when the relevant commit is pushed and acceptance evidence exists.

## 18. Prohibited claims/actions

Codex must not:

- say it pushed without a successful push response;
- say CI passed without viewing the run/result;
- say deployed without a reachable deployment/build identifier;
- invent a PR URL;
- invent test counts;
- hide skipped tests;
- edit `IMPLEMENTATION_STATUS.md` to Done before implementation;
- force-push;
- commit `.env`, private receipts or live credentials;
- merge without instruction;
- continue on a different base SHA without documenting it.
