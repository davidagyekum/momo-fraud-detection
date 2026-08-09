# P00 repository preflight and gap analysis

**Date:** 2026-08-09  
**Mode:** New repository  
**Starting Git state:** Empty directory, no `.git`, no remote, no branch, and no base SHA before package import  
**Work branch:** `codex/p00-preflight-foundation`

## Executive finding

The selected workspace contained no implementation or Git repository. The supplied implementation package has been preserved at the repository root and is the only retained project material. There is therefore no existing application code to migrate, reconcile, replace, or discard.

P00 establishes policy, documentation, toolchain diagnostics, secret checks, and a local backlog view. P01 remains responsible for creating the monorepo and runnable Flask/PostgreSQL foundation; this phase intentionally contains no product feature implementation.

## Starting inventory

| Area | Retained at preflight | Missing / deferred | Conflict or obsolete work |
|---|---|---|---|
| Git/GitHub | Git 2.46.0 is installed | No original repository, remote, default remote branch, commit, CI, issue labels, milestones, or PR | None; remote setup is an external P00 blocker |
| Product specifications | Full supplied package: numbered specifications, status files, traceability, backlog, samples, templates, and prompts | None for planning | `backlog.csv` contains several truncated display titles, while the corresponding descriptions remain complete; task IDs/descriptions are used as the reliable local view |
| Mobile | None | Entire Expo/React Native application (P04 onward) | None |
| Admin portal | None | Entire React/Vite portal (P05 onward) | None |
| API/worker | None | Flask API, worker, OpenAPI, and background processing (P01 onward) | None |
| Database/storage | None | PostgreSQL schema, migrations, seeds, and storage adapters (P01–P02) | None |
| OCR/image analysis | None | Tesseract/OpenCV pipeline and deterministic evidence (P07/P09) | None |
| Machine learning | None | Dataset tooling and structured/CNN pipelines (P10–P12) | None |
| Verification/risk | None | Reference imports, field comparison, rules, and aggregation (P08/P13) | None |
| Tests/CI | None | Product tests and CI workflows begin with P01 and grow by phase | None |
| Deployment | None | Docker/Compose and deployment configuration (P01/P19) | None |

## Toolchain observation

| Tool | Observed | P00 interpretation |
|---|---|---|
| Git | 2.46.0.windows.1 | Available |
| Python launcher | Python 3.12 available at the Windows launcher | Selected runtime; the unqualified `python` command currently resolves to Python 3.11.7, so Windows commands use `py -3.12` |
| Node.js | 22.11.0 | Selected Node major: 22 LTS |
| npm | 10.9.0 through `npm.cmd` | Available; PowerShell script execution policy blocks `npm.ps1`, so Windows docs should use `npm.cmd` when required |
| Docker | Not found | Required for P01 local infrastructure; not a P00 failure |
| Tesseract | Not found | Required before P07/runtime OCR; not a P00 failure |
| PostgreSQL CLI | Not found | Docker is the preferred local P01 path; not a P00 failure |

## Scope lock

The retained requirements establish these fixed boundaries:

1. Fraud risk and transaction verification are separate persisted and displayed outcomes.
2. Verification uses stored/imported reference records unless a real authorised adapter is added later.
3. Automated evidence is immutable; OCR corrections, reanalyses, and reviewer decisions append new evidence.
4. Missing analytical components produce an explicit partial/degraded state.
5. Receipt images and research/model artifacts remain private and outside Git.
6. The fixed stack is Expo/React Native, React/Vite, Flask, PostgreSQL, Tesseract/OpenCV/Pillow, TensorFlow/Keras, and scikit-learn.

## P00 deliverables and disposition

| Deliverable | Disposition |
|---|---|
| Preserve implementation package and root `AGENTS.md` | Complete locally |
| Repository inventory and gap analysis | Complete locally in this file |
| Root README, ignore/line-ending/editor policy, security note | Complete locally |
| Python/Node version selection | Python 3.12 and Node 22 recorded |
| Cross-platform bootstrap, doctor, secret scan, and verification scripts | Complete locally; results recorded in the session handoff |
| GitHub issue labels/milestones or local equivalent | Local phase/backlog index created because no remote exists |
| Phase branch and local commit | Created locally |
| Remote push/PR | Blocked until the owner supplies or configures a GitHub remote |

## Next implementation boundary

After the P00 remote blocker is resolved, the next phase is P01: create the monorepo, Flask application factory, PostgreSQL/Docker Compose infrastructure, health/readiness/version endpoints, OpenAPI baseline, structured errors/logging, and backend quality tooling. No P01 feature should be backfilled into this P00 branch.

