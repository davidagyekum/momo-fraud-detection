# P05 Portal Design Specification

## Accepted concept references

- `p05-staff-login-concept.png` — 1584×1024 staff-login split screen
- `p05-admin-shell-desktop-concept.png` — 1584×1024 desktop shell
- `p05-admin-shell-tablet-concept.png` — 1086×1448 tablet shell and navigation drawer

The generated references are implementation specifications, not production UI assets. All navigation, controls, tables and text remain semantic code-native elements.

## Visual system

- Background: true white primary workspace with cool-gray secondary surfaces.
- Brand/navigation: deep evergreen `#0B2F26`; selected navigation uses a restrained lighter evergreen and warm-gold boundary.
- Accent: warm gold `#D49A2A`, used for primary action/focus and selected-state emphasis.
- Text: near-black ink; muted text remains WCAG-readable.
- Typography: Inter-like sans serif; 28–32px page headings, 13–15px deliberate control text, tabular numerals for future amounts.
- Geometry: open bands, lists and tables; 10–12px radii on controls/purposeful frames; no nested card grid.
- Icons: consistent outline family around 1.75px stroke; icon plus text where status or navigation meaning is conveyed.
- Motion: short drawer/dialog transitions only; disabled under `prefers-reduced-motion`.

## Layout and component inventory

- Login: open split layout, editorial brand panel and one focused form. On tablet/narrow layouts, the editorial panel becomes a compact header band.
- Desktop shell: fixed evergreen sidebar, quiet top header, breadcrumb and open main workspace.
- Tablet shell: compact header and modal navigation drawer with focus containment/restoration.
- Reusable families: buttons, form fields, alerts, status badges, table/list alternative, filters, pagination, dialog, drawer, chart frame, skeleton, empty/retry/permission states and secure-download action.
- Required state treatments: loading, refresh, empty, filtered empty, error/retry, partial/degraded, permission denied, not found, session expired and confirmation.

## Copy lock

Login first viewport may contain only:

- `MoMo-FDVS`
- `Review evidence. Protect every decision.`
- `Fraud risk and transaction verification remain separate throughout every case.`
- `Staff sign in`
- `Secure access for authorised administrators and investigators.`
- `Work email`, `Password`, `Sign in`, `Forgot password?`
- `Environment: Local`
- `Access is monitored and audited.`

Authenticated first viewport may contain the required brand, role/environment/header controls, route navigation, `Operations overview`, `Refresh`, the separate labels `Fraud risk`, `Verification status`, `Case status`, `Processing state`, and honest inactive/empty copy. No metric value, chart, operational count or later-phase success may be invented.

## Role navigation

- ADMIN: Dashboard, Transactions, Cases, Users, Reference Imports, Receipt Templates, Fraud Rules, Model Registry, Reports, Audit Logs, System Status, Profile/Security.
- INVESTIGATOR: Dashboard, authorised Transactions, Cases, Reports and Profile/Security.
- USER or missing staff capability: no protected content; route to No Access after identity validation.

Navigation hiding is usability only. The API remains authoritative for every protected operation.

## Implemented fidelity ledger

| Concept commitment | Implemented evidence | Outcome |
|---|---|---|
| Deep-evergreen shell with restrained gold selection/focus | Desktop sidebar and tablet drawer use `#0B2F26`; active navigation and focus rings use the warm-gold token | Matched |
| Open white/cool-gray workspace rather than a dashboard card grid | Page content is arranged as a heading band, one informational band, a four-column evidence strip and one open activity frame | Matched |
| Fraud risk, verification, case and processing are independent concepts | Four named icon-and-text cells remain separate at desktop, tablet and narrow widths | Matched |
| Role and environment context remain visible | Desktop sidebar/header and tablet drawer identify Local plus Administrator/Investigator | Matched |
| Tablet navigation becomes a modal drawer | 768Ã—1024 evidence shows the focus-contained, dismissible navigation drawer over the workspace | Matched |
| No invented operational values | The implementation renders em dashes and explicit later-phase/no-data copy | Matched |
| Accessible semantic controls | Code-native landmarks, links, buttons, status regions, dialog naming, visible focus and reduced-motion styles replace all generated pixels | Matched |

The desktop concept included a dormant transaction-table header. The implementation intentionally uses a neutral `Recent activity` frame instead: P16 owns operational transaction queries and column semantics, so P05 must not imply that those records or aggregates already exist. The implemented frame preserves the concept's visual weight and empty-state hierarchy without crossing the documented phase boundary.

Reviewed implementation evidence:

- `docs/evidence/admin/p05-staff-login-desktop.png`
- `docs/evidence/admin/p05-admin-dashboard-desktop.png`
- `docs/evidence/admin/p05-admin-dashboard-tablet.png`
- `docs/evidence/admin/p05-admin-navigation-tablet.png`
- `docs/evidence/admin/p05-admin-dashboard-narrow.png`
