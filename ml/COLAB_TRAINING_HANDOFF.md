# Google Colab Training Boundary

P10 ends with governed manifests, deterministic fixtures and leakage checks. P11's controlled structured model has now run in Colab. P12 image-model fitting must likewise begin only in Google Colab after the project owner approves the pinned notebook revision.

The training entry points now fail closed. A reportable command must select `--profile full`, provide `--acknowledge-full-training I_ACKNOWLEDGE_FULL_COLAB_TRAINING`, run outside CI and expose the expected Colab runtime markers. UNIT cannot fit. SMOKE may enter only the logical PR12 tiny surrogate flow under hard row/image/epoch caps; it cannot call the reportable training commands or produce promotable output. This does not grant dataset permission; all consent, split and owner-review gates still apply.

Logical PR12 adds `ml/notebooks/colab/00_environment_preflight.ipynb` and `01_tiny_restart_safe_smoke.ipynb`. Run them from a fresh signed-in Colab session at the exact SHA in the PR12 handoff. They use only committed fictitious/controlled fixtures and stop before acquisition or reportable training. Follow `COLAB_RUNTIME_RECOVERY.md` if the VM disappears.

For P12, open `ml/notebooks/P12_COLAB_IMAGE_TRAINING.ipynb` only after the P12 pre-training handoff. Verify its immutable SHA, run the preflight cells, then stop at its explicit training boundary until approval.

## Safe Colab preparation

1. Create a new private Colab notebook and select a Python runtime; choose a GPU only for the later CNN run.
2. Clone `https://github.com/davidagyekum/momo-fraud-detection.git` and check out the exact P12 training-code SHA reported in the handoff.
3. Install `ml/requirements-dev.lock` and `ml/requirements-training.lock`, set `PYTHONPATH=ml/src`, and run `python scripts/verify_ml.py` before any fit.
4. For controlled-only work, regenerate into `/content/momo-controlled` with seed `20260810` and confirm its manifest/split hashes match the committed report.
5. If authorised real data will be used, mount its approved private location. Do not copy it into the Git checkout, notebook source, output cells or a public Drive folder. Create a dataset card with real permission and retention references first.
6. Keep each source group intact. Do not augment validation/test data and do not fit encoders, scalers or imputers before the split.

## Evidence every real training run must return

- exact Git commit and notebook identifier;
- Python and dependency versions;
- dataset card, canonical manifest hash and split hash;
- split seed and source-group leakage result;
- class/source/split distributions;
- per-class precision, recall and F1, macro F1, balanced accuracy and confusion matrix;
- calibration/threshold evidence where applicable;
- exported artifact SHA-256 and safe storage location;
- explicit controlled/synthetic limitations.

Do not paste credentials into notebook cells. Use Colab secrets or an institution-approved mount. Do not commit private datasets, `.keras`, `.joblib`, pickle or other large/trusted-only artifacts to Git.
