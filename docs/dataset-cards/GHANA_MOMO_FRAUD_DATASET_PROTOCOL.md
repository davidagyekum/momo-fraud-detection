# Ghana Mobile-Money Fraud Image Dataset Protocol

Status: collection workspace implemented; no real image has been approved for training yet.

## Purpose and boundary

This protocol governs a Ghana-only image corpus for a future mobile-money fraud-message classifier. It is separate from the P12 controlled-tampering corpus, whose labels are `ORIGINAL` and `CONTROLLED_TAMPERED`. The Ghana corpus uses `fraudulent`, `genuine` and `suspicious` image-level labels and must not be used to rewrite P12 claims.

The collection target is 500–600 eligible images when rights, privacy, Ghana relevance and visual quality permit. A smaller, honestly reported corpus is acceptable; synthetic filler is not part of this dataset profile.

## Provider and label taxonomy

The provider vocabulary treats “Telesell” as Telecel Cash and preserves historical aliases:

- `MTN_MOMO`: MTN MoMo / MTN Mobile Money.
- `TELECEL_CASH`: Telecel Cash / historical Vodafone Cash.
- `ATMONEY`: ATMoney / historical AirtelTigo Money.
- `GENERIC_MOMO`: provider not visually attributable.
- `MULTI_PROVIDER`: more than one provider is present.
- `UNKNOWN`: provider remains unclear after review.

Primary labels are `fraudulent`, `genuine` and `suspicious`. Suspicious examples stay in `images/review/` and are never used for training. Scam subtypes are multi-label metadata, not replacements for the primary label.

## Ghana-only inclusion rule

Each image requires a recorded Ghana evidence note. Strong evidence includes a Ghana provider, GHS currency, Ghanaian short code or authoritative Ghana source. Moderate evidence combines a Ghanaian source/context signal with compatible message characteristics. Weak evidence is not eligible for training.

Do not infer a person’s physical location from a phone screenshot. Ghanaian language or code-switching is a supporting signal and must be reviewed by a competent speaker where it affects the label.

## Source and rights workflow

Use the following priority order:

1. CSA, MTN Ghana, Telecel Ghana, AT Ghana, Bank of Ghana and Ghana Police publications.
2. Ghanaian news publishers and blogs that document scam patterns or reproduce screenshots.
3. X, Facebook/Instagram, Reddit and public channels only through a permitted interface, approved research access, manual review or explicit creator consent.

Every candidate requires a private provenance record containing the source URL, platform, account type, access date, rights assessment, consent/licence reference, takedown contact and retention review date. Unknown rights are `unknown_do_not_release` and cannot enter the training set.

Do not bulk-scrape X, Telegram, Reddit or private messaging spaces. Do not click suspicious links or decode QR codes during collection.

The initial discovery log was checked against the Ghana Data Protection Commission
DPIA guidance, the X Terms of Service, Telegram content-licensing terms, Reddit
Data API Terms and Meta's research-tool guidance. These are operating references,
not blanket reuse licences: a candidate still needs a recorded licence or consent
decision before it can become training data.

- [Ghana DPC DPIA guidance](https://dataprotection.org.gh/wp-content/uploads/2025/07/DPC-DPIA.pdf)
- [X Terms of Service](https://x.com/en/tos)
- [Telegram content licensing](https://telegram.org/tos/content-licensing)
- [Reddit Data API Terms](https://redditinc.com/policies/data-api-terms)
- [Meta research tools](https://about.fb.com/news/2023/11/new-tools-to-support-independent-research/)

## Privacy and redaction

The restricted original and the redacted research copy are separate objects. Redact phone numbers, wallet/account identifiers, transaction references, names, profile photographs, OTPs, PINs, email addresses, personal handles, physical addresses and QR codes. Defang malicious domains in review text and remove EXIF metadata.

Redaction must be consistent across fraudulent and genuine examples. The redaction version and human reviewer are recorded for every released image. The release copy must not contain active credentials, OTPs, PINs or live suspicious links.

## Annotation and splitting

Run a 50-image double-annotated pilot before scaling. Review agreement by primary label, provider and subtype; target κ/α ≥ 0.80 and adjudicate lower results. Record the reason for every adjudication.

Assign `source_group_id` and campaign groups before splitting. Default model split is 70% train, 15% validation and 15% test. Reposts, crops, recompressions and images from the same underlying campaign must remain in one split. Suspicious rows use the `review` split and are excluded from model evaluation.

## Local storage

The local working copy is intentionally under the already ignored path:

```text
ml/data/authorized/ghana_momo_fraud/
```

Only redacted working images belong there. Unredacted originals, consent records and creator identity data must stay in restricted encrypted storage. The canonical repository manifest uses `private_object_id`, not a repository-relative path, for real authorised images.

## Release gate

An image is eligible only when provenance, Ghana evidence, rights/privacy review, image decode/size checks, SHA-256, perceptual-hash review, labels, source-group split and redaction checks pass. The validator writes `audits/qa_report.json` with `status=NOT_READY` until eligible rows exist. It never fabricates model metrics or release approval.
