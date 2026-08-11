# Logical PR13 STFD source and access review

Date reviewed: 2026-08-11  
Review scope: authoritative public metadata only; no archive/sample download, extraction, image opening, splitting or training

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

Decision: follow the stricter current dataset-card notice. The academic/no-redistribution licence conditions are recorded as verified, but permission remains `access_request_required`. A publicly visible password is not treated as project-specific written approval. No password or access correspondence belongs in Git; only an opaque approval reference may be recorded after the owner receives it.

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
- Permission: access request required
- Exact version/archive metadata: recorded
- Image/mask pairing: recorded
- Leakage-safe group mapping: pending
- Acquisition status: `not_acquired`
- Enabled/promotable: false
- Network acquisition, archive opening, splits, locked-test access and training executed by this review: false
