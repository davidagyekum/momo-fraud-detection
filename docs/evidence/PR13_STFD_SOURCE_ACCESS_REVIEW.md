# Logical PR13 STFD source and access review

Date reviewed: 2026-08-11  
Initial review scope: authoritative public metadata only. The 2026-08-11 owner-attestation addendum authorizes a private pinned transfer; extraction, image opening, splitting and training remain outside this review.

## Canonical source identity

- Dataset: Screenshot Text Forgery Dataset (STFD)
- Canonical dataset repository: <https://huggingface.co/datasets/Zegkim/STFD>
- Repository revision: `9edebed2109052a77e9a5581c2ea7ce33d685da0`
- Repository last modified: `2026-03-18T03:15:17Z`
- Repository state at review: public and ungated
- Protected archive: `STFD_ICASSP2023.zip`
- Archive size: 2,941,753,426 bytes
- Hugging Face LFS SHA-256: `6159a6611caaf71f40acf181b404af5a5dd0547f3d2d8d819bb640e3fb5de18c`
- Official project repository: <https://github.com/ZeqinYu/STFL-Net>
- Paper: Zeqin Yu, Bin Li, Yuzhen Lin, Jinhua Zeng and Jishen Zeng, “Learning to Locate the Text Forgery in Smartphone Screenshots,” ICASSP 2023, DOI <https://doi.org/10.1109/ICASSP49357.2023.10095070>

The revision, last-modified value, archive filename, byte size and LFS object hash were obtained from Hugging Face's metadata/tree APIs. The archive itself was not downloaded or opened.

## Terms and access decision

The Hugging Face metadata displays `cc-by-4.0`. Its dataset card adds narrower conditions: academic research only, attribution/citation, an access-password request sent from an academic or institutional email with researcher/supervisor/purpose details, and a request not to redistribute images because unintended information leakage may remain. The official project repository announced a public release on 2026-03-06 and currently displays an extraction password, which conflicts with the dataset card's email-request instruction.

Decision: follow the stricter current dataset-card notice. The academic/no-redistribution licence conditions are recorded as verified. On 2026-08-11 the project owner explicitly attested that the project has permission; the repository records only opaque reference `OWNER_ATTESTATION_STFD_20260811`, with no password, email or personal details. Permission is `approved`; the subsequent identity, hostile-archive, decoded image/mask and conservative grouping checks are recorded in `PR13_STFD_REGISTRATION.json`.

## Authoritative published layout

The dataset card documents smartphone screenshots from Android, HarmonyOS, iOS and Windows across chat, social media, mobile payment, e-commerce, online banking and other scenes. It documents PNG/JPEG images and five tampering types:

1. Copy-move
2. Splicing
3. Removal
4. Insertion
5. Replacement

Each category contains `tamper/` and `masks/` directories. A tampered image and its binary mask share the same filename; mask values are documented as 0 for unchanged pixels and 255 for tampered pixels.

## Unresolved source-group gate

The public card provides image/mask pairing but does not expose a source screenshot, donor, editing-session, template or device-instance lineage key. Hash-like filenames are pairing identifiers, not evidence of independent source groups. Random image-level splitting could therefore place related variants or donor/source material across train, validation and test.

Before PR14, one of the following must be recorded and tested:

- an authoritative grouping/index supplied by the dataset owner;
- archive metadata that unambiguously reconstructs shared source/editing lineage; or
- a conservative, reviewed grouping policy that prevents related images from crossing splits.

No STFD split may be created from filenames alone.

## Current outcome

- Licence/restrictions: verified under the stricter academic/no-redistribution notice
- Permission: approved by opaque project-owner attestation `OWNER_ATTESTATION_STFD_20260811`
- Exact version/archive metadata: recorded
- Image/mask pairing: recorded
- Leakage-safe group mapping: all STFD records are one external-pretraining train-only group; no filename-level or internal STFD evaluation split
- Acquisition status: `registered`; the private archive is 2,941,753,426 bytes, its SHA-256 matches `6159a6611caaf71f40acf181b404af5a5dd0547f3d2d8d819bb640e3fb5de18c`, and the extracted inventory hash is `1087bbc4ba2cd349f08e2a0a4c4ebbc78c209d603d625c2a5344c0ff50f220dc`
- Enabled/promotable: false
- Network acquisition: true, through a resumable transfer from the exact pinned official URL into restricted private storage
- Central-directory and complete decoded image/mask validation: true; splits, locked-test access and training: false

## Safe aggregate archive evidence

The completed encrypted ZIP contains 7,865 files and 19 directory entries. All 7,865 file payloads are encrypted. The central-directory review found zero unsafe paths, zero duplicate normalized paths, 7,864 PNG members and one metadata document. Total declared uncompressed size is 2,999,173,049 bytes; the largest member is 4,170,908 bytes. Both the 100,000-member and 100 GiB declared-size safety caps pass.

| Category | Tampered images | Masks | Complete pairs | Missing masks | Orphan masks |
|---|---:|---:|---:|---:|---:|
| Copy-move | 758 | 758 | 758 | 0 | 0 |
| Splicing | 830 | 830 | 830 | 0 | 0 |
| Removal | 1,016 | 1,016 | 1,016 | 0 | 0 |
| Insertion | 701 | 701 | 701 | 0 | 0 |
| Replacement | 627 | 627 | 627 | 0 | 0 |
| **Total** | **3,932** | **3,932** | **3,932** | **0** | **0** |

No raw member name, password, archive byte, screenshot or mask is committed. The later registration pass decoded all 3,932 pairs with zero decode/dimension/duplicate failures and documented three antialiased masks containing 12,860 soft pixels. Source masks remain immutable; any thresholding at 128 is derived-data-only. Independent lineage remains unavailable, so ADR-030 treats the complete corpus as one train-only external-pretraining group.
