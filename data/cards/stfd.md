# Dataset Card — STFD

- Registry ID/version: `stfd` / `hf-revision-9edebed2109052a77e9a5581c2ea7ce33d685da0-private-v1`
- Source locator/citation key: `Zegkim/STFD`; Yu et al., “Learning to Locate the Text Forgery in Smartphone Screenshots,” ICASSP 2023, DOI `10.1109/ICASSP49357.2023.10095070`
- Intended role: external smartphone screenshot text-forgery localization/pretraining only where written terms permit
- Acquisition status: `registered`; exact private extracted inventory validated; disabled/non-promotable pending PR14
- Licence/permission: `verified` under the stricter combined conditions and `approved` by project-owner attestation `OWNER_ATTESTATION_STFD_20260811`; Hugging Face metadata shows CC BY 4.0, while the dataset notice limits use to academic research and asks users not to redistribute images
- Redistribution: blocked
- Expected schema: `data/schemas/screenshot.schema.json`
- Exact public archive identity: `STFD_ICASSP2023.zip`, 2,941,753,426 bytes, Hugging Face LFS SHA-256 `6159a6611caaf71f40acf181b404af5a5dd0547f3d2d8d819bb640e3fb5de18c`
- Published layout: five tampering types (`Copy-move`, `Splicing`, `Removal`, `Insertion`, `Replacement`), each with `tamper/` images and same-filename `masks/`; masks are documented as binary values 0/255
- Class distribution: unknown until authorised archive bytes are independently hash-verified and fully registered
- Appropriate use: approved academic image-tampering research with attribution, private storage and no redistribution
- Prohibited use: password bypass, credential sharing, non-academic use, archive/image redistribution, provider authenticity claims, or treating foreign screenshot/device distributions as Ghanaian coverage
- Limitations: public documentation does not expose a reliable source-lineage grouping key, so all STFD records form one external-pretraining train-only group and cannot produce internal STFD validation/test metrics. Three masks contain documented antialiased boundary pixels and may be thresholded only in derived training tensors. The real-world screenshots may still contain unintended information despite manual screening, and the device/template/provider distribution is not Ghana-specific.

No request email, password, archive, filename inventory, screenshot, mask or sample may enter Git. `docs/evidence/PR13_STFD_SOURCE_ACCESS_REVIEW.md` and `docs/evidence/PR13_STFD_REGISTRATION.json` record public-safe evidence. The registered source stays disabled/non-promotable; it may enter only the PR14 external-pretraining train partition as one group.
