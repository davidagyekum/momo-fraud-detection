# Google Colab Training Boundary

P10 ends with governed manifests, deterministic fixtures and leakage checks. It intentionally contains no trained model, metric or model artifact. P11/P12 execution begins only in Google Colab after the project owner opens a Colab runtime and supplies any authorised data location.

Upload or open `ml/notebooks/P10_COLAB_DATA_PREFLIGHT.ipynb` in Colab first. Replace its SHA placeholder with the exact merged P10 SHA from the session handoff and run through its explicit stop cell.

## Safe Colab preparation

1. Create a new private Colab notebook and select a Python runtime; choose a GPU only for the later CNN run.
2. Clone `https://github.com/davidagyekum/momo-fraud-detection.git` and check out the exact merged P10 SHA reported in the P10 handoff.
3. Install `ml/requirements-dev.lock`, set `PYTHONPATH=ml/src`, and run `python scripts/verify.py --ml` before adding private data.
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
