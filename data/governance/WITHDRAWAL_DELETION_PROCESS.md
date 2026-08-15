# Withdrawal and Deletion Process

1. Receive the request through the approved private contact and authenticate it without exposing the participant publicly.
2. Resolve the private participant record to its SHA-256 pseudonymous identifier; never put the linkage value in Git.
3. Add a private withdrawal-ledger entry with request reference, scope, time, owner and `pending_disable` status.
4. Disable matching raw, transcript, annotation, derivative and manifest records before further processing.
5. Delete or quarantine affected objects according to the approved institutional process and retention obligations.
6. Rebuild dataset manifests and group splits; record new hashes and prove the participant hash is absent.
7. Mark every dependent run, checkpoint and model artifact invalid/retired until retrained on the rebuilt dataset.
8. Verify backups/caches/publication candidates according to the approved scope; document any lawful/technical limitation privately.
9. Have a second authorised reviewer confirm completion and set the ledger status to `completed`.
10. Notify the participant through the approved channel where required.

The executable validator rejects a participant hash present in a withdrawal ledger. It does not perform deletion automatically.
