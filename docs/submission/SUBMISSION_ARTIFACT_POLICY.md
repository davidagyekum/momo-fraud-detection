# Submission Artifact Policy

## Purpose

The academic ZIP must reproduce an exact pushed commit without copying private, ignored or mutable local state. `scripts/build_submission_package.py` is the only supported final package builder.

## Source boundary

The builder requires:

- a clean working tree;
- `HEAD` equal to the selected commit;
- local `HEAD` equal to its configured upstream;
- every source entry to come from `git archive <commit>`.

It does not read files from the working tree. Untracked and ignored files cannot enter the ZIP.

## Rejected content

The path policy rejects traversal/absolute/Windows-drive paths, files larger than 25 MiB, and a package larger than 250 MiB. It also rejects:

- `.env` variants other than `.env.example`, credentials and private keys;
- `.local`, private storage, uploads, private/raw/staging/quarantine data and consent records;
- model artifacts/checkpoints and executable serialisation formats;
- Node/Python caches, dependency trees, build/export/test/browser output;
- nested archives, including ZIP/TAR/7z/RAR;
- the ignored `output/` directory itself.

Controlled fixtures and anonymised evidence already tracked in Git remain eligible after the same path, size and evidence-manifest checks.

## Deterministic construction

The ZIP contains:

1. `FINAL_SUBMISSION_PACKAGE_MANIFEST.json`;
2. every accepted tracked file in UTF-8 path order.

All ZIP members use the fixed timestamp `1980-01-01T00:00:00Z` and stable file mode/compression settings. The manifest records the exact source commit and a SHA-256/size tuple for every file. It excludes itself from the file count and hash list to avoid a recursive self-hash.

The ZIP and its `.sha256` sidecar are generated beneath ignored `output/submission/`; neither derived file is committed. Both are reproducible from the pushed source commit.

## Build and verify

From a clean repository root after pushing:

```powershell
$sha = git rev-parse --short=12 HEAD
py -3.12 scripts\build_submission_package.py build `
  --output "output\submission\momo-fdvs-academic-submission-$sha.zip"

py -3.12 scripts\build_submission_package.py verify `
  "output\submission\momo-fdvs-academic-submission-$sha.zip" `
  --expected-commit (git rev-parse HEAD)
```

To validate the academic evidence index independently:

```powershell
py -3.12 scripts\build_submission_package.py validate-evidence
```

To prove deterministic reproduction, build the same pushed commit to two different output filenames and compare their SHA-256 values.

## Independent verification checks

Verification fails on duplicate archive members, unsafe paths/extensions, unexpected directories, non-fixed timestamps, missing/extra entries, invalid manifest schema, commit mismatch, unsorted/duplicate manifest paths, size/hash drift, missing evidence files, duplicate evidence IDs or an evidence row marked both sensitive and submission-safe.

Passing package verification proves archive integrity and consistency with its manifest. It does not independently prove a hosted deployment, model accuracy or compatibility beyond the evidence records.
