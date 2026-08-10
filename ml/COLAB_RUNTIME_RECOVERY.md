# Google Colab Runtime-Loss Recovery

Colab virtual machines are ephemeral. Every logical PR12 smoke run therefore writes active work under the VM root and atomically mirrors verified checkpoints, the run manifest and final safe reports to the configured private Drive root.

## Standard roots

- VM: `/content/momo-work`
- private Drive: `/content/drive/MyDrive/momo-fraud`

Override them only through `MOMO_FDVS_VM_ROOT` and `MOMO_FDVS_DRIVE_ROOT`. Do not put a person's name, credential or shared public folder in a committed notebook path.

## Starting a new smoke run

1. Open `ml/notebooks/colab/00_environment_preflight.ipynb` from the pushed PR12 revision.
2. Set `TARGET_COMMIT` to the immutable code SHA from the handoff and run all cells.
3. Confirm the checkout is clean, Python is 3.12, all lock hashes are recorded, `is_ci` is false and acquisition/full-training flags are false.
4. Open `01_tiny_restart_safe_smoke.ipynb` with the same commit and leave `RESUME_RUN_ID = None`.
5. Record the generated run ID and durable manifest path. Do not copy secrets or private data into the run folder.

## Recovering after a lost VM

1. Start a fresh runtime and run the smoke notebook from the top with the same immutable commit, seed, Drive root and notebook path.
2. Set `RESUME_RUN_ID` to the original run ID.
3. The runtime marks the previously open session `interrupted`; it does not call it complete.
4. Before using a checkpoint, the loader verifies the durable ledger identity, filename, byte count and SHA-256. Missing VM-local files are restored atomically from Drive.
5. A mismatched or corrupt checkpoint stops the run. Never delete the ledger, edit its hashes or resume from a different run ID to bypass the failure.
6. Completed components are loaded from checkpoints; incomplete components run again. The run ID stays unchanged and the next session records the checkpoint hash it resumed from.
7. A completed run cannot be resumed. Create a new run ID for a new experiment.

## Checkpoint and synchronization policy

- Checkpoints are immutable JSON envelopes for this tiny smoke only.
- Each checkpoint is written to a same-directory temporary file, flushed, atomically renamed, hashed and then mirrored.
- The final JSON bundle and smoke report are hash-verified before and after Drive synchronization.
- Partial manifests remain non-promotable. Even completed smoke artifacts have `promotable: false` and cannot be registered as product models.
- Full future model workflows must apply the same ledger/session semantics to their framework-native checkpoints stored outside Git.

## Incident handling

If a run folder contains a secret, direct identifier or unapproved private data, stop immediately. Do not share the folder or paste its output into GitHub. Follow `data/governance/INCIDENT_RESPONSE.md`, revoke exposed credentials where relevant and start a new clean run only after containment.

## Evidence returned to the repository

Return only the non-sensitive preflight summary, smoke report, validated run-manifest hash and checkpoint hashes. Do not commit Drive paths containing identity, secret values, datasets, model binaries or checkpoint contents.
