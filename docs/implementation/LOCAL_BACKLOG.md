# Local implementation milestones

`backlog.csv` is the task-level source. This compact local index substitutes for GitHub labels and milestones until a remote repository is configured. Status changes remain in `backlog.csv` and `IMPLEMENTATION_STATUS.md`.

| Phase | Tasks | Milestone |
|---|---:|---|
| P00 | 9 | Repository preflight, scope lock and execution foundation |
| P01 | 10 | Monorepo, API skeleton and local infrastructure |
| P02 | 10 | Relational schema, migrations, seeds and private storage abstraction |
| P03 | 11 | Authentication, session security, ownership and RBAC |
| P04 | 10 | Mobile application shell, design system and authentication experience |
| P05 | 10 | Administrator and investigator web portal shell |
| P06 | 11 | Receipt capture, hostile-file validation and private upload |
| P07 | 11 | OCR preprocessing, extraction, confidence and correction workflow |
| P08 | 11 | Reference-record import and transaction verification |
| P09 | 11 | Deterministic image-forensics and manipulation evidence |
| P10 | 10 | Dataset governance, controlled sample generation and reproducible splits |
| P11 | 11 | Structured-feature fraud classifier |
| P12 | 11 | CNN receipt-tampering classifier |
| P13 | 12 | End-to-end analysis orchestration, rules and risk aggregation |
| P14 | 10 | History, search, downloadable reports and notifications |
| P15 | 11 | Fraud reporting, investigation and governance administration |
| P16 | 10 | Operational dashboard, analytics, audit and system status |
| P17 | 10 | UI completion, accessibility, responsive and visual QA |
| P18 | 11 | Full hardening, security, performance and regression QA |
| P19 | 11 | Staging deployment, release engineering and rollback |
| P20 | 11 | Final documentation, evidence, cleanup and inspection handoff |

Total: 222 tasks.

## Local status workflow

Use the fixed values `Not Started`, `In Progress`, `Blocked`, `In Review`, and `Complete`. A phase is complete only after its exit criteria, status/traceability updates, commit, and remote evidence exist. External blockers retain an owner, impact, safe fallback, and exact next action.

