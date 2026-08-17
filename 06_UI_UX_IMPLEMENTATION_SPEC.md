# 06 — UI/UX Implementation Specification

## 1. Product experience goals

The interface must help a non-technical Mobile Money user answer four separate questions:

1. What information did the system read from the receipt?
2. Does the receipt appear visually or structurally suspicious?
3. Does the transaction information match an available stored/imported reference record?
4. What should the user do next?

The interface must never collapse these into a single unexplained “fake/real” badge.

## 2. Design principles

- **Clarity over novelty:** plain language, familiar controls and concise explanations.
- **Evidence before verdict:** show the main reasons behind a result.
- **Separate statuses:** risk class and verification status have distinct cards, icons and labels.
- **Privacy by default:** mask full phone/reference values in lists and reports.
- **Progressive disclosure:** users see a simple summary first; detailed evidence is available on demand.
- **No colour-only communication:** every status has text and icon/shape.
- **Recoverability:** upload, OCR and network errors provide a clear next action.
- **Honest uncertainty:** `UNVERIFIED`, `PARTIAL` and low-confidence states are explained.
- **Role-specific complexity:** normal users do not see raw feature vectors; investigators can inspect detailed evidence.
- **Chapter separation:** low-fidelity wireframes remain in Chapter Three; implemented high-fidelity interfaces and screenshots are recorded for Chapter Four.

## 3. Design tokens

Codex must create shared semantic tokens rather than scattering values.

### 3.1 Semantic status tokens

Suggested semantics, not fixed brand colours:

- success / low risk;
- warning / suspicious;
- danger / high risk;
- neutral / unverified;
- info / processing;
- disabled;
- focus;
- surface/background/border/text hierarchy.

A status component includes:

- icon;
- text label;
- semantic colour;
- optional short explanation;
- accessible name.

### 3.2 Typography

- readable body size with dynamic-text support on mobile;
- clear heading hierarchy;
- tabular or aligned numerals for amounts/score;
- minimum touch-target and line-height standards;
- no all-caps paragraphs.

### 3.3 Components

Mobile and web implementations may differ internally but should share terminology:

- `RiskBadge`
- `VerificationBadge`
- `ProcessingStatus`
- `EvidenceReason`
- `MaskedValue`
- `ReceiptThumbnail`
- `ReceiptViewer`
- `ConfidenceIndicator`
- `EmptyState`
- `ErrorState`
- `RetryPanel`
- `PermissionNotice`
- `ConfirmationDialog`
- `AuditTimeline`
- `ModelVersionTag` for staff only
- `Pagination`
- `FilterBar`
- `FormField`
- `Skeleton`

## 4. Mobile information architecture

### Auth stack

- Splash / session restore
- Welcome/Login
- Register
- Forgot Password
- Reset Password
- Terms/Privacy summary when required

### Authenticated tabs

1. **Home**
2. **History**
3. **Upload/Scan** — central primary action or prominent home action
4. **Notifications**
5. **Profile**

Feature routes open above the tabs:

- Receipt Source
- Receipt Preview
- Upload/OCR Progress
- OCR Review
- Analysis Progress
- Result Summary
- Evidence Detail
- Transaction Detail
- Report Preview/Download
- Fraud Report Form
- Help/How Results Work

## 5. Mobile screen specifications

### M01 — Splash and session restoration

**Purpose:** Restore a valid session without flashing protected content.

**Content:**

- product mark/name;
- neutral loading indicator;
- no sensitive user data.

**States:**

- valid session -> Home;
- expired access with valid refresh -> rotate/continue;
- no session -> Login;
- offline with previously known session -> show reconnect guidance, do not pretend protected data is current;
- fatal config error -> support message with request/build ID.

### M02 — Login

**Fields:**

- email;
- password with show/hide;
- remember-device wording only if behaviour is defined.

**Actions:**

- Login;
- Forgot password;
- Create account when registration enabled.

**Requirements:**

- generic invalid-credentials message;
- disabled submit while request is active;
- keyboard-friendly;
- no token or password logged;
- accessible errors tied to fields;
- rate-limit message with safe retry timing.

### M03 — Registration

**Fields:**

- full name;
- email;
- optional phone according to project policy;
- password;
- confirm password;
- consent/terms checkbox only when real policy text exists.

**Feedback:**

- password requirements before submission;
- duplicate email response not over-specific if enumeration policy uses generic messaging;
- successful registration routes according to verification/session policy.

### M04 — Forgot/reset password

- request email;
- generic accepted state;
- token/deep-link reset screen;
- new password/confirmation;
- expired/used token state;
- success -> login or session according to policy.

### M05 — Home

**Primary objective:** Start a new check in no more than three principal actions.

**Sections:**

1. Greeting/profile shorthand.
2. Primary “Check a receipt” button.
3. “How it works” three-step strip: Upload -> Review details -> See risk and verification.
4. Recent analyses (maximum 3–5).
5. Notification/attention card for incomplete OCR review or case update.
6. Small disclaimer that results are automated decision support.

**Empty state:** Explain the first upload without showing fake analytics.

### M06 — Receipt source

Options:

- Take photo;
- Choose from gallery;
- Cancel.

Permission-denied state includes “Open settings” only when platform permits. Explain accepted formats and privacy.

### M07 — Receipt preview and quality check

**Content:**

- zoomable preview;
- replace/remove;
- selected source;
- file-size/quality guidance;
- privacy note.

**Client-side warnings:**

- likely blurry;
- too dark;
- receipt edges not visible;
- very small image.

Warnings do not block unless client detects an obviously unusable file; server remains authoritative.

**Primary action:** Upload and extract details.

### M08 — Upload/OCR progress

Use stages with user-friendly text:

- Securing receipt;
- Improving readability;
- Reading transaction details;
- Preparing fields for review.

Include cancel only if server supports safe cancellation. A background/app resume returns to the persisted transaction.

Error states:

- unsupported/corrupt;
- too large;
- network interrupted;
- storage unavailable;
- OCR unavailable;
- unknown layout.

Each error has a safe retry/replace action and request ID for support.

### M09 — OCR review

This is a critical screen.

**Layout:**

- receipt image at top or switchable pane;
- tap/zoom/pan;
- field form below;
- low-confidence fields first or clearly marked;
- original OCR value available in a non-confusing detail;
- confidence expressed as “Check this field” rather than raw percentages for normal users.

**Fields:**

- provider/network;
- transaction reference;
- amount and currency;
- sender name/phone where present;
- receiver name/phone where present;
- date/time;
- receipt status text.

**Rules:**

- canonical formatting preview;
- mask values in summary but permit the owner to review their own full entered values;
- validation errors explain expected format;
- correction reasons may be automatically captured; user-facing reason field only where useful;
- confirmation creates immutable snapshot.

Before the editable fields, show an immediate **Message-risk preview** derived
from the stored OCR assessment. The card must use text and icon/badge semantics,
not colour alone, and distinguish `High fraud risk`, `Suspicious message`, `No
decisive text signal` and `Text assessment unavailable`. Show only fixed,
plain-language reason summaries. When present, label the rule score `not a
probability`. A no-match state must not say safe, genuine or verified. High and
suspicious states include a concrete pause/official-channel safety action while
the separate final analysis and stored-reference verification remain pending.

**Primary action:** Confirm details and analyse.

### M10 — Analysis progress

Poll the analysis resource and display:

- queued;
- checking reference information;
- checking image consistency;
- running automated fraud checks;
- preparing result.

Do not show a fake linear percentage when stage duration is unknown. Show completed stage count or indeterminate progress.

Support:

- app background/resume;
- network loss/retry;
- partial completion;
- “You may leave this screen; the result will appear in History” when notifications/history support it.

### M11 — Result summary

Order matters.

#### A. Fraud risk card

- label: Genuine / Suspicious / Fraudulent;
- score as supporting information, not the only signal;
- one-line interpretation;
- icon + semantic status;
- “Automated assessment” label.

#### B. Verification card

- Verified / Unverified / Mismatch;
- basis: “Checked against stored/imported reference records”;
- concise field comparison summary;
- never imply live MNO confirmation.

#### C. Main reasons

2–4 top reason cards with:

- plain title;
- short explanation;
- severity;
- optional “See evidence”.

#### D. Recommended next step

Examples:

- low risk + verified: keep/report summary;
- low risk + unverified: confirm through an authorised channel if payment remains uncertain;
- suspicious: compare receipt with wallet/statement or ask for a trusted reference;
- fraudulent/high risk: do not rely on the receipt alone; report for review.

Avoid legal/financial guarantees.

#### E. Actions

- View evidence;
- Download summary;
- Report suspicious transaction;
- Back to Home/History.

#### F. Disclaimer

“MoMo-FDVS provides an automated risk assessment. It does not itself reverse, confirm or complete a Mobile Money transfer.”

### M12 — Evidence detail

User-safe sections:

1. Confirmed transaction details.
2. OCR confidence/fields reviewed.
3. Image checks (plain-language outcomes).
4. Automated model checks (status and high-level result).
5. Reference comparison.
6. Versions/date/request ID in a collapsed technical section.
7. Human review/case status when applicable.

Do not expose:

- other users' duplicate details;
- private object keys;
- raw secrets;
- unbounded raw feature vectors;
- model code paths.

### M13 — History

**List item:**

- date/time;
- masked reference;
- amount;
- provider;
- risk badge;
- verification badge;
- processing/case indicator.

**Controls:**

- search;
- date range;
- risk;
- verification;
- provider;
- status;
- reset filters.

**States:** first-time empty, filtered empty, loading skeleton, retry, pagination/end.

### M14 — Transaction detail

Reconstruct from persisted result:

- receipt thumbnail;
- confirmed details;
- latest risk + verification;
- result timestamp/model/rule versions;
- analysis run history/reanalysis if supported;
- report and case status;
- safe actions.

Historical output must not change when an active model changes.

### M15 — Report preview/download

- explain masked fields;
- display generation/ready/failure state;
- download/share using platform-safe mechanisms;
- do not store report publicly;
- provide report generated timestamp and result version.

### M16 — Report suspicious transaction

Fields:

- category;
- description;
- confirmation that the linked analysis will be shared with authorised reviewers;
- submit.

States:

- existing open case -> open status instead of duplicate;
- success with case ID/status;
- invalid/permission error.

### M17 — Notifications

- unread/read sections or filter;
- type icon and plain title;
- timestamp;
- deep link;
- mark read;
- empty state;
- no full sensitive transaction values in preview text.

### M18 — Profile, privacy and help

Sections:

- profile;
- password/security;
- notification preferences;
- privacy/data explanation;
- “How results work”;
- app version/build;
- logout;
- deletion/deactivation request according to policy.

## 6. Mobile reusable feature modules

Suggested feature folders:

```text
features/
├── auth/
├── receipt-capture/
├── ocr-review/
├── analysis/
├── history/
├── notifications/
├── fraud-reporting/
└── profile/
```

Each contains:

- API hooks;
- screens/components;
- validation schemas;
- query keys;
- tests;
- feature-specific types only where not generated.

## 7. Administrator/investigator portal information architecture

### Shared shell

- skip link;
- header with environment indicator and current role;
- side navigation;
- breadcrumb;
- global session/error handling;
- role-based navigation;
- no hidden-only security.

### Routes

1. Login
2. Dashboard
3. Transactions
4. Cases
5. Users
6. Reference Imports
7. Receipt Templates
8. Fraud Rules
9. Model Registry
10. Reports
11. Audit Logs
12. System Status
13. Profile/Security

Investigators may see a reduced shell: Dashboard, Cases, authorised Transactions, Reports/Profile.

## 8. Web screen specifications

### W01 — Staff login

- organisation/product identity;
- email/password;
- no public registration;
- password reset according to policy;
- generic errors and rate-limit handling;
- environment label for staging.

### W02 — Dashboard

Top summary cards:

- total analyses;
- suspicious/fraudulent count;
- verified/unverified/mismatch;
- open/in-review cases;
- average/p95 analysis time;
- queue/degraded component warning.

Charts/tables:

- analyses over time by risk;
- verification distribution;
- provider distribution;
- cases by status;
- recent high-risk/case queue;
- active model/rule/template versions.

Controls:

- date range;
- provider;
- refresh;
- tabular export where authorised.

Every chart has textual/table alternative and empty/partial-data state.

### W03 — Transactions

Data table columns:

- submitted at;
- masked user;
- provider;
- masked reference;
- amount;
- risk;
- verification;
- processing state;
- case;
- actions.

Features:

- server pagination/filter/sort;
- accessible filter drawer;
- saved filters optional;
- no full receipt displayed in list;
- authorised detail access audited.

### W04 — Staff transaction detail

Sections:

- summary;
- user/receipt information with role masking;
- confirmed OCR;
- risk/verification;
- evidence;
- analysis stages/timings;
- model/rule/template versions;
- linked cases/reports;
- audit access link.

Receipt viewer supports zoom and approved diagnostic variants. It must not load a public URL.

### W05 — Case queue

Columns/cards:

- case age;
- source;
- risk/verification;
- provider/amount;
- assigned investigator;
- status;
- priority;
- last activity.

Controls:

- status/assignment/source/provider/date/risk filters;
- “My cases”;
- claim/start review where permitted.

### W06 — Case detail

Three-column/section design:

1. **Evidence workspace**
   - original receipt;
   - OCR overlays;
   - diagnostic variants;
   - reference comparisons.
2. **Automated findings**
   - risk and verification separately;
   - model status/probabilities as staff evidence;
   - rule triggers;
   - versions/limitations.
3. **Case actions/timeline**
   - assignment;
   - notes;
   - confirm/dismiss/escalate;
   - mandatory reason;
   - generated report.

Destructive/terminal action requires confirmation and current case version to prevent lost updates.

### W07 — Users and roles

- search/filter status/role;
- create staff/user according to policy;
- enable/disable;
- role assignment;
- revoke sessions;
- last-admin safeguard;
- audit history link;
- never display password/reset token.

### W08 — Reference imports

Wizard:

1. Choose file/source label.
2. Upload securely.
3. Validate/preview counts.
4. Inspect errors/download invalid rows.
5. Confirm commit.
6. View imported batch/result.

Show explicitly: “Verification uses the reference data imported here; this is not a live provider connection.”

### W09 — Reference transaction detail/list

- masked default;
- provider/reference/amount/status/timestamp;
- import batch/source;
- authorised raw-row expansion only when needed;
- related verification uses;
- no edit of committed evidential rows; correction is a new import/version or authorised correction event.

### W10 — Receipt templates

- provider/name/version/status;
- draft editor for anchors/regions/regex/config;
- validation against safe fixture;
- activate/retire;
- diff between versions;
- active badge;
- no direct edit of active historical version.

A structured form is preferred to a raw JSON textarea. An advanced JSON editor may exist behind validation.

### W11 — Fraud rules and thresholds

- rule-set versions/status;
- weights and thresholds;
- rule list with reason code, severity and contribution;
- validation checks;
- scenario preview against safe fixture;
- activate/rollback;
- immutable active versions.

UI must warn that changing thresholds affects future analyses only.

### W12 — Model registry

- model type/name/version;
- artifact readiness/hash;
- framework/preprocessing/schema versions;
- measured metrics and dataset scope;
- synthetic-only warning;
- active/retired status;
- verify/activate/rollback actions;
- model card view.

Never provide arbitrary server path entry or executable upload without a controlled artifact-import design.

### W13 — Reports

- analysis/case/operations reports;
- filters;
- status;
- generated by/date;
- authorised download;
- row limit and export audit;
- failed report retry.

### W14 — Audit logs

- actor;
- action;
- target;
- outcome;
- request ID;
- timestamp;
- safe metadata detail;
- filters/pagination;
- no delete/edit;
- export only when authorised and audited.

### W15 — System status

Cards:

- API/build;
- database;
- storage;
- Tesseract;
- worker queue/heartbeat;
- structured model;
- image model;
- notification adapters;
- migration revision.

Clearly distinguish:

- Ready;
- Degraded;
- Unavailable;
- Disabled by configuration.

Do not expose secrets, internal hostnames or private filesystem paths.

## 9. Copy and terminology

Use:

- “Check a receipt”
- “Review extracted details”
- “Fraud risk”
- “Verification status”
- “Checked against stored/imported reference records”
- “Automated assessment”
- “Needs review”
- “Analysis partially completed”

Avoid:

- “100% genuine”
- “Guaranteed fake”
- “Confirmed by MTN/Telecel/AT” without real integration
- “AI knows”
- “No fraud”
- “Bank verified” unless true
- unexplained acronyms in normal-user screens.

## 10. Accessibility requirements

### Mobile

- all touch controls have accessible names/roles;
- minimum practical touch target;
- form errors announced and tied to inputs;
- image alternatives describe purpose, not raw sensitive text;
- dynamic text does not clip;
- focus moves to error/heading after navigation;
- reduce motion where requested;
- status includes text/icon.

### Web

- semantic landmarks/headings;
- skip link;
- keyboard-operable menus/dialogs/tables/actions;
- visible focus;
- dialog focus trap and restoration;
- form labels/descriptions/errors;
- sortable table headers announced;
- charts have summaries/tables;
- contrast checked;
- no hover-only information.

## 11. Responsive test matrix

Codex records exact final viewports, with at least:

### Mobile

- small Android phone;
- common 360–390 CSS/density-equivalent width;
- large Android phone;
- portrait and critical landscape/image-viewer behaviour;
- dynamic font at larger setting.

### Web

- 1280×720;
- 1366×768;
- 1440×900;
- tablet around 768×1024;
- narrow window where supported.

No horizontal document overflow. Wide tables may use contained horizontal scrolling with sticky labels or card alternatives, not overflow the page.

## 12. UI state checklist for every data screen

- initial loading;
- background refresh;
- empty;
- filtered empty;
- success;
- validation error;
- permission denied;
- not found;
- network/server error;
- retry;
- degraded/partial data;
- stale data indicator where relevant;
- destructive confirmation;
- optimistic/pessimistic update behaviour;
- session expiry.

## 13. Visual QA evidence

For each critical screen Codex captures:

- route/screen name;
- role/account used;
- viewport/device;
- build/SHA;
- state represented;
- screenshot path;
- console/runtime errors;
- accessibility notes.

Critical screenshot set:

- mobile login;
- mobile home;
- receipt preview;
- OCR review;
- analysis progress;
- each risk class;
- each verification status;
- partial analysis;
- history/detail/report;
- admin dashboard;
- case queue/detail/decision dialog;
- reference import;
- template/rule/model registries;
- audit/system status.

## 14. UI acceptance journeys

### Journey A — New user

Register -> Login -> Home -> Upload -> OCR review -> Analysis -> Result -> History -> Report.

### Journey B — Verification mismatch

Import reference -> User analyses corresponding edited receipt -> Mismatch displayed separately from fraud risk -> Investigator opens evidence.

### Journey C — Partial analysis

Disable image model -> Analyse -> PARTIAL result explains unavailable component -> Existing evidence preserved -> Status visible in portal.

### Journey D — Human review

User reports -> Investigator starts review -> Adds note -> Escalates with reason -> User receives status notification -> Original automated result unchanged.

### Journey E — Permission denial

Normal user attempts staff route/object ID -> no data leak; staff with wrong role cannot activate models or decide cases.

All journeys must be demonstrated against the final staging/local build and named in the final handoff.
