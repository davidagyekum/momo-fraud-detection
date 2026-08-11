# Logical PR13 dataset-acquisition threat model

## Assets and trust boundaries

- Third-party archives and private participant folders are hostile/untrusted bytes even after access is authorised.
- Licence, consent, reviewer and version evidence are authoritative only in restricted governance storage; Git stores opaque references and safe status.
- Raw datasets, filenames, member names, identifiers, images, masks, transcripts and credentials must remain outside Git and public reports.
- Registration manifests and safe profiles are evidence, not permission grants and not training activation.

## Threats and controls

| Threat | Control |
|---|---|
| Unknown mirror or version substitution | Canonical registry ID/version, authoritative-source review, independent expected hash/size, content-addressed inventory and exact version match. |
| Acquisition before terms/consent | Permission/licence/consent states must be approved before source-path resolution or byte access. |
| Credential leakage | No network client; request schema accepts opaque references only; repository secret/PII/path scans remain registered. |
| Path escape or symlink substitution | Absolute source must resolve inside the approved private root; source and archive symlinks and traversal paths are rejected. |
| ZIP bomb or archive ambiguity | Member and expanded-size caps, duplicate normalised-path rejection, safe inventory and explicit/unambiguous CSV entrypoint. |
| Schema/count/class drift | Source-specific immutable validation specs, exact required columns, target/type/count checks and quarantine on mismatch. |
| Duplicate contamination | Exact canonical row hashes are stored temporarily in disk-backed SQLite; duplicate counts are aggregate-only. |
| Malformed or oversized images | Decoding plus byte, dimension and pixel caps; zero dimensions and configured image/mask mismatches quarantine the source. |
| Private filename or member disclosure | Inventories hash relative names; safe profiles expose aggregate counts/hashes only; member-level export is refused. |
| Silent mutation during validation | Source hash/size are verified and registration never extracts, moves, deletes or rewrites source bytes. |
| Accidental training use | Every registration manifest and safe profile sets promotion false; PR14 split/feature gates and later FULL Colab guards remain separate. |

## Residual risks and required human controls

- Code cannot decide whether third-party terms permit the intended use; an accountable reviewer must record the authoritative decision.
- Current MoMTSim, STFD and FSTS layouts are intentionally pending rather than guessed.
- Ghana-private consent, withdrawal linkage and institutional approval remain external human-governance processes.
- A valid hash proves byte identity, not legality, representativeness, label quality or absence of sensitive content.
