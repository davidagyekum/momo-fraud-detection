# Safe Samples

These files contain fake data for development and contract testing. They are not Mobile Network Operator records and must not be described as such.

- `reference_transactions_import.csv`: sample format for stored/imported reference verification.
- `receipt_dataset_manifest.csv`: sample dataset manifest. Image paths are placeholders.
- `fraud_rules_seed.csv`: human-readable starter rule catalogue; the implemented database seed must validate and version these rules.
- `API_EXAMPLES.http`: safe local request examples with placeholder tokens.
- `test_accounts.template.md`: test-account handoff structure without real passwords.

Never replace these with private production data in Git.
