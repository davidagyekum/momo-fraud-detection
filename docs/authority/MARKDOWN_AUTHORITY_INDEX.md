# Markdown Authority Index

This index classifies repository Markdown by purpose. It prevents historical planning documents from acting as current execution prompts.

## Tier 0 — current execution authority

- `FINAL_COMPLETION_OVERRIDE.md`
- `IMPLEMENTATION_STATUS.md` for the exact branch/head, verified state and next task
- current code, migrations, generated OpenAPI and executable tests

## Tier 1 — binding product and quality contracts

- `AGENTS.md`
- `00_SOURCE_OF_TRUTH_AND_SCOPE.md`
- `02_SYSTEM_REQUIREMENTS_SPECIFICATION.md`
- `03_ARCHITECTURE_AND_REPOSITORY_SPEC.md`
- `04_DATABASE_AND_STORAGE_SPEC.md`
- `05_API_CONTRACT.md`
- `06_UI_UX_IMPLEMENTATION_SPEC.md`
- `07_OCR_IMAGE_ML_VERIFICATION_SPEC.md`
- `08_SECURITY_PRIVACY_AUDIT_SPEC.md`
- `09_TESTING_QA_RELEASE_PLAN.md`
- `10_GITHUB_WORKFLOW_AND_SESSION_PROTOCOL.md`
- `11_DEPLOYMENT_RUNBOOK.md`
- `12_FINAL_INSPECTION_PROTOCOL.md`
- `13_DOCUMENTATION_AND_CHAPTER4_EVIDENCE.md`
- `SECURITY.md`
- `DATA_ACCESS.md`

## Tier 2 — active supporting design and evidence

These may constrain the current task when they describe an implemented contract or active blocker:

- `docs/architecture/**`
- `docs/security/**`
- `docs/deployment/**`
- `docs/models/**`
- `docs/reference/**`
- `docs/audits/**`
- `docs/evidence/**`
- `DECISION_LOG.md`
- `CHANGELOG.md`
- `requirements_traceability.csv`
- current PR description and review threads

## Tier 3 — completed historical plans and handoffs

These are evidence only. Their imperative language is not a current command:

- `docs/handoffs/**`
- `docs/implementation/**`
- `docs/superpowers/plans/**`
- `docs/superpowers/specs/**` after their named stage is complete
- `docs/plans/PR15_TRANSACTION_MODELS_IMPLEMENTATION.md`
- historical sections of `docs/plans/MoMo_Fraud_Detection_PR10_PR20_Colab_Blueprint.md`
- old phase tables in `01_CODEX_MASTER_IMPLEMENTATION_PLAN.md`

## Tier 4 — archive, bootstrap or external review context

- `README_FIRST.md`
- `COMPLETE_CODEX_HANDOFF.md`
- `docs/WEBCHAT_GPT_OCR_TEXT_RISK_REVIEW_BRIEF.md`
- external WebChatGPT/ChatGPT review requests
- supplied ZIP prompts and prior implementation packages

Tier 4 content may identify defects or provide reference code. It never overrides Tier 0–2 requirements and never chooses the next branch or phase.

## Conflict rule

When two documents conflict:

1. preserve privacy, security, ownership, immutability and evidence integrity;
2. follow Tier 0 before Tier 1, Tier 1 before Tier 2, and so on;
3. prefer a newer versioned contract over an older unversioned narrative;
4. prefer executed tests and current schema over aspirational historical prose;
5. record a compatibility decision and migration for any intentional contract change;
6. do not silently reinterpret a historical metric or claim.

## Required Codex behavior

At session start, Codex must print:

```text
Authority read: FINAL_COMPLETION_OVERRIDE.md
Baseline head: <sha>
Current next task: <one sentence from IMPLEMENTATION_STATUS.md>
Historical documents used only as evidence: yes
```

If `FINAL_COMPLETION_OVERRIDE.md` is absent, the task must stop before code changes.
