# Draft konsep NADI

Pixel-inspected references, 2026-11-05:

- `../../konsep1.png`, PNG 1448 × 1086: Action Board (Management), four attention
  cards (maintenance window, budget decision, repeat failure/RCA, risk acceptance),
  Top 5 Asset Risk and Critical Findings Open tables.
- `../../konsep2.png`, PNG 1448 × 1086: Recommendations, status filter/search, status
  summary cards, and columns ID, Asset, Method, Finding, Recommendation, Risk Impact,
  Target Completion, Status, WO Reference, PIC.

## Implemented now

`/action-board` is a read-only draft layout with four expandable data-requirement
cards, unknown risk-ranking and critical-findings placeholders. No example counts,
asset risk scores, trends, overdue status or person from the reference is copied.
It sits inside Asset → Action Board; Asset → Master Asset retains the real Mart
list/detail. Beranda stays blank.

Its separate WAPPR table reads up to 10 actual maintenance records per page from
the existing canonical API. It validates BSR/IP and exact status WAPPR, strips
unapproved fields, and uses bounded GET requests only. A failed/unverified read
shows an explicit disconnected state. Total is a **record count**, not a count of
unique WO, incidents, losses or failure evidence. No status or source data changes.

`/inspections` is an independent local module, not PdM log book. One simple form
saves a request immediately; its owner Engineer can add inspection method/date,
findings and recommendation on that same draft. Content labels indicate what is
filled, with no approval queue or workflow engine. All records remain drafts.
Reference/summary and a canonical Asset link can be entered; Asset references are
verified on save. Only the reference is stored, never an Asset source payload.

The table/search and summary counters use actual local draft records. The impact
column remains unknown; target dates are user-entered proposals. An optional WO
reference is explicitly manual/unverified and makes no Maximo write. No fake
recommendation, test row or example count is preloaded for users. Browser testing
created one clearly synthetic row and removed only that exact row afterwards.

## Access

Admin manages local users/roles. Engineer creates/edits own inspection drafts.
Supervisor and Manager read. All active roles can read workspace/Asset/Action
Board/local drafts. Admin does not automatically acquire Engineer write rights.
Account and owner authorization is enforced on the server. The old application
accounts, production privileges and collector controls are unaffected.

Four requested local usernames use their matching roles. Their easy-to-remember
initial passphrase is in an ignored mode-0600 local file; the accounts require
local environment plus loopback IP/Host on every request. No secret is in this note.

## Not yet connected

No validated risk method/threshold, weighted reliability score, critical-finding
classification, human-approved RCA linkage, budget authorization, maintenance
window selection, historian correlation, overdue/closure workflow, external
identity, personal-data permission, notification, or external sending is implied.
External requests use nonpersonal references/test data in this development stage.

WAPPR source status is retained as backlog, never an automatic failure/score
input. WO-count Pareto will require explicit work-type, evidence, date, duplicate
and status rules; actual incidents require operational context and human validation.

## Evidence

Foundation extended to 41 hermetic tests / 378 assertions; 32 concept/auth browser
checks plus 16 mapping/WO browser checks. Screenshots and JSON
results: `/tmp/nadi-concepts-qa` (private temporary artifacts). Browser checks
include the four accounts, server denials, real WAPPR pagination, one inspection
to recommendation, and desktop/mobile layouts. No commit/push/deploy.
