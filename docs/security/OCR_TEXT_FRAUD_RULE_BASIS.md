# OCR Text-Fraud Rule Basis

## Purpose and boundary

`ghana-momo-obvious-scam-rules-v1` is a conservative, deterministic safety layer
over OCR text from a user-supplied screenshot. It is not a trained classifier, a
calibrated probability, live mobile-network verification or a legal finding.
No-match text does not establish that a transaction is genuine.

The implementation package supplied on 2026-08-17 was treated as a technical
reference. Repository contracts and ADR-040 control the integrated behavior.

## Primary-source basis

The following public safety notices were reverified on 2026-08-17:

- [Ghana Cyber Security Authority — Fraudulent Business Impersonation](https://www.csa.gov.gh/cert-gh-alert44.php)
  warns about impersonated business contacts, requests for mobile-money details
  and PINs/OTPs, and recommends verifying contacts through official channels.
- [Ghana Cyber Security Authority — WhatsApp Account Takeover](https://www.csa.gov.gh/cert-gh-alert27.php)
  documents code-disclosure lures, mobile-money-transfer pretexts and malicious
  links, and directs users to keep OTPs and PINs confidential.
- [MTN Ghana — Scam Alert: Protect Your Personal Information](https://mtn.com.gh/newsabout/scam-alert-protect-your-personal-information/)
  identifies suspicious account/prize links and urgency pressure and states that
  MTN will not request a PIN through a text link or social media.

These sources justify safety-oriented rule categories; they do not validate the
ruleset's accuracy on a representative population.

## Privacy and evidence contract

Raw OCR text and matched substrings remain private OCR evidence. API, stage,
audit and log projections are allowlisted to fixed reason codes/summaries,
versions, categorical class, non-probabilistic rule score, evidence quality and
limitations. Dynamic phone numbers, URLs, secrets, values and snippets are not
persisted in the assessment projection.

Every assessment is bound to
`momo-text-fraud-assessment-v1` and
`ghana-momo-obvious-scam-rules-v1`. Historical evidence is not silently
recomputed under a later ruleset.

## Evaluation limitation

Unit and controlled integration tests demonstrate deterministic behavior,
negation handling, common OCR obfuscations, privacy-safe projection and product
integration. They are not accuracy, precision, recall, macro-F1 or calibration
evidence. A future optional text model requires the governed PR20 data and
locked-test process before it can influence the product policy.
