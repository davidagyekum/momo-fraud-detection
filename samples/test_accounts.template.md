# Test Account Handoff Template

Do not commit real passwords. Provide one of:

- a seed command that creates accounts with locally supplied environment passwords; or
- a one-time secure channel for staging credentials.

## Accounts

| Role | Email/identifier | Creation command/process | Capabilities | Password delivery |
|---|---|---|---|---|
| USER |  |  | Own uploads/history/reports | Not in Git/chat |
| ADMIN |  |  | Users/config/import/audit | Not in Git/chat |
| INVESTIGATOR |  |  | Cases/evidence/decisions | Not in Git/chat |

## Safe dataset/scenarios

- Genuine + Verified transaction ID:
- Suspicious + Unverified transaction ID:
- Fraudulent + Mismatch transaction ID:
- Partial analysis transaction ID:
- Open case ID:
- Reference import batch ID:

## Reset/cleanup

Describe how the reviewer can recreate/reset safe data without production access.
