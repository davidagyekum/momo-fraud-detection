# Codex Session Handoff

## Session identity

- Date/time: 2026-08-10
- Phase/sub-phase: P10 follow-up — Ghana mobile-money fraud image corpus governance
- Repository: `davidagyekum/momo-fraud-detection`
- Base branch: `codex/p12-cnn-tampering`
- Base SHA: `fe39556b67ccab26004bda1674593c335d2e35dd`
- Work branch: `codex/p10-ghana-image-corpus`
- Implementation commit: `80bf6c6868cecab2acf46778becc916e68cac7c5`
- Final head SHA: the documentation-only handoff follow-up is included after the implementation commit; report the resulting exact branch head at session close
- Pull request: not opened
- Push status: implementation branch pushed successfully to `origin/codex/p10-ghana-image-corpus`; this handoff update is the final documentation-only follow-up
- Worktree status: preserve the four pre-existing untracked P12 evidence/model-card files; they are not part of this workstream

## Scope completed

- Requirement IDs: NFR-DATA-001; P10 dataset-governance follow-up
- Backlog task IDs: no new backlog ID; work is a separately governed Ghana-corpus workstream
- Goal: implement the staged, rights-cleared and redacted Ghana-only image-corpus plan without mixing it with P12 controlled tampering
- Actual completed work: added an ignored private workspace, source/query registry templates, provider and label taxonomy, explicit redaction helper, SHA-256/pHash/OCR-fingerprint checks, duplicate and source-group split guards, canonical private-object manifest projection, CLI operations, tests, dataset protocol and a NOT_READY QA report

## Changed files

| Path | Change | Why |
|---|---|---|
| `ml/src/momo_fdvs_ml/ghana_dataset.py` | New governed dataset validator and redaction/manifest helpers | Enforce Ghana evidence, rights, privacy, hashes, pHash/OCR deduplication and split isolation |
| `scripts/ghana_dataset.py` | New `init`, `validate`, `redact` and `build-manifest` CLI | Make collection and release checks repeatable and fail closed |
| `ml/tests/test_ghana_dataset.py` | New regression suite | Cover workspace setup, rights/privacy rejection, redaction, hashes, deduplication, split leakage and private-object manifests |
| `docs/dataset-cards/GHANA_MOMO_FRAUD_DATASET_PROTOCOL.md` | Tracked protocol | Define scope, taxonomy, evidence, rights, redaction, annotation and release gates |
| `ml/data/authorized/ghana_momo_fraud/` | Local gitignored workspace, registry, query log, docs and QA report | Keep redacted working data and private provenance out of Git |
| `IMPLEMENTATION_STATUS.md`, `requirements_traceability.csv`, `DECISION_LOG.md`, `CHANGELOG.md` | Governance/session updates | Record the separate workstream, blocker and honest NOT_READY state |

## Database/migrations

- Migration revision(s): none
- Upgrade tested from: not applicable
- Downgrade/rollback notes: not applicable
- Data backfill: none
- Schema/ERD update: none

## API/contract

- Endpoints added/changed: none
- OpenAPI/client regenerated: no
- Breaking change: no
- Error/permission behaviour: dataset CLI returns `2` for an incomplete/not-ready corpus and never treats an empty workspace as a successful release

## UI

- Screens/components: none
- States covered: not applicable
- Viewports/devices: not applicable
- Screenshot/evidence paths: none
- Accessibility notes: not applicable

## OCR/image/ML/verification

- Pipeline/model/rule/template versions: `ghana-mobile-money-fraud-message-v1`; manifest schema `ghana-momo-fraud-manifest-v1`; redaction `manual-box-v1`; OCR fingerprint `redacted-ocr-v1`
- Dataset/split/artifact hashes: empty-workspace manifest hash and split hash are recorded in `ml/data/authorized/ghana_momo_fraud/audits/qa_report.json`; no model artifact
- Metrics actually measured: 117 ML tests passed at 93.00% branch-aware coverage; no fraud-message model was trained and no classifier metric is claimed
- Limitations: zero eligible images; discovery records are not training data; no rights-uncertain image was downloaded into the corpus; 500–600 remains a target, not a result
- No fabricated or unavailable evidence: QA explicitly reports `NOT_READY`, `ready_count=0`, `training_executed=false`, `model_metrics=null`

## Security/privacy

- Access-control impact: no application endpoint change; canonical real-data records require private object IDs
- Private-data impact: raw originals, consent records and creator identity data remain outside the repository; the local workspace is gitignored
- Upload/storage impact: no upload endpoint; redaction helper requires explicit human-reviewed boxes and removes EXIF metadata
- Audit events: source URL, platform, access date, rights status, Ghana evidence and query status are logged in the private registry/query log
- Security checks: private identifier scan, path containment, rights/PPI release gates, exact SHA-256, pHash distance, OCR fingerprint and source-group split checks

## Verification performed

| Command | Result | Counts/summary | Duration |
|---|---|---|---|
| `.venv\\Scripts\\python.exe -m ruff check ml\\src\\momo_fdvs_ml\\ghana_dataset.py ml\\tests\\test_ghana_dataset.py scripts\\ghana_dataset.py` | PASS | All checks passed | < 5 s |
| `.venv\\Scripts\\python.exe -m mypy ml\\src\\momo_fdvs_ml\\ghana_dataset.py scripts\\ghana_dataset.py` | PASS | No issues found | < 5 s |
| `.venv\\Scripts\\python.exe -m pytest ml -q` | PASS | 117 passed; total coverage 90.97% | 64.00 s |
| `.venv\\Scripts\\python.exe scripts\\ghana_dataset.py init` | PASS | Workspace/templates created without overwriting existing files | < 2 s |
| `.venv\\Scripts\\python.exe scripts\\ghana_dataset.py validate` | EXPECTED NOT_READY | Exit 2; 0 rows, 0 ready images, 1 target warning | < 2 s |
| `.venv\\Scripts\\python.exe scripts\\verify_ml.py` | PASS | 117 tests; 93.00% branch-aware coverage; controlled/structured/image report drift checks passed; no model training | 71.00 s |
| `.venv\\Scripts\\python.exe scripts\\verify.py --ml` | PARTIAL | Secret scan and ML verification passed; wrapper returned 1 because the doctor found inactive Node 24, Tesseract and PostgreSQL CLI prerequisites | 81.10 s |

Skipped/blocked checks and reason:

- Bulk social scraping was not attempted because the plan requires permitted interfaces, approved APIs or explicit consent and the logged platform terms prohibit unapproved collection/ML reuse.
- No candidate screenshot was admitted because rights were not verified. The source registry records discovery only.
- No 50-image agreement statistic exists because the rights-cleared pilot has not started.

## Known defects/blockers

| ID | Severity | Description | Impact | Safe fallback | Owner/input | Next action |
|---|---|---|---|---|---|---|
| GHANA-DATA-001 | High | No rights-cleared Ghana image set is available; current web/social candidates have unknown or restricted reuse status. | The corpus cannot enter training and no fraud-message metric can be produced. | Keep the workspace empty/NOT_READY and retain auditable discovery records only. | Project owner/research team | Obtain official/licensed/consented material, complete redaction and run the 50-image double-annotation pilot. |

## Documentation updated

- `IMPLEMENTATION_STATUS.md`: added separate Ghana workstream, blocker, NOT_READY count and next task
- `requirements_traceability.csv`: extended NFR-DATA-001 evidence
- `DECISION_LOG.md`: added ADR-017 rights-gated corpus decision
- `CHANGELOG.md`: recorded the corpus tooling and limitation
- Evidence manifest/docs: added the tracked protocol and private local corpus README, datasheet, rights/redaction and annotation guides

## Git evidence

```text
git status --short:
  Preserve four pre-existing untracked P12 evidence/model-card files.
git log --oneline <base>..HEAD:
  80bf6c6 feat(data): add Ghana MoMo fraud corpus tooling
  Followed by the final documentation-only handoff update.
push output:
  `codex/p10-ghana-image-corpus -> origin/codex/p10-ghana-image-corpus` succeeded.
```

## Next exact task

After owner approval and documented source permissions, add the first 50 redacted candidate rows under `ml/data/authorized/ghana_momo_fraud/`, double-annotate core/provider/subtype labels, adjudicate agreement, run `scripts/ghana_dataset.py validate --require-ready --minimum-ready 50`, and only then assign release splits. Keep suspicious rows in `images/review/` and keep P12 training unchanged.
