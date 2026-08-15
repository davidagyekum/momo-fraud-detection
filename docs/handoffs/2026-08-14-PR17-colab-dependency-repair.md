# Codex Session Handoff

## Session identity

- Date/time: 2026-08-14, Africa/Lagos
- Phase/sub-phase: Logical PR17 Colab OCR dependency repair
- Repository: `davidagyekum/momo-fraud-detection`
- Base branch: `codex/p17-ocr-benchmark`
- Base SHA: `a12097719649c24e5e02c17b6724e2d6ae5ee6cb`
- Work branch: `codex/p17-ocr-benchmark`
- Final head SHA: reported after the session commit
- Pull request: not created in this session
- Push status: reported after the session commit
- Worktree status: reported after the session commit

## Scope completed

- Requirement IDs: `NFR-ACC-001`, `NFR-AUD-001`, `NFR-MNT-001`, logical PR17 runtime reproducibility
- Goal: identify and repair the first PR17 Colab failure without touching private benchmark data or weakening dependency reproducibility.
- Actual completed work:
  - traced the screenshot traceback to pip dependency resolution in the notebook checkout/install cell;
  - confirmed from official package metadata that PaddleOCR 3.7.0 pulls PaddleX 3.7.0, which requires NumPy `>=1.24,<2.4`;
  - identified the conflicting repository pin `numpy==2.5.2` as the root cause;
  - added a failing regression test before changing production code;
  - changed the runtime/pyproject pin to `numpy==2.3.5` and regenerated the runtime lock hash;
  - added an executable Colab lock-contract guard for missing, malformed and out-of-range NumPy pins whenever PaddleOCR is present;
  - verified Python 3.12 Linux wheels exist for the four exact direct pins: NumPy 2.3.5, EasyOCR 1.7.2, PaddleOCR 3.7.0 and PaddlePaddle 3.3.1;
  - recorded the failed attempt as stopping before engine initialisation, archive extraction, benchmark execution or locked-test access.

## Changed files

| Path | Change | Why |
|---|---|---|
| `ml/requirements-runtime.lock` | Pin NumPy 2.3.5 | Satisfy PaddleX 3.7.0's published `<2.4` constraint |
| `ml/pyproject.toml` | Match the repaired NumPy direct dependency | Prevent editable-package drift from the runtime lock |
| `ml/src/momo_fdvs_ml/colab.py` | Enforce the PaddleOCR/NumPy compatibility interval | Fail CI before a future Colab resolver failure |
| `ml/tests/test_colab.py` | Add red/green compatibility, malformed and non-OCR branch tests | Reproduce the failure and protect all guard branches |
| `ml/colab_lock_report.json` | Record runtime lock SHA `074ab7b4…` | Keep deterministic lock evidence current |
| status/decision/changelog/evidence docs | Record root cause and fail-closed boundary | Prevent any metric or data-access claim for the failed attempt |

## Database/migrations

- Migration revision(s): none
- Upgrade tested from: not applicable
- Downgrade/rollback notes: restore the prior lock only by reverting this commit; it is known incompatible with PaddleX 3.7.0
- Data backfill: none
- Schema/ERD update: none

## API/contract

- Endpoints added/changed: none
- OpenAPI/client regenerated: not applicable
- Breaking change: none
- Error/permission behaviour: invalid OCR/NumPy lock combinations now fail the repository verification gate before Colab.

## OCR/image/ML/verification

- Runtime pin: `numpy==2.3.5`
- Runtime lock SHA-256: `074ab7b414333046081b5892cffafec0fa79a0953472ca219473e82727bdc0dc`
- OCR lock SHA-256: `4e01f2c3d5e15469c5223e9a75d29428d667006dd0533e7d1752b5f1bb7e3515`
- Metrics actually measured: none.
- Failed-run boundary: pip resolution only; engines were not initialised and the private archive was not extracted.
- Limitations: wheel availability and repository gates are verified locally; the corrected installation still requires a fresh Colab runtime run for environmental confirmation.
- No fabricated or unavailable evidence: benchmark, training, selection and locked-test access remain false.

## Security/privacy

- Access-control impact: none
- Private-data impact: no private archive or OCR record was opened during diagnosis or the failed Colab attempt
- Upload/storage impact: the previously verified private ZIP remains unchanged in restricted Drive storage
- Audit events: preparation evidence now records the resolver failure boundary and exact before/after NumPy pins
- Security checks: repository secret/prohibited-artifact scan recorded below

## Verification performed

| Command | Result | Counts/summary | Duration |
|---|---|---|---|
| `.venv\Scripts\python.exe -m pytest ml\tests\test_colab.py -q --no-cov -k "numpy_incompatible"` before implementation | EXPECTED FAIL | did not raise, proving regression reproduction | 2.05 s |
| `.venv\Scripts\python.exe -m pytest ml\tests\test_colab.py ml\tests\test_cli.py -q --no-cov` | PASS | 64 focused tests before branch-coverage additions | 18.09 s |
| metadata-only Linux wheel check | PASS | exact Python 3.12 wheels found for NumPy/EasyOCR/PaddleOCR/PaddlePaddle pins | 5.1 s |
| `.venv\Scripts\python.exe scripts\verify_ml.py` | PASS | 595 tests; 90.02% branch-aware coverage; format, Ruff, strict mypy, governance, locks, notebooks and controlled-data checks | 108.9 s |
| `.venv\Scripts\python.exe scripts\check_secrets.py` | PASS | 542 candidate files scanned | 11.8 s combined final audit |

Skipped/blocked checks and reason: Chrome automation was unavailable, and the corrected Colab install has not yet been rerun. No benchmark result may be inferred from local dependency checks.

## Known defects/blockers

| ID | Severity | Description | Impact | Safe fallback | Owner/input | Next action |
|---|---|---|---|---|---|---|
| PR17-COLAB-RERUN | Pending | Corrected lock has not executed in a fresh Colab runtime | Environmental installation and OCR benchmark remain unconfirmed | Preserve benchmark/metrics false | Project owner/Codex | Push repair, reopen pinned notebook and rerun from a fresh runtime |
| PR17-TAMPERED-SLICE | High | No approved controlled tampered-image validation slice exists | Clean validation cannot satisfy robustness gate | Keep any bundle experimental | Project owner/data steward | Create governed edits without locked-test records |

## Documentation updated

- `IMPLEMENTATION_STATUS.md`: yes
- `requirements_traceability.csv`: unchanged; requirement status remains in progress
- `DECISION_LOG.md`: ADR-035 dependency-repair addendum
- `CHANGELOG.md`: yes
- Evidence manifest/docs: PR17 preparation evidence and manifest hash updated

## Git evidence

```text
git status --short: reported after final commit
git log --oneline a12097719649c24e5e02c17b6724e2d6ae5ee6cb..HEAD: reported after commit
push output: reported after push
```

## Next exact task

Push the repair commit, open the PR17 notebook at that exact SHA in a fresh Colab runtime, set `TARGET_COMMIT` to the repaired SHA and `RUN_BENCHMARK=True`, then run all cells. The first safe output must confirm the 58-record development manifest, 33 validation records, locked-test false and training false before the benchmark continues.
