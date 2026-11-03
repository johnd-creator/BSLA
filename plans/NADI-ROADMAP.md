# NADI product roadmap — main quest

## 1 November 2026 — PdM Sprint2 candidate, no phase advancement

[Sprint2 delivery / issue mapping](../reliability-cockpit/docs/NADI-PDM-SPRINT-02-DELIVERY.md)
implements bounded Register pages, exact native history navigation, honest graph
eligibility and disposable independent-review qualification. Branch is stacked on
unmerged PR114 `aa065af9cef01d8ee3358bcca8fc628ba311ca3a`; main remains
`f1fc4e8b395691a17fe6d986bf14c772d37c1f2c`. One Draft PR; no merge/cutover.
Execution priority: complete candidate CI/review → PO bounded workflow evaluation →
authorized M02 evidence decisions → separately authorized local activation with
fresh controller/session/recovery/backup gates. Real cross-inspection trend remains
NOT_ELIGIBLE. All26 method/comparability decisions and Q01–Q10 remain pending.
Official Phase0–5 and M0–M8 history below is retained; no phase/M02 completion or
new source/KPI implementation is claimed. No Linear issue was created.

## 31 October 2026 — PdM product reset proposal

**Documentation proposal; no implementation, activation or phase completion.**
Verified main f1fc4e8b395691a17fe6d986bf14c772d37c1f2c contains PR105/106/108–112; PR107 remains OPEN. Development runtime is a different local source lokal yang berbeda. Historical entries below, including their “current” wording and source checkpoints, retain their dated scope.

Start with [the Product Owner blueprint](../reliability-cockpit/docs/NADI-PDM-PRODUCT-BLUEPRINT.md). Proposed execution priority: make the existing engineer workflow understandable → bounded frontend presentation Sprint1 → engineer validation/offline crosswalk inventory → contract-first reliability KPI planning. Three pillars: Data Integration, PdM Center, Reliability Performance. Five entry points: Beranda, Aset, PdM Center, Tindak Lanjut, Laporan.

[Roadmap/Linear mapping and Sprint1](../reliability-cockpit/docs/NADI-PDM-ROADMAP-AND-SPRINT-1.md) retains Phase0–5/M01–M07/UX history, existing Engineering/Recommendation/review/audit services and pending F03/field/operational gates. No Linear issues were created. Existing historical archive counts are not inspection counts or canonical evidence; runtime parity must be resolved before any later authorized deployment. Phase statuses are not recertified here.

### Retained historical roadmap and acceptance checkpoints

Latest verified source/data checkpoint: [2–3 November integration](../docs/NADI-NIGHT-INTEGRATION-20261102.md), including the approved closed canonical append. No phase advancement or runtime activation. Historical runtime/policy checkpoints below retain their dated scope.

## Source-free 72h review — 12 Oktober 2026

**Monitoring PARTIAL; product readiness UNKNOWN; Phase 1 CURRENT/PARTIAL.**
Review window8 Oktober21:45:26.619585–11 Oktober21:45:26.619585WIB. Stored WO822/836
full successes, PI304/322full433/433,857paired Mart completion reports. Reconstructed
stale windowsMaximo 6/2190,086s, PI 3/6279,663s; Mart≈105,795s paired-log proxy, exact
per-domain stale durationUNKNOWN. False alerts dan24h reviewUNKNOWN. Latest snapshot
12 Oktober05:36WIB8 PASS/1 UNKNOWN, bukan retroactive72h acceptance.
Effective policies660/660/1800;5legacy/conditionUNSET, no drift. Checkpoint Owner
12 Oktober20:00WIB dan hard expiry13Oktober00:00WIB tetapmanual, tanpaextension/reset.
Main3ad0da8 verified; previewf06abce preserved. Tidak ada source GET/retry/migration/
restart/data/policy change. Earlier sections remain dated historical evidence.

[Full audit, gates, evidence gaps and decision matrix](../reliability-cockpit/docs/nadi-p1-fresh-review-72h.md).

## Current checkpoint — NADI-ENG-INTEGRATION-01 — 2026-10-11

Latest main `cc90fc73bea6ae399383d8538035c6454dc7e65a` is unchanged. Exact unmerged
PR67 `8658c2fbd00bb78f1d8ee2b4462ccece4200a30e` and PR68
`e60ad78620b6f4e34959731090f8f248a35b6414` are integrated in a new candidate,
`codex/nadi-eng-integration-01`. Login presentation and persistent synthetic Case →
reviewed Recommendation → Advisory → authorized Inbox/ACK work together on one
HTTPS3000 preview through the official launcher. QA regression and real source
rollback PASS; final release/serving SHA and exact-head CI are verified at PR handoff.
No PR merge, global authentication, operational distribution or PO/UAT acceptance
is inferred. All existing QA data/schema/session authority and operational services
are preserved. Earlier entries remain dated historical evidence.

Evidence: [Integration report](../reliability-cockpit/docs/nadi-eng-integration-01.md), [screenshots](../reliability-cockpit/docs/evidence/nadi-eng-integration-01/README.md).

## Engineering delivery track — NADI-ENG-BUNDLE-A — 2026-10-11

Product Owner directive NADI-ENG-BUNDLE-A explicitly requests reviewed Engineering
analysis usable by authorized Operations/Maintenance consumers. This extends Phase 4
and depends on Phase 2 cases and NADI-owned recommendations; it is not permission
for actual operational distribution. Main `cc90fc73bea6ae399383d8538035c6454dc7e65a`
is verified. PR67 remains independently OPEN at `8658c2fbd00bb78f1d8ee2b4462ccece4200a30e`.

| Phase / ID | Required capability | Current milestone | Acceptance / dependencies |
|---|---|---|---|
| 2 / ENG-UX-01 | Scoped case register, structured create/edit/detail | PLANNED | Existing server pagination, CaseDraft, idempotency/CAS, no raw JSON input |
| 2 / ENG-UX-02 | Evidence, revision and independent reviewer workflow | PLANNED | Exact asset/evidence references, trusted identity, independent review/history |
| 4 / ADV-01 | Versioned advisory draft/review/in-app QA publication | PLANNED | Reviewed immutable eligible upstream version; independent publication; audit |
| 4 / ADV-02 | Scoped recipient inbox and explicit acknowledgement | PLANNED | Trusted server audience/asset grants; durable events; never claims delivery/work approval |
| 4 / ADV-03 | Existing Action Board/follow-up traceability | PLANNED | Exact case/recommendation/advisory links; reuse local lifecycle, no competing tracker |
| 4 / ADV-04 | Real channels and operational rollout | FUTURE / GATED | Approved identities/consumers, rollout authority, custody and real UAT; no external sending in this bundle |

Phase 2 and Phase 4 remain PARTIAL. Planned, implemented, tested, merged, visible,
PO accepted and operationally accepted remain independent. Isolated authenticated
SYNTHETIC QA is the delivery boundary; no fictitious severity/health/approval.
Phase 1 independent 72h review (11 Oct21:45:26.619585 WIB), owner checkpoint
(12 Oct20:00 WIB) and hard expiry (13 Oct00:00 WIB) remain separate and unchanged.
Existing Phase 0–5 and historical checkpoints below remain authoritative.

## Current product checkpoint — NADI UX Bundle C — 2026-10-10

This is the **official product roadmap**. Phase 0–5 remains intact; the UX track
below complements it. Verified main `cc90fc73bea6ae399383d8538035c6454dc7e65a`
contains merged Engineering PR29–61, PR62, PR63, PR64, Bundle A PR65 and Bundle B PR66. Their merge commits and CI are
in [Repository Status](REPOSITORY-STATUS.md). Older checkpoint language below,
including “current”, “OPEN” and the original phase table, is dated historical
evidence and does not override this reconciliation. No runtime/PO acceptance is
inferred from merge or documentation approval.

| Phase | Current status | Evidence and remaining scope |
|---|---|---|
| 0 — Factual Foundation | **COMPLETE within accepted factual scope** | PR1/release v0.1.0-rc.1; preserve factual semantics |
| 1 — Evidence Expansion | **CURRENT / PARTIAL** | Bounded governed pilot and provisional monitoring; condition freshness and independent reviews remain gates |
| 2 — Collaborative Engineering Workspace | **FOUNDATION MERGED / OPERATIONAL PARTIAL** | PR29–61; persisted isolated QA is not operational activation or actual engineer UAT |
| 3 — Diagnostic & PdM Intelligence | **DESIGN READY / NOT OPERATIONAL** | Existing diagnostic design; approved data, methods, thresholds and ground truth still required |
| 4 — Recommendation Action Loop | **LOCAL FOUNDATION / OPERATIONAL PARTIAL** | Reviewed NADI-owned recommendation/follow-up foundation; effectiveness/operational acceptance pending |
| 5 — Organizational Learning | **PLANNED** | Evidence and accepted outcome history prerequisites |

[PRD](../PRD.md) owns product requirements, [UI spec](../docs/design/NADI-UI-SPEC.md)
owns page design, and [M0–M8](reliability-cockpit-platform/05-roadmap-implementasi.md)
retains scoped engineering sequencing. No completion percentages are inferred.

### Product UI/UX Development track

| Task | Scope | Development status | Merge / acceptance boundary |
|---|---|---|---|
| UX-01 | Single Development Environment | **Development acceptance PASS** | PR62 MERGED via 72b7ec55acbb3d5d9562102c3eaf721d4dda714b; historical HTTPS3000 acceptance retained; PO/operational acceptance separate |
| UX-02 | NADI Design System V1 | **IMPLEMENTED / TESTED candidate** | Shared V1 tokens/primitives and scoped contrast/accessibility regression; PR65 MERGED; PO acceptance pending |
| UX-03 | Sidebar Information Architecture | **IMPLEMENTED / TESTED candidate** | Compatible product navigation, desktop collapse and modal drawer; Engineering placement/PO review pending |
| UX-04 | Executive Overview Visual Polish | **IMPLEMENTED / TESTED candidate** | REF-EXEC hierarchy with supported facts; development review in Bundle A, final PO visual acceptance pending |
| UX-05 | Asset Health List & Detail UI | **MERGED / DEVELOPMENT ACCEPTED provisionally** | Registry filters/page search, six-section canonical detail; original factual evidence/tabs retained; PR66 MERGED; final visual review 12 Oct pending |
| UX-06 | PdM Center UI | **MERGED / DEVELOPMENT ACCEPTED provisionally** | Authorized synthetic QA inspection event/detail/history UI; PR66 MERGED; operational methods/trends NOT ACTIVATED; PR63 Q01–Q10 pending |
| UX-07 | Recommendations & Action Board UI | **MERGED / DEVELOPMENT ACCEPTED provisionally** | Authorized local registers, exact details/history, review/follow-up queues; PR66 MERGED; existing gated commands reused, operational UAT pending |
| UX-08 | Login Page Design Only | **IMPLEMENTED / TESTED candidate** | Existing QA login presentation polished; global enforcement absent; separate Bundle C PR/PO review |
| UX-09 | UI Regression & Visual Acceptance | **PREPARATION / TESTED candidate** | Responsive/state/accessibility and A/B regression evidence; final senior/PO visual acceptance still PENDING |

The Product Owner's Bundle C directive gives provisional development acceptance to
PR66, with final visual review Monday, 12 October 2026. Main synchronization preserved
sessions, fixture records and collectors. [Bundle C readiness](../reliability-cockpit/docs/nadi-ux-bundle-c.md)
records UX-08 implementation and UX-09 preparation; final visual polish remains
correctable and no global authentication or Phase 3 intelligence is activated.

Bundle B source, contract limits, responsive evidence and independent milestone states are in the [Bundle B review](../reliability-cockpit/docs/nadi-ux-bundle-b.md). Implementation does not activate operational PdM or approve method rules.

UX-02/03/04 implementation evidence is in the [Bundle A review](../reliability-cockpit/docs/nadi-ux-bundle-a.md); PO visual acceptance remains separate. UX-04/05 preserve accepted
factual functionality. UX-06/07 depend on engineer contracts and reviewed evidence.
UX-08 can be designed independently and grants no authentication activation.
UX-09 evaluates exact implementation SHA and original references. A specification
created by this task does not mark these delivery tasks complete.

### PdM and Phase1 continuity

PR63 is MERGED. The [PdM requirements packet](../reliability-cockpit/docs/nadi-pdm-requirements-01.md)
owns R01–R08, Q01–Q10 and M01–M07; the preserved dated checkpoint below records
Phase2/3 alignment. Engineer field approval, episodic measurement semantics and
portable/DCS/PI comparability gates remain unchanged. The single frontend uses the
[merged development runbook](../reliability-cockpit/docs/nadi-dev-reset-01.md).
Bundle B selects its reviewed frontend candidate through that launcher. This grants no operational or PdM activation.

[Phase1 acceptance](NADI-PHASE-1-ACCEPTANCE.md) retains its independent 24h/72h
reviews, 12 October20:00 WIB checkpoint and **13 October2026 00:00 WIB hard expiry**.
Operator review outcomes are UNKNOWN in available evidence. This task does not
activate, extend, reset or roll back any policy. Current operational readiness is
not re-certified by documentation or a successful frontend status response.

### Historical checkpoints and original phase backlog

All following checkpoints retain their original evidence, dates and limitations.

## Historical NADI-PDM-REQ-01 — requirements reconciliation — 2026-10-09

Verified main: `f54643f3510bf505628a1400024784faab46e496`, including merged PR61.
Older candidate/open-PR checkpoints below retain historical evidence and are not
current merge-state claims. No runtime acceptance or fresh operational audit is implied.

| Phase | Current checkpoint |
|---|---|
| 0 | COMPLETE for accepted factual scope |
| 1 | CURRENT / PARTIAL; existing evidence gates remain |
| 2 | Foundations MERGED; operational acceptance / engineer UAT PARTIAL |
| 3 | DESIGN READY; not operational |
| 4 | Recommendation foundation implemented; operational acceptance pending |
| 5 | PLANNED |

Phase 2 **PdM Measurement & Investigation** is an explicit candidate backlog:
M01 engineer samples/terminology → M02 approved method/point/instrument contracts
→ M03 irregular-time history → M04 controlled Excel/diagnostic evidence workflow
→ M05 independent interpretation review → M06 informational WO/local recommendation
→ M07 engineer UAT. Secure storage, trusted operational identity and application
provisioning remain dependencies. Field proposals are NOT approved.

Portable measurements are episodic, not assumed daily/24-hour telemetry. Installed
DCS/PI and portable series cannot be combined without approved comparability.
PD is unresolved and must not be equated with DGA; “30% acr” is undefined.
All ten engineer decisions remain PENDING_ENGINEER_VALIDATION. No automatic
threshold, traffic light, score or source write is authorized.

[Engineer statements, requirement traceability, acceptance criteria and validation register](../reliability-cockpit/docs/nadi-pdm-requirements-01.md).
Documentation only; active LiveDev and operational/Phase1 evidence remain unchanged.

## NADI-E-INTEGRATION-02 — local authentication and final audit — 2026-10-09

Main `eda3595a9b8d86726dd0d89192ebf4657b66d27e` unchanged. Bundle E PR51–59 preserved;
E9 PR60 and E10 PR61 extend the OPEN/UNMERGED stack. Local username/password is the
selected initial-QA identity path; enterprise SSO is optional future work.
Tested implementation `1ec149de2d1acd4113987364e1f96c790bfaf63e`.
Argon2id accounts, private operator admin, versioned sessions/RBAC, actual HTTPS
login/workflow and disposable migration006 validated. Audit LOW stale-response
finding repaired; Compose preflight argv and migration docs corrected.
Cockpit687/Maximo181/PI191/contracts14 PASS,0FAIL/0SKIP including11 Timescale;
frontend143/browser40 +legacy25/type/build/32-file safety PASS. Actual source-free
preflight remains NO_GO with unapproved host/policy/storage references.
**Development acceptance PASS; merge READY pending explicit authorization/exact-head CI.**
**Phase1 CURRENT/PARTIAL; Phase2 CANDIDATE/PARTIAL; real QA NO_GO; activation OFF.**
Actual host/TLS, application DB/roles, admin custody/onboarding, reviewed startup and
secure frontend transport, password/session/resource policy, storage/scanner,
PdM fields/UAT and per-action deployment authority remain required. No SSO gate.
No production source GET/write, WO mutation, DB DDL, deployment or Phase1 mutation.
Older test counts/checkpoints below are historical.
[Final audit, tests, activation blockers and merge plan](../reliability-cockpit/docs/nadi-e-integration-02.md).

## Bundle D merged / Bundle E QA preparation — 2026-10-09

PR44–50 MERGED via merge commits; authoritative main
eda3595a9b8d86726dd0d89192ebf4657b66d27e. Older OPEN/candidate statements below
are historical. Bundle E stack51→59 is OPEN/UNMERGED, preparation only.
Dedicated QA architecture, enterprise trust contracts, fail-closed privilege
audit, attachment integrity/recovery, bounded HTTP, source-free preflight, exact
artifact binding and disposable restart/restore rehearsal validated.
Final Cockpit661/Maximo181/PI191/contracts14,11Timescale, frontend127/type/build/
safety and browser25 PASS. No real QA UAT or operational activation.
**Phase1 CURRENT/PARTIAL; Phase2 QA preparation CANDIDATE/PARTIAL; real QA NO-GO.**
Operator allowed naming; actual host/IdP/DB role provisioning/storage/scanner,
reviewed real-QA startup/frontend integration, PdM fields/UAT and explicit
deployment authority remain required. No new production source request/write,
WO changes, DB DDL, deployment or Phase1 mutation.
[Bundle E handoff](../reliability-cockpit/docs/nadi-phase2-bundle-e.md).


## Bundle D final integration review — NADI-D-INTEGRATION-01

Baseline main e836710 unchanged. Stack44→50 remains OPEN; no merge/deployment.
Session cancellation finding corrected6f66ecd in PR48; normal forward merges
preserve ancestry. Final implementation c03e57c; final documents at PR50 head.
Local acceptance Cockpit610/Maximo181/PI191/contracts14,11Timescale, HTTP11,
browser25 +proxy8, frontend110/type/build/safety PASS. Corrected scoped CI run
37892980855 SUCCESS; final PR50 CI must match its exact head before merge.
**Merge candidate READY pending explicit operator authorization.**
**Phase1 CURRENT/PARTIAL; Phase2 QA CANDIDATE/PARTIAL; operational activation BLOCKED.**
PUBLIC/default/schema-owner privilege audit, enterprise identity/deadlines,
attachment storage/recovery/scanner, PdM field approval and operational UAT remain
activation gates. QA proxy streaming caps are a non-operational follow-up.
[Final review, findings and controlled merge plan](../reliability-cockpit/docs/nadi-d-integration-01.md). Older checkpoints
retain historical evidence; no source/production/Phase1 mutation or new acquisition.

## Current development checkpoint — Phase 2 Bundle D

Baseline main `e836710d1984af7a4bfb739bad0bfbbb96d544ca`, Bundle C PR37–43 MERGED.
Tested implementation `ee20307a2664e7ca64737c3f43f1256f26cdf9f6`.
**Development/test acceptance PASS; operational activation BLOCKED.**
**Phase1 CURRENT/PARTIAL; Phase2 integrated QA CANDIDATE/PARTIAL.**
D1–D7 stack adds enterprise identity adapter/session bootstrap, deliberate
application migration ledger/writer grants, private attachment service and real
HTTP/PostgreSQL/frontend workflow. Operational Engineering routes remain unmounted.
No production/source/Phase1 mutation; Maximo/PI strictly READ-ONLY, NADI never
creates or changes Maximo WO. Original accepted runtime is unchanged.

Final local Cockpit600, Maximo181, PI191, contracts14 PASS;11 formerly skipped
Timescale tests now executed in disposable fixtures. HTTP11/browser25/frontend110,
29 safety files/typecheck/build/diff-check PASS. D6 actual GitHub backend/frontend
jobs SUCCESS, run37887690942. Security diff review found no concrete reportable
issue in15 changed source/config surfaces; production IdP/storage not certified.
Real enterprise IdP/directory, existing-store provisioning/privilege approval,
secure storage/scanning, PdM engineer field sign-off and operational UI/UAT remain
external activation gates. QA command editor is not final engineering form UX.
[Bundle D acceptance and activation manifest](../reliability-cockpit/docs/nadi-phase2-bundle-d.md) records the exact stack,
recovery proposal, test evidence and limits. Next: senior stack review, then
separately authorized identity/provisioning/field UAT. Older checkpoints below
retain historical measured evidence; they are not re-certified by this bundle.

## Current development checkpoint — Phase 2 Bundle C

Verified main `7a846ef2c7e25306f23da99dd011e1d54aa8f4a4`, BundleB PR30–36 MERGED.
**Phase1 CURRENT/PARTIAL; Phase2 CANDIDATE/PARTIAL; operational activation OFF.**
Stacked C1–C7 candidates add same-asset local context/maintenance chronology,
reviewed manual inspection evidence, case-linked recommendations and independent
local completion verification, integrated development-only concept screens and
trusted-session/PostgreSQL acceptance. Maximo/PI remain strictly source READ-ONLY;
NADI recommendations never create/update/close/approve/cancel Maximo WOs.

Local validation: Cockpit532 PASS (all disposable PG/Compose), Maximo181 PASS,
contracts14 PASS/35schemas, PI180 PASS/11 isolated Timescale SKIP;100 frontend
assertions,27 safety files,40 browser assertions, TypeScript/build/diff-check PASS.
No production access, DB/DDL, deployment, source acquisition or Phase1 mutation.
Enterprise identity/bootstrap, deliberate application provisioning/migration ledger,
PdM engineer fields, secure storage and operational UI integration/UAT remain BLOCKED.
Candidate UI is browser-memory DEMO only; no operational writer route is mounted.
Do not mark Phase1 or Phase2 COMPLETE. Historical operational evidence, GOV03 policy
approvals/checkpoints/expiry and accepted condition evidence are unchanged and not
re-certified by this software task.
[Bundle C report, stack and handoff](../reliability-cockpit/docs/nadi-phase2-bundle-c.md)
Next: trusted enterprise bootstrap/provisioning contracts → engineer field approval
→ operational UAT. New Maximo coverage requires separate collection authorization.


## Current development checkpoint — Phase 2 Bundle B

Main `02e887c56057611f112b7b652ba9a9aee8b382ea`, corrected PR29 MERGED.
**Phase 1 CURRENT/PARTIAL; Phase 2 CANDIDATE/PARTIAL; activation OFF.**
B1–B7 implement source-boundary policy/coverage, trusted identity/session adapters,
bounded local WO context, Manual PdM envelope, NADI-native recommendations,
development-only concept lab and isolated integrated acceptance. Maximo/PI remain
strictly source read-only. A recommendation is not a WO or maintenance authorization.
No production source GET, DB/DDL, deployment, activation or Phase-1 evidence mutation.

Local evidence: Cockpit 462 pass (isolated PG + Compose), Maximo 181 pass,
contracts 14 pass, PI 180 pass/11 fixture skips; frontend 25+37 assertions,
product safety/typecheck/build and 24 browser checks pass. Enterprise provider,
reviewed session bootstrap/provisioning/migration ledger, engineer-approved method
fields, directories and operational UI/UAT remain required. No phase is marked COMPLETE.
[Bundle report and review stack](../reliability-cockpit/docs/nadi-phase2-bundle-b.md) records limitations and migration/rollback proposals.
Next: trusted enterprise identity + PdM field sign-off + reviewed application
provisioning/backend integration. Earlier runtime checkpoints below are historical;
GOV03 approvals/checkpoints/expiry are unchanged and are not re-certified here.


## Current development checkpoint — overnight Engineering bundle 01

Baseline PR28 MERGED, main `e67c641e23214bf8851a05d312e1426c1e471ec3`.
**Phase 1 CURRENT/PARTIAL; Phase 2 IN DEVELOPMENT; Phase 3 DESIGN READY.**
Source-free candidate adds typed human cases, attributed independent review,
transactional audit/idempotency/concurrency, bounded local canonical references,
disabled isolated API contracts and an explicitly synthetic development-only UI.
Production write routes remain unmounted: trusted application identity/RBAC/session
and application writer/migration provisioning are BLOCKED, not simulated as users.
RCFA identity/Data Trust provider and operational UAT remain explicit gaps.

[Morning acceptance](../reliability-cockpit/docs/nadi-phase2-overnight-bundle-01.md)
and [Phase 3 design](../reliability-cockpit/docs/nadi-phase3-diagnostic-foundation.md)
record exact available tests and readiness. No source request, operational DB write,
deployment, worker/env/grant change or new operational database. Accepted R3 evidence,
GOV-03 policies/checkpoints/expiry and Phase-1 semantics remain untouched. This
checkpoint authorizes development reporting only; historical runtime evidence below
is not replaced by a new observation. Next: **NADI-PH2-02 — Trusted Engineering
Identity & Activation Contracts**. Do not mark Phase 2 COMPLETE or diagnostics live.

## Current runtime checkpoint — NADI-P1-FRESH-GOV-03 (8 October 2026)

**PASS — temporary internal monitoring ACTIVE; Phase 1 CURRENT/PARTIAL.**
Fauzi authorized MAXIMO_WO=660s, MART_FACTUAL=660s, PI_COLLECTOR=1800s as
project owner/accountable internal technical approver. External endorsements are
not required or claimed. Legacy and both condition policy settings remain UNSET.
Original 8 October owner approval stays DATE_ONLY; historical GOV02 is preserved.

Actual activation `2026-10-08T21:45:26.619585+07:00`; 24h review
`2026-10-09T21:45:26.619585+07:00`; 72h review `2026-10-11T21:45:26.619585+07:00`.
Explicit owner-revised hard expiry **2026-10-13T00:00:00+07:00**.
Fauzi confirms **12 October 20:00 WIB** checkpoint and rollback before expiry
without an approved extension. Enforcement is manual; no automatic scheduler.

Main `1f7c25a711e68afc87ee0c4b1322bfca4be6ba97` / PR27 MERGED; actual serving SHA `1cf7fed971594581913e8e7f635691f834133b6e`,
application source identical to main. Same-image API replacement only; other 22
containers preserved. R3 evidence/timestamps, VERIFIED1/PROPOSED0, approved signal1,
latest/state1/1 and 433 active technical attributes unchanged; source GET0.
Initial readiness **8 PASS / 1 UNKNOWN**. Final observation **7 PASS / 1 PARTIAL /
1 UNKNOWN**, overall UNKNOWN, require-pass exit2: unchanged background PI worker
completed 432/433 with 1 error; prior full-cycle success is preserved. No retry/probe.
Condition freshness acceptance remains outstanding; technical BAD_QUALITY18/epoch
anomalies remain visible and are independent of collection freshness.

[Activation and rollback evidence](../reliability-cockpit/docs/nadi-p1-fresh-gov-03.md)
and [migration handoff](../reliability-cockpit/docs/nadi-pre-migration-readiness-gov-03.md)
record remaining operator reviews, manual expiry risk and separately authorized
future cutover. No server migration, condition refresh/replay, DDL or approval changes.
Earlier sections below are historical and do not override this checkpoint.

Public SEC01 audit preserves approval scope, dates, thresholds and recorded readiness;
host-specific deployment and executable recovery details are retained privately.
Sanitization changes documentation only; runtime and accepted evidence are unchanged.
Git history is retained, so earlier public revisions remain accessible.

## Historical owner decision — NADI-P1-FRESH-GOV-02 (8 October 2026)

**PROJECT_OWNER_APPROVED**: Fauzi approved MAXIMO_WO=660s, MART_FACTUAL=660s,
PI_COLLECTOR=1800s for provisional monitoring; both condition policies stay UNSET.
This is conversational authorization reported directly in the user-supplied task,
not digitally signed or externally authenticated approval. Three component
endorsements remain PENDING; **ACTIVATION_NOT_AUTHORIZED / GOV-03 NOT EXECUTED**.

[Approval register and handoff](../reliability-cockpit/docs/nadi-p1-fresh-gov-02.md)
preserve the historical proposal, named reviewer gaps, date-only approval precision
and expiry rule. Calendar expiry reference is 15 October 2026; exact expiry instant
is NULL until approval-time/timezone evidence or explicit expiry clarification.
Activation, 24h/72h review dates remain NULL. No duplicate owner approval requested.

All eight runtime policies remain UNSET; R3 evidence/journal preserved. Actual
readiness 5 PASS / 4 UNKNOWN; hypothetical 8 PASS / 1 UNKNOWN; overall UNKNOWN. Phase1
CURRENT/PARTIAL, not COMPLETE. Next: component endorsements, exact expiry
resolution, reviewed release and separately authorized controlled GOV-03 activation.
No source GET, policy change, operational mutation or deployment occurred.

## Historical decision package — NADI-P1-FRESH-GOV-01 (8 October 2026)

**PASS: ready for owner review. Policies are not activated; approvals PENDING.**
Reviewed/serving release `1cf7fed971594581913e8e7f635691f834133b6e` includes PR26.
Accepted R3 real Coal Flow A evidence 54.84218978881836 Ton/h, original source/
collection/projection times and strict replay are preserved. VERIFIED=1 / PROPOSED=0,
approved signal=1, latest/state=1/1; all eight freshness settings remain UNSET.

[Engineering decision package](../reliability-cockpit/docs/nadi-p1-fresh-gov-01.md)
evaluates nearly 24h of local evidence: 278 WO attempts / 273 successes; 287 paired Mart
completion reports; 104 PI runs / 99 full 433/433 successes. Proposes 660/660/1800 seconds for
**provisional monitoring pending named owner/reviewer approval**, with proposed
7-day expiry. Condition source/projection remain DEFERRED: two manual samples
cannot establish cadence or acceptable use-age. No source GET/acquisition/replay,
production mutation, activation or restart occurred.

Source-free fourteen-case simulation passes; targeted 45 tests PASS / 9 PostgreSQL skips.
Actual readiness remains 5 PASS / 4 UNKNOWN, overall UNKNOWN. Hypothetical three
monitoring policies yield 8 PASS / 1 UNKNOWN, leaving product acceptance UNKNOWN. Phase 1 remains
**CURRENT/PARTIAL — FRESHNESS_POLICY_PENDING**. Next: accountable owner decision,
then separately authorized controlled activation; condition policies need further
engineering evidence. BFPT frozen/KKS issue unchanged. Earlier sections are
historical checkpoints, not current policy activation instructions.

## Latest runtime promotion — NADI-IDN-002B-R1-FIX-01 (8 October 2026)

**PASS — bounded first real Coal Flow A evidence pilot.** PR22 MERGED;
authoritative source `478cce1958ab5800ce21d7b1e93b83ff43c1ac19` deployed to
Cockpit API/operator tooling only. No application repair or unmerged code was
needed. Existing control checkout, private configuration and all accepted
worker/PI/web/DB images remain preserved. Image ID plus serving-source checksum
prove the reviewed 512-character contract; actual 203 and synthetic 512 accepted,
513 rejected. Historical Compose revision label is not the image source SHA.

Fauzi's existing 2026-10-08 approval for precisely Coal Flow A / `coal_flow`
is now persisted through canonical administration. Exactly one approved signal,
one latest condition evidence and one projection state; VERIFIED mapping 1 /
PROPOSED 0 unchanged. No new identity review or approval was requested.
Five guarded current-source GETs (six cumulative including R1 identity GET)
produced NUMERIC evidence with original `Ton/h`, time/quality/lineage; four
canonical schema/model checks passed. Real replay writes 0 and preserves every
condition row, source/projection timestamp, state and API document.

[Operational evidence](../reliability-cockpit/docs/nadi-idn-002b-coal-feeder-a.md#r1-fix-01--reviewed-runtime-promotion-and-first-real-evidence)
records backup, immutable image, counts, actual response, replay, API/UI and
all nine gates. Coverage 845 registered / 1 VERIFIED / 1 approved-signal asset /
1 projected asset. Source policy remains blank; Good is signal quality only.
Actual readiness: governance/schema/identity/selection/status PASS; three
collector/Mart freshness gates UNKNOWN; projection gate UNKNOWN due
UNKNOWN_SOURCE_OR_PROJECTION_FRESHNESS. Overall UNKNOWN, require-pass exit 2.
The measured real projection is accepted; freshness-qualified readiness is not.

**PHASE 1 SOFTWARE RUNTIME FOUNDATION: ACCEPTED.**
**BOUNDED REAL PILOT: ACCEPTED.**
**PHASE 1 PRODUCT ACCEPTANCE: NOT PASS — FRESHNESS_POLICY_PENDING.**
Phase 1 remains CURRENT/PARTIAL. Identity approval, signal approval, bounded
canary, controlled handoff and real replay are complete for this one asset only.
Other equipment identities remain unverified. The live technical inventory
remains 433 active; technical BAD_QUALITY 18 and epoch timestamps are independent
of this Good pilot evidence. PI_AF_KKS_LOOKUP_UNRESOLVED remains open;
BFPT stays REJECTED/FROZEN/DO NOT VERIFY.

Task-attributable mutations: one signal selection and one evidence/state batch;
replay 0 writes, mapping mutations 0, source writes 0. Collector/web restarts,
DDL/history/discovery/registry/reset/volume recreation/new operational DB,
CEMS/NK changes and credential exposure 0. Only cockpit-api replaced once;
22 other existing container identities remain unchanged. No recurring condition
projection was enabled. No unnecessary repair PR; documentation checkpoint
is separate from deployed source. Earlier checkpoints below are historical.

Next: approve defensible collector/source/projection freshness policies and
controlled refresh/acceptance procedure, then rerun actual readiness without
weakening gates. No new mapping, broader signal selection or health scoring
is implied by this successful one-signal pilot.

## Historical R1 checkpoint — signal approved, runtime contract repair pending (8 October 2026)

**PARTIAL — CODE_ACCEPTANCE_REQUIRED.** Fauzi directly approved exactly one
Coal Flow A / `coal_flow` signal on 2026-10-08, evidence reference
`NADI-SIGNAL-COAL-FLOW-A-20261008`. Human signal approval is now RECEIVED.
One exact guarded Attribute metadata GET proved ownership by the existing
VERIFIED Coal Feeder A AF Element. NUMERIC and local source unit `Ton/h` are
preserved; no unit conversion, engineering SLA or Hidayat signal approval is claimed.

Canonical production approval failed before DML: the exact Attribute WebId has
203 characters, exceeding the merged contract's 200-character limit. PR22
contains an additive, bounded 512-character Attribute-reference correction,
consistent Python/JSON contracts and synthetic SQLite/PostgreSQL/API acceptance.
No candidate application code was deployed. This is a concrete independent
SOFTWARE/RUNTIME blocker for this pilot; historical foundation acceptance below
remains evidence of its earlier bounded validation.

Production remains PROPOSED=0 / VERIFIED=1, selected signals=0, condition
latest/state=0/0. Source canary/handoff/projection/replay NOT RUN. R1 PI source
GET=1 (identity metadata), Maximo GET=0; business writes/mapping mutation/
signal persistence/projection/deployment/restart/DDL=0. Blank freshness policies
remain UNKNOWN / FRESHNESS_POLICY_PENDING. Identity gate PASS for this pilot,
signal/projection BLOCKED NO_APPROVED_SIGNALS; overall readiness BLOCKED.
**PHASE 1 PRODUCT ACCEPTANCE: BLOCKED; Phase 1 CURRENT/PARTIAL.**

[Full R1 evidence and test commands](../reliability-cockpit/docs/nadi-idn-002b-coal-feeder-a.md#r1--explicit-coal-flow-a-signal-approval-8-october-2026)
records 440 distinct Cockpit/PI/contracts test cases passing across isolated
fixtures and opt-in environments. Accepted runtime, 433 active PI attributes,
Maximo recovery floor and SELECT-only reader are preserved.
PI_AF_KKS_LOOKUP_UNRESOLVED stays open; BFPT REJECTED/FROZEN/DO NOT VERIFY.

Next: review/merge PR22's compatible contract repair, deliberately deploy reviewed
compatible consumer/operator tooling with accepted overrides, then resume the
already authorized one-signal approval → bounded governed canary → schema-valid
handoff → Mart projection/replay → API/UI/readiness. No repeat human approval is
required for the recorded scope. Approve freshness policy separately before
claiming final Phase-1 PASS. Earlier checkpoints below are historical.

## Historical pilot checkpoint — NADI-IDN-002B (8 October 2026)

[Coal Feeder A evidence](../reliability-cockpit/docs/nadi-idn-002b-coal-feeder-a.md)
records **PARTIAL**: one BSR/IP CS01 Coal Feeder A mapping is VERIFIED via
canonical dry-run → PROPOSED → explicit human-review transition.
`verified_by=Fauzi`; technical reviewer Hidayat, System Owner Boiler / Senior
Engineer, in-person verbal MATCH reported by operator on 2026-10-08.
No signed artifact or direct engineer authentication is claimed.
Production PROPOSED=0 / VERIFIED=1, ambiguity=0, approved signals=0, condition evidence=0.
**SIGNAL_APPROVAL_PENDING**: exact local Coal Flow A reference identified,
accountable meaning/use approval pending; canary/projection not run, source GET=0.
Identity gate PASS for this pilot; signal/projection BLOCKED NO_APPROVED_SIGNALS.
Maximo/Mart/PI freshness UNKNOWN with blank policy; governance/schema/status PASS.
**PHASE 1 PRODUCT ACCEPTANCE: BLOCKED**, Phase 1 CURRENT/PARTIAL.
HUMAN_CROSSWALK_REQUIRED is resolved for this one asset only; other identities
remain unverified. PI_AF_KKS_LOOKUP_UNRESOLVED is separate and unchanged;
BFPT REJECTED/FROZEN/DO NOT VERIFY. No runtime redeploy/DDL or source changes.
Next: one accountable signal approval → bounded governed canary → accepted
handoff/idempotent projection, plus approved freshness policy and actual readiness.
Older checkpoint populations below are historical as of their respective audits.

## Current Phase-1 runtime acceptance — 2026-10-08

PR20 MERGED; exact main `c2fb0fc686396e79c19f42af46694673827493a9` deployed
for PI API, NADI API and UI. Existing control checkout/accepted overrides,
workers, projector and DB volumes remain preserved. See
[operational acceptance](../reliability-cockpit/docs/nadi-phase1-runtime-acceptance-001.md)
and [authoritative Phase-1 matrix](NADI-PHASE-1-ACCEPTANCE.md).

**PHASE 1 SOFTWARE RUNTIME FOUNDATION: ACCEPTED.**
**PHASE 1 PRODUCT ACCEPTANCE: BLOCKED.** Phase 1 stays **CURRENT / PARTIAL**.
Existing Mart canonical002/003/004 ready; validated private full backup and
17 locked factual count/content comparisons passed. The dedicated Mart reader remains
SELECT-only, including three empty condition relations. PI local stored-data
observation and NADI integration-status/Data Trust/Asset condition panels live.
Readiness: governance/condition-schema/status PASS; collection/projection freshness
UNKNOWN because **FRESHNESS_POLICY_PENDING**; identity/selection/projection BLOCKED
with **HUMAN_CROSSWALK_REQUIRED**. Registry845, PI active433, mapping0/0,
approved signals0 and projected evidence0. Technical BAD_QUALITY18 remains visible;
a complete collector cycle does not prove source freshness or equipment health.

NADI-IDN-002 human crosswalk remains BLOCKED / EXTERNAL; BFPT remains
REJECTED / FROZEN / DO NOT VERIFY. Runtime is ready for NADI-IDN-002B **when a
controlled human MATCH becomes available**, then attributable human verification
and separately authorized bounded governed canary. Approved signal semantics,
engineering freshness/quality policy and real bounded projection remain subsequent
product prerequisites. No production source GET/mapping/signal/projection was
initiated by runtime acceptance. Documentation/evidence PR remains OPEN/UNMERGED.

GitHub already marked PR19 MERGED separately; this differs from expected
superseded/unmerged metadata. Its211faec commit is already an ancestor of required
main; executor merged neither PR and did not deploy PR19 separately.
Older checkpoints below preserve historical evidence and do not override this state.

## Historical overnight bundle checkpoint — 2026-10-08

NADI-PHASE1-OVERNIGHT-BUNDLE-01 branches from exact unmerged PR #19 HEAD
`211faec4b0916361491d3ca8bc01ada2f0072284`, with authoritative main unchanged at
`f8c37f068102a06906cb3ca464fe08745e0351cf`. PR #19 remains OPEN/UNMERGED and its
branch is untouched. The new bundle includes that foundation and supersedes
PR #19 **only if the bundle is accepted**. Neither PR is automatically merged.

[Authoritative Phase-1 acceptance](NADI-PHASE-1-ACCEPTANCE.md) distinguishes
candidate software tests from operational deployment and human/data acceptance.
B0 freshness wiring, B1 integration status/Data Trust, B2 synthetic PostgreSQL
projection acceptance and B3 read-only Phase-1 preflight are implemented candidates.
NADI-IDN-002 human crosswalk remains BLOCKED / EXTERNAL; verification PENDING.
Production PROPOSED0 / VERIFIED0 remain unchanged; BFPT stays REJECTED / FROZEN.

**PHASE 1 SOFTWARE READINESS: PASS (candidate, bounded bundle scope)**
**PHASE 1 PRODUCT ACCEPTANCE: BLOCKED**
External identity blocker: **HUMAN_CROSSWALK_REQUIRED**. It is not the only
outstanding product prerequisite: reviewed runtime deployment, existing-Mart
condition migration 004/reader grants, explicit freshness policy, approved pilot
signals and real governed evidence acceptance are still required. No operational
condition migration or projection was performed. Phase 1 remains CURRENT / PARTIAL.
Next: senior bundle review; separately authorized runtime acceptance can proceed
independently of human crosswalk. With controlled MATCH evidence, execute
NADI-IDN-002B human verification/governed canary, then approved bounded projection.

## Historical NADI-ING-PI-001A checkpoint — 2026-10-07

PR #18 MERGED; baseline origin/main `f8c37f068102a06906cb3ca464fe08745e0351cf`.
[NADI-ING-PI-001A](../reliability-cockpit/docs/nadi-ing-pi-001a.md) implementation
**CURRENT / candidate**, synthetic acceptance **PASS**: explicit separately
approved selected signals, governed collector boundary, canonical typed evidence,
additive latest-only existing-Mart migration, read-only API/Asset view and four
independent freshness dimensions. No production deployment/projection is claimed.

NADI-PI-001 ✅ MERGED; NADI-PI-RUNTIME-001 ✅ ACCEPTED;
NADI-RUNTIME-002 ✅ ACCEPTED. NADI-IDN-002A R1/R2 evidence rounds are completed;
NADI-IDN-002 human crosswalk **BLOCKED / EXTERNAL**, human verification PENDING.
PROPOSED0 / VERIFIED0 remain unchanged. BFPT stays REJECTED / FROZEN.
Task source GET/write0, no operational DDL/restart/new DB. Phase 1 remains
**CURRENT / PARTIAL**. Next: **NADI-INTEGRATION-STATUS-001**. Real governed PI
projection still requires human identity plus signal approval and deployment review.

NADI — **Navigasi Analitik Data dan Informasi**, Reliability / Engineering
Intelligence Platform pembangkit. Implementasinya berada di
`reliability-cockpit/`; shared collectors tetap menjadi kemampuan platform.
Basis audit awal: `main ef07a26`, 7 Oktober 2026; FIX-01 direkonsiliasi dengan
`main 3e981a3` setelah PR #12/#13/#14 merged; runtime evidence ada pada NADI-PI-RUNTIME-001. [Repository Status](REPOSITORY-STATUS.md)
memuat full SHA, merged PR dan pekerjaan di luar `main`.

## Product phases

| Phase | Scope | Status |
|---|---|---|
| 0 — Factual Foundation | Maximo → canonical contracts → Mart → factual NADI views | **COMPLETE**, release faktual `v0.1.0-rc.1` |
| 1 — Evidence Expansion | source semantics, governed identity, PI evidence dan integration trust | **CURRENT / PARTIAL** |
| 2 — Collaborative Engineering Workspace | investigation, evidence, collaboration, review dan decision history | **PLANNED** |
| 3 — Diagnostic / PdM Intelligence | finding, patterns, diagnostic assistance, explainable PdM | **PLANNED**, evidence-gated |
| 4 — Recommendation & Action Loop | engineering review → action → existing maintenance → effectiveness | **PLANNED**, no implicit source write-back |
| 5 — Organizational Learning | accumulated engineering knowledge and maintenance outcomes | **PLANNED** |

### Phase 0 — completed factual scope

PR [#1](https://github.com/johnd-creator/reliability-knowledge-starter/pull/1)
merged as `af1d9bd`; tag `v0.1.0-rc.1` resolves to that commit and is an ancestor
of the audited `main`. Canonical contracts (`28a0d47`), Mart persistence
(`6ec2b22`, `9e6f2b5`), Mart queries (`7576214`), and local projection (`fa1bc05`)
are also on `main`.

The nine factual routes cover Executive Overview, Asset Reliability,
Maintenance, Maintenance Investigation, FMEA, RCFA, Asset Health, Overhaul and
Data Trust. Release QA evidence is in
[NADI V1 Release Candidate](../reliability-cockpit/docs/nadi-v1-release-candidate.md)
and [Product Readiness](../reliability-cockpit/docs/nadi-v1-product-readiness.md).
QA was recorded for that release; it is not rerun or a live-runtime certificate
by this documentation task.

Completeness is scoped: Registered Reliability Assets, local Collector
projection, controlled Mart populations and technical context remain distinct.
Repeat Activity is not Repeat Failure. Health/Wellness/Risk scores, RPN,
reliability failure KPIs and PdM remain gated. Legacy KPI code does not unlock
these metrics in the factual NADI decision surface. Runtime wiring debt remains
even though product foundation was accepted.

### Phase 1 — evidence already merged

Discovery completion means the bounded work was performed and its findings
recorded, not that all business semantics became verified.

| Workstream | Git evidence | Implemented evidence / remaining boundary |
|---|---|---|
| Asset Health discovery | PR #2, `6687f07` | MX-013A/B: Engineering Judgement metadata advanced; report lineage and Wellness/ACR/MPI meanings still partial/unknown |
| FMEA item discovery | PR #3, `596d799` | IPFMEAITEM → FMEA parent verified; item semantics/RPN policy and product projection not accepted |
| Maintenance failure semantics | PR #4, `44868d8` | Direct WO fields observed; governed failure identity/hierarchy and Repeat Failure still unknown |
| RCFA relationships | PR #5, `2c73b03` | Direct source Asset field and RCFA→FDT verified; NADI canonical Asset link remains unresolved; WO/failure-event meaning not verified |
| DOMINION Overhaul | PR #6, `2163be2` | Inspection and Scope-PM/WO paths advanced; KPI/progress/completion semantics still incomplete |
| Central PI topology + identity investigation | PR #7, `74e5dc3` | AF→PI Point and timestamp/quality/unit shapes verified in bounded samples; native Maximo→AF key not found in bounded probe |
| Maximo WO recency | PR #13/#14, main `52c67d4` | Bounded floor recovery, automatic cursor, cheap scheduled reads, local Mart and registered BSR/IP NADI CURRENT; MXR-004 moving-source/global concurrency remains PARTIAL |
| Governed Asset↔AF registry | PR #8, `1c24a78` | Existing Mart relation, explicit lifecycle, UNMAPPED/MAPPED/AMBIGUOUS resolution |
| Governed PI source adapter | PR #12, `3e981a3` | MERGED; lineage/origin guards and typed quality evidence; governed pilot/projection remain pending |
| Controlled mapping administration | PR #9, `883534c`; PR #10, `ef07a26` | Atomic PROPOSED import, human verify/retire, provenance; SQLite timestamp test correction merged |

Source findings are detailed in the linked
[Repository evidence catalog](REPOSITORY-STATUS.md#merged-evidence-catalog).
New discovery has not been projected into every canonical contract or product
view. Update those boundaries through separate reviewed technical changes;
never overwrite unknowns from labels or branch existence.

### Current controlled identity checkpoint — 2026-10-07

PR #17 MERGED14:00:31 UTC; fresh main
`83c529fd2d9ea5e3d3233f8d3b6025937a97054f`. NADI-PI-001 ✅ MERGED;
NADI-PI-RUNTIME-001 ✅ ACCEPTED; NADI-RUNTIME-002 ✅ MERGED / runtime ACCEPTED.
[Round1](../reliability-cockpit/docs/nadi-idn-002-pilot.md) remains preserved.
[NADI-IDN-002A-R2](../reliability-cockpit/docs/nadi-idn-002-round2.md): local exact
identity search then PI25/30 GETs and Maximo3/10 exact scoped GETs. Three
hypotheses remain INSUFFICIENT_EVIDENCE; BFPT stays REJECTED/FROZEN. AF KKS has
an ASSETNUM lookup expression, but no usable result or governed table authority.
No confirmed bridge, replacement, dry-run/import or production verification.
PROPOSED0 / VERIFIED0. Evidence/proposal **PARTIAL**, human verification **PENDING**.
**HUMAN CROSSWALK REQUIRED**: three-row MATCH/NOT_MATCH/UNKNOWN packet requires a
responsible reviewer/date/controlled evidence naming both exact identities.
NADI-IDN-002B follows qualified proposals and human verification; production
canary cannot start now. Phase1 stays **CURRENT / PARTIAL**.

### Phase 1 — remaining acceptance

- NADI-PI-001 governed PI source boundary is **MERGED** via PR #12 in
  `main 3e981a3`. NADI-PI-RUNTIME-001 applied migration 004 to the existing PI
  Timescale store, verified stored API and one technical source GET, and wired
  one snapshot owner. Operator/Compose changes are merged via PR #15; accepted
  runtime provenance and overrides remain distinct from source-controlled wiring. [Runtime evidence](../pi-collector/docs/nadi-pi-runtime-001.md).
- NADI-RUNTIME-002 reconciled the accepted existing Mart schema/runtime via
  merged PR #16: `asset_af_mapping` exists, mappings remain zero, NADI uses the
  dedicated reader. Preserve that store and the separately authorized writer.
- Approve a bounded real/pilot Registered Asset ↔ AF mapping set. Code and
  synthetic tests do not establish that production mappings are populated.
- Project PI measurement evidence into NADI with identity lineage, units,
  source timestamp and quality flags; define authorization and failure behavior.
- Make coverage, unmapped/ambiguous, stale/degraded and integration status
  visible without substituting business-record dates for collection freshness.
- Resolve required Mart deployment wiring and read-only role/migration readiness
  before pilot operation. Do not create a new Mart DB.
- Record Phase 1 acceptance against a scoped pilot, source-access authorization,
  quality/time rules, failures, contract compatibility and engineering review.
  Do not open diagnostic/scoring capabilities merely to finish this checklist.

### Phase 2 — collaborative engineering workspace

```text
problem → asset workspace → collect evidence → engineering investigation
        → collaboration / peer review → published engineering insight
        → decision log
```

The existing factual Asset workspace is a foundation, not implementation of
this collaboration lifecycle. Later work defines ownership, evidence snapshots,
versions, access control, review and publish rules. Investigation and decision
history must remain attributable and survive recomputation. No workflow tables,
forms or write endpoints are added by this roadmap task.

### Phase 3 — diagnostic / PdM intelligence

```text
Trend Detection → Condition Finding → Failure Pattern
                → Diagnostic Assistance → PdM Insight → Asset Health / Risk
```

Prerequisites: accepted measurement semantics, mapped evidence, units, time
alignment, quality/freshness rules, versioned thresholds/model, validation and
explainability. Missing/bad/stale data must not imply healthy equipment.

### Phase 4 — recommendation and action loop

```text
Finding → Recommendation → Engineering Review → Action
        → Existing WO / Maintenance → Execution → Closure → Effectiveness Review
```

Actions may refer to existing Maximo Work Orders. Direct creation/update of
Maximo WO requires a separately authorized and governed write-back architecture;
this vision does not authorize it. Human decisions must not be overwritten by
recomputed recommendations.

### Phase 5 — organizational learning

Equipment and failure history + PI condition + FMEA + RCFA + investigations +
recommendations + maintenance results become organizational reliability
knowledge. Preserve provenance, evidence versions, review decisions, outcome
feedback and reusable engineering insights. This is a long-term product goal,
not an already deployed knowledge engine.

## Next execution sequence

### 1. NADI-PI-001 MERGED; NADI-PI-RUNTIME-001 runtime checkpoint

PR #12 merged at `2026-10-07T10:27:39Z`, merge SHA `3e981a3`. The historical
implementation/FIX-01 notes remain offline evidence for that scope, not current
merge status. Runtime uses this exact PI main image, preserving Maximo/CEMS/NK
and existing stores. Migration 004 and stored-data API acceptance were performed
before the explicitly authorized one-GET technical source canary.

Technical registry collection remains distinct from governed NADI signals.
No production VERIFIED target is established. PR #16 now provides governance
in the actual existing Mart, but NADI-IDN-002A found no identity-qualified
proposal. **GOVERNED CANARY DEFERRED** until controlled identity evidence and
human verification. PR #15/#16 are merged; their runtime acceptance is preserved.
No PI projection or Phase 1 completion is claimed.

### 2. NADI-IDN-002 — pilot verified Asset ↔ AF mapping

Use controlled dry-run/import → PROPOSED → human verification → VERIFIED.
Bound the pilot population, approved evidence and units; test unmapped and
ambiguous states. Do not import a whole AF hierarchy or seed plausible names.
Complete NADI-RUNTIME-002 existing-Mart schema/runtime acceptance before executing
the pilot; `7149455` is historical evidence only, never a blind cherry-pick.

### 3. NADI-ING-PI-001 — PI evidence projection

Connect accepted mappings to approved collector evidence APIs/contracts and
project a bounded read model using existing owning stores. Preserve mapping
version, source identity/time/quality, idempotency and partial-failure behavior.
No new DB or diagnostic scores. Keep technical PI attributes distinct from
governed NADI Asset signals.

### 4. NADI-INTEGRATION-STATUS — trust in integration

Expose coverage, source last-success/attempt, collection lag, gaps, mapping
readiness and degraded state. Separate source freshness from business recency,
Mart projection freshness and API availability.

### 5. NADI-PHASE-1-ACCEPTANCE

Review the scoped end-to-end pilot and failure evidence, publish acceptance and
remaining domain gaps, then explicitly authorize Phase 2 planning/implementation.
[M0–M8](reliability-cockpit-platform/05-roadmap-implementasi.md) stays the
engineering implementation map underneath these product phases. M5 derived
intelligence and M7 PdM/actions now belong to later phases, not Phase 0 gaps.

## Freshness governance proposal checkpoint — NADI-P1-FRESH-001A (8 October 2026)

Reviewed main `478cce1` is serving. Runtime evidence reconciliation is the separate
[documentation PR23](https://github.com/johnd-creator/reliability-knowledge-starter/pull/23),
head `b08a4fd`; review that documentation checkpoint first. The earlier R1 repair
blocker is historical: one VERIFIED mapping, one approved Coal Flow signal and
one accepted condition row now exist. This proposal does not duplicate that
acceptance patch or alter its measurement.

[Freshness engineering proposal](../reliability-cockpit/docs/nadi-phase1-freshness-policy-proposal.md)
records bounded local cadence/error evidence and proposes separate acquisition
monitoring boundaries. All proposals are **PROPOSED — NOT YET APPROVED**. Coal
Flow source/projection thresholds remain **POLICY_EVIDENCE_INSUFFICIENT**. Three
shared runtime knobs cannot express five independent policies; reviewed compatible
component wiring and controlled-refresh journal/chronology acceptance are next.
Production policies remain blank, handoff collector success remains null, actual
Phase1 readiness remains UNKNOWN; Phase1 stays CURRENT/PARTIAL, never COMPLETE.
No source GET, mapping/selection mutation, projection, deployment or restart
is performed by this task. Next: **NADI-P1-FRESH-001B**, engineering policy
decisions and separately authorized manual refresh; recurring scheduling stays
unconfigured. PI_AF_KKS_LOOKUP_UNRESOLVED and BFPT freeze remain in force.

## Component freshness implementation candidate — NADI-P1-FRESH-001B

PR #23/PR #24 are merged; base `4b6ae7d`. [Implementation and deployment runbook](../reliability-cockpit/docs/nadi-p1-freshness-implementation.md) adds five independent
blank-default policies with exclusive legacy compatibility, API-only runtime
wiring and a manually invoked one-asset/one-signal refresh coordinator. Private
journal, shared host lock, existing-Mart advisory lease, Collector-owned five-GET
cap, chronology/quality gates and read-only replay are implemented in the candidate.
No candidate code is deployed, no policy is activated and no production refresh
or mapping/selection mutation occurs. Runtime remains `478cce1`; Phase 1 remains
CURRENT/PARTIAL and actual readiness UNKNOWN. Threshold 660/660/1800 proposals,
source/projection policies and one live run require separate accountable approval
after software review/merge. Next: exact merged-SHA controlled deployment,
configuration preflight and separately authorized single manual Coal Flow refresh
plus real replay/API/UI/readiness acceptance. No recurring scheduler is enabled.
PI_AF_KKS_LOOKUP_UNRESOLVED and BFPT freeze remain unchanged.

### NADI-ENG-BUNDLE-A implementation checkpoint — 2026-10-11

Evidence: [Engineering delivery report](../reliability-cockpit/docs/nadi-eng-bundle-a.md),
[PR #68](https://github.com/johnd-creator/reliability-knowledge-starter/pull/68).
Baseline `cc90fc73bea6ae399383d8538035c6454dc7e65a`; reviewed implementation
`2a7678d82f6f0e8769a03ca09857c59f2f37f338`. PR #67 remains independent OPEN.

| Official task | Implementation / tests | Persistent preview / acceptance |
| --- | --- | --- |
| ENG-UX-01 | IMPLEMENTED / TESTED: structured register/create/edit/detail, server scope/filter/pagination | VISIBLE in isolated QA; PO/engineer acceptance PENDING |
| ENG-UX-02 | IMPLEMENTED / TESTED: frozen evidence, notes, CAS/retry, independent review, immutable history | VISIBLE in isolated QA; operational activation PENDING |
| ADV-01 | IMPLEMENTED / TESTED in disposable PostgreSQL: approved Case + Recommendation, review/publication/withdrawal, immutable snapshots | BLOCKED_SCHEMA_PREREQUISITE in persistent QA; no DDL performed |
| ADV-02 | IMPLEMENTED / TESTED in disposable PostgreSQL: fixed server QA audience + asset scope, durable receipt | Persistent inbox/acknowledgement BLOCKED; DEMO UI evidence only |
| ADV-03 | IMPLEMENTED / TESTED: source links and existing Recommendation/Action Board local workflow | Local workflow VISIBLE; durable recipient handoff BLOCKED |
| ADV-04 | PLANNED / FUTURE GATED | Real identity/distribution/UAT/operational activation NOT APPROVED |

Overall bundle PARTIAL. No merge or Product Owner acceptance is inferred from
self-review/CI. Phase 2 and Phase 4 remain PARTIAL; Phase 0–5 definitions and all
historical evidence remain unchanged. Phase-1 independent review/checkpoint/expiry
are still 11 Oct 21:45 / 12 Oct 20:00 / 13 Oct 00:00 WIB; this bundle changes no policy.

### NADI-ENG-BUNDLE-A-FIX-01 — persistent QA checkpoint — 2026-10-11

This supersedes only the earlier persistent-schema blocker; the historical
checkpoint above remains accurate for its original execution. The PO authorized
narrow QA-only DDL on existing `nadi_live_dev_test`; operational scope is unchanged.
Evidence: [FIX-01 report](../reliability-cockpit/docs/nadi-eng-bundle-a-fix-01.md),
[actual persistent QA screenshots/results](../reliability-cockpit/docs/evidence/nadi-eng-bundle-a-fix-01/README.md),
[unmerged PR #68](https://github.com/johnd-creator/reliability-knowledge-starter/pull/68).

| Official task | Current development gate | Separate acceptance gate |
| --- | --- | --- |
| ENG-UX-01/02 | VISIBLE / TESTED, original Case workflow preserved | Actual engineer UAT and PO review PENDING |
| ADV-01 / B2 | PERSISTENT SYNTHETIC QA PASS; independently reviewed publication and preserved withdrawal | Operational distribution NOT APPROVED |
| ADV-02 / B3 | PERSISTENT SYNTHETIC QA PASS; trusted QA recipient, durable ACK, reload/reconnect, security rejection | Real organizational recipients/privileges PENDING |
| ADV-03 / B4 | QA PASS; existing local Action Board plus version-bound recipient handoff | Physical completion/effectiveness/UAT remain separate |
| ADV-04 | FUTURE / GATED | No email/push/operational activation authorized |

The original Phase0–5 roadmap, Phase2/4 PARTIAL, PdM engineer-validation gates and
Phase1 review/checkpoint/expiry are unchanged. QA execution PASS does not infer
merge, PO visual acceptance, real engineer UAT or production acceptance. PR #67
remains independent OPEN. No new roadmap phase or deadline extension.

### NADI-UX-ID-01 — Indonesian localization checkpoint — 2026-10-11

Track UI/UX yang sama; Phase 0–5 dan UX-01–09 tidak diganti atau diperluas.
PR #69 telah MERGED pada main `09b6d6308a6cc70818292eb71f79733255dcf823`,
terverifikasi 11 Oktober. Bukti historis integration/source PR tetap dipertahankan.

| Milestone | Status kandidat | Gate terpisah |
|---|---|---|
| L0 — Audit/baseline | PASS; PR #69 merged, branch/worktree terisolasi dari latest main | Runtime existing b348235 dipertahankan |
| L1 — Indonesian interface | IMPLEMENTED / TESTED | PO wording/visual acceptance pending |
| L2 — Panduan & istilah | IMPLEMENTED / TESTED; 41 istilah dan pencarian | Definisi kandidat engineering menunggu engineer |
| L3 — V1 responsive | TESTED 1440/768/390; dark mode/logo/token tetap | Bukan sertifikasi aksesibilitas penuh |
| L4 — Regression/review | Local frontend/contract PASS; exact-head CI dicatat pada PR handoff | Browser workflow adalah fixture; bukan UAT persisten baru |
| L5 — Delivery | Dokumentasi/evidence dan PR terpisah; no auto-merge | Kandidat belum dipilih pada preview aktif |

[Laporan dan preservasi](../reliability-cockpit/docs/nadi-ux-id-01.md) serta
[matriks/screenshot](../reliability-cockpit/docs/evidence/nadi-ux-id-01/README.md)
memisahkan implemented/tested/merged/visible/accepted. Launcher source selection saat
ini menghentikan web + API QA; tugas lokalisasi tidak menjalankannya. Backend,
collector, database, session dan schema Advisory/ACK tidak diubah.

72-hour Phase 1 review **11 Oct 21:45:26 WIB**, checkpoint PO **12 Oct 20:00 WIB**
dan hard expiry **13 Oct 00:00 WIB** tetap berlaku; hasil review operator UNKNOWN
bila belum ada bukti terpisah. Task ini tidak menjalankan, memperpanjang atau mereset
kebijakan/monitoring tersebut. Global login dan operational engineering tetap gated.


### NADI-UX-ID-02-FIX-01 — frontend-only activation checkpoint — 2026-10-11

Official frontend-only lifecycle and explicit frontend/backend SHA approval support a
separate Indonesian candidate while the QA API remains at b348235. Implementation/
hermetic checks are separate from runtime activation and PO acceptance. Exact-head CI,
actual HTTPS3000 visibility and preservation are final release gates; no new roadmap
phase, authentication activation, engineering scoring, source acquisition or Phase1
policy change. [Fix/runbook](../reliability-cockpit/docs/nadi-ux-id-02-fix-01.md).


FIX-01 actual activation checkpoint: **frontend-only development preview PASS** at
b6a4981, pinned backend b348235. Live106checks/30screenshots, exact-head backend/frontend
CI run38128497987 and preservation/rollback preflight PASS. PR71 remains unmerged,
stacked on unchanged OPENPR70. Final documentation-only release undergoes independent
CI/source selection. PO visual/engineer UAT/operational acceptance remain PENDING;
Phase0–5 and freshness governance unchanged. See the linked actual report above.


## NADI-UX-LOGIN-01 checkpoint — 2026-10-11

UX-08 fullscreen QA login/layout separation is IMPLEMENTED / TESTED candidate on latest merged main f8f8f2c. UX-09 remains responsive/regression preparation; final Product Owner visual acceptance is PENDING. No Phase 0–5 scope or freshness review/expiry policy changes. Runtime visibility and exact-head CI are separate gates recorded in the PR handoff.

[Implementation, boundaries and evidence](../reliability-cockpit/docs/nadi-ux-login-01.md).

Fullscreen-login actual checkpoint: functional 79dda14c passed CI and official
frontend-only activation; 102 actual live checks PASS and credential-free 1440/768/390
light/dark screenshots retained. Original QA records/sessions/schema/API and collectors
preserved; final documentation-release head/CI/visibility independently reverified on
[PR73](https://github.com/johnd-creator/reliability-knowledge-starter/pull/73). Product
Owner final visual review remains PENDING; UX-09 final acceptance is not inferred.

## Phase 2 PdM Measurement — native-input checkpoint — 2026-10-13

[NADI-PDM-CENTER-INPUT-01](../reliability-cockpit/docs/nadi-pdm-center-input-01.md)
is an IMPLEMENTED/TESTED development candidate from latest main `2e190c2b51fde50e0467d6d5165ebb1060902867`,
separate DRAFT PR. It advances M03/M05 within the existing Phase 2 scope: native
multi-point draft, authorized register/event history, safe page-scoped original-sample
scatter, independent review and exact-version Case handoff. M02 field signoff,
M04 parser/custody, M07 engineer UAT and cross-acquisition comparison are pending;
Q01–Q10 and PD/DGA uncertainty are preserved. Three workbook contexts are candidates,
not accepted measurement methods. MERGED/official runtime VISIBLE/ENGINEER APPROVED/
OPERATIONALLY ACCEPTED remain NO/PENDING. Phase0–5 and Phase1 policy/checkpoints/
hard-expiry are unchanged; no runtime or operational action was performed.

## Phase 2 M01/M02 — workbook candidate checkpoint — 2026-10-15

PR82 foundation is MERGED; PR83 reusable local tooling is MERGED in reviewed main
`106a4dc08b149576b2e84bbf8c70694288c7e9a7`. The laptop still serves the unchanged
PR82 source; merging tooling does not install it or select another branch.

[NADI-PDM-WORKBOOK-01](../reliability-cockpit/docs/nadi-pdm-workbook-01.md) advances
M01 with read-only inventory of the three original workbooks/23 worksheets and M02
candidate preparation with three versioned header profiles/nine DIRECT fields.
Native grid, generic input, review/CAS and Case handoff are retained. This is a
PARTIAL candidate: remaining sheet variants, formula/units/time/point ambiguity,
engineer mapping approval and operational UAT remain pending. No parser, schema,
source acquisition, threshold, scoring, attachment custody or live source selection
is activated. Q01–Q10, Phase0–5 and separate Phase1 governance remain unchanged.

## Checkpoint 15 Oktober 2026 — NADI-PDM-WORKBOOK-02

Phase0–5 dan Q01–Q10 tidak berubah. M01/M02 kandidat diperluas pada DRAFT PR85:4/4 sumber baru,177 sheet diinventarisasi;4 keluarga Vibration +2 CEP provisional,39 DIRECT baru dan3 input ambigu. Old3 profil/9 DIRECT serta historical acceptance dipertahankan. [Laporan](../reliability-cockpit/docs/nadi-pdm-workbook-02.md): implementation/test evidence ada; mapping PARTIAL, engineer approval/comparability PENDING, belum merged/visible/operational accepted. Tidak mengubah Phase1 review/expiry. Next: PO visual review dan field validation; bukan historical import atau aktivasi IRT.

## 15 Oktober 2026 — Engineering validation pack / M02 readiness

Checkpoint ini melengkapi catatan historis di atas; tidak menulis ulang acceptance.
Main terverifikasi `05ce1c060605defb58a74467a38acb43ff4d04f9` memuat PR82,83,85
MERGED. PR85 HEAD `7daab3a62866f19b30fb45462a94bafff8795dc5`;9 profil terintegrasi,
48 DIRECT sumber +3 unit temperatur AMBIGUOUS. DIRECT bukan engineer approval.

Bukti [checkpoint merge development](https://github.com/johnd-creator/reliability-knowledge-starter/pull/85#issuecomment-6192024336)
dan [post-merge CI PASS](https://github.com/johnd-creator/reliability-knowledge-starter/actions/runs/38734062455)
memisahkan MERGED, TESTED, VISIBLE dan ACCEPTED. Live development keyboard1280/
1440/1920, light/dark, zoom browser asli125%, draft/review/Case serta HMR telah
terverifikasi pada7daab3a; final visual PO tetap PENDING. QAO-PDM-01 tetap dicatat:
ERR_TOO_MANY_RETRIES, root UNKNOWN, risiko NON_BLOCKING hanya untuk development;
run bersih berikutnya tidak membuktikan penyebabnya.

[Paket validasi M02](../reliability-cockpit/docs/nadi-pdm-eng-validation-01.md)
menyiapkan20 keputusan P1 +6 P2 yang masih PENDING_ENGINEER_VALIDATION dan
[lembar diskusi engineer](../reliability-cockpit/docs/nadi-pdm-engineer-review-packet.md).
Dokumentasi READY tidak menutup M02 atau menyetujui definisi field.

| Milestone existing | Checkpoint aktual / gerbang berikutnya |
|---|---|
| M01 — sampel/terminologi | Inventaris7 workbook/200 sheet dan9 profil tersedia; jawaban/approval Q01–Q10 tetap pending |
| M02 — kontrak metode/titik/instrumen | CANDIDATE: matriks/analisis v1.1 siap;20 keputusan kritis dan definisi berwenang belum diterima. Registry titik, konteks per-row, semantik waktu ganda dan snapshot konteks perlu proposal terpisah bila diperlukan |
| M03 — kronologi/filter | Foundation history/manual entry/raw scatter terintegrasi; comparability dan historical import tetap gated oleh M02 serta izin tersendiri |
| M04 — import/lampiran | Parser dan custody/upload diagnostik belum diaktifkan; izin/mapping/storage terpisah |
| M05 — interpretasi/review/Case | Foundation independent review/exact-revision handoff teruji; bukan method approval atau engineer UAT |
| M06 — WO/rekomendasi | Foundation NADI existing tetap; WO Maximo hanya rujukan read-only, tanpa perluasan scope |
| M07 — UAT engineer | PENDING setelah field sign-off dan bukti representatif; QA sintetis bukan UAT |

Next: PO membahas paket per keluarga representatif dengan engineer; implementasi
hanya keputusan M02 yang disetujui melalui task berikutnya. Vibration point/quantity,
3 unit temperatur, CEP IR Window/IRT dan comparability tetap unresolved. Phase0–5,
M01–M07 serta batas diagnostik Phase3 dipertahankan. Tidak ada assessment otomatis.
Phase1 review/checkpoint/expiry dan kewenangan operasional tidak diubah, diperpanjang
atau disertifikasi ulang; hasil operator tidak dinilai oleh task dokumentasi ini.
Tidak ada runtime/DB/session/source/collector/Mart/external-QA action.

## 15 Oktober 2026 — NADI-INTEGRATION-UI-01 candidate

[Pusat Integrasi Sistem](../reliability-cockpit/docs/nadi-integration-ui-01.md) pada
[DRAFT PR87](https://github.com/johnd-creator/reliability-knowledge-starter/pull/87)
mengimplementasikan `/system-integration` development-only dari DTO integration
status/Data Trust existing. Independent freshness/availability/identity/quality,
populasi Registry vs teknis dan semua route domain dipertahankan. Komponen, browser
sintetis/responsive/a11y dan local regression PASS; CI exact-head dicatat pada PR.
IMPLEMENTED/TESTED kandidat bukan MERGED, live VISIBLE, PO ACCEPTED atau operational
readiness. Tidak ada runtime/DB/collector/Mart/source/policy action. M01–M07 dan
Phase0–5 tetap; M02/M03/M07 ON HOLD, seluruh26 engineer decisions tetap pending.
Phase1 checkpoint/review/hard-expiry tidak diubah atau disertifikasi ulang.
Next: senior/product review, kemudian conditional integration checkpoint.

## 15 Oktober 2026 — NADI-REPORTS-UI-01 candidate

Baseline main36203fe478e5a558fcf5ce4f8d5a9ff36fe92014 includes PR87 MERGED as
DEVELOPMENT ACCEPTED only; factual API authorization remains a deployment
prerequisite. [Reports Center V1](../reliability-cockpit/docs/nadi-reports-ui-01.md)
adds two development candidate previews using existing DTOs. Local synthetic
selection/period/race/semantics/responsive/browser and regression gates PASS;
exact-head CI/PR status recorded separately at delivery. Candidate IMPLEMENTED/
TESTED is not MERGED, live VISIBLE, PO ACCEPTED or operational approved. No export,
delivery, new KPI, source access, runtime transition or policy change.
Phase0–5 and M01–M07 unchanged; M02/M03/M07 ON HOLD and26 engineer decisions
pending. Phase1 review/checkpoint/hard-expiry unchanged, not extended or recertified.
Next: senior review then conditional development checkpoint.

## 16 Oktober 2026 — Administration architecture readiness

Verified main5af41294745d7eb78eb14f617cacdbc223844564 includes PR88 MERGED with
[post-merge backend/frontend CI PASS](https://github.com/johnd-creator/reliability-knowledge-starter/actions/runs/38768396811),
Reports Center DEVELOPMENT ACCEPTED only; export/deployment/report-definition
approvals remain pending. [NADI-ADMIN-READINESS-01](../reliability-cockpit/docs/nadi-admin-readiness-01.md)
provides source-grounded capability inventory, permission matrix, threat/gap register
and [ADMIN-01–05 proposed slices](../reliability-cockpit/docs/nadi-admin-implementation-plan.md).
These are implementation task proposals, not new phases or authority to execute.
Seven API gap groups (5 HIGH/2 MEDIUM potential unsafe-exposure impacts),12 pending
security/product/operator decisions; organizational role mappings PROPOSED.
Administration UI/API remains PLANNED. Phase0–5/M01–M07 stay; M02/M03/M07 ON HOLD,
26 engineer decisions pending, Phase1 review/checkpoint/hard-expiry unchanged.
No runtime/session/DB/source/collector/Mart or external QA action. Next: senior
security/product review, then separately authorize ADMIN-01 read-contract decisions.


## 18 Oktober 2026 — NADI Design System V2 candidate

NADI-UX-V2-OVERHAUL-01 checkpoints A–E IMPLEMENTED; checkpoint F locally TESTED:
shared controls/surfaces, PdM entry/register, Case search/review presentation,
Executive/Assets, Recommendations/Action Board, Reports and shared factual pages.
[Report and 20 screenshot pairs](../reliability-cockpit/docs/NADI-UX-V2-OVERHAUL-01.md).
15 frontend check groups, types/lint/build and 1,193 synthetic browser assertions
pass; 34 axe scans report zero violations. Exact-head remote CI belongs to the
Draft PR checks. UNMERGED, PO acceptance PENDING, LIVE_PREVIEW_NOT_PROMOTED.
No source/DB/API/auth architecture changes; Administration remains PLANNED.
Existing phases, engineering approvals and ON HOLD decisions are not advanced.
Next: senior design/code review → PO visual acceptance → authorized merge.


## 19 October 2026 — NADI UI source consolidation checkpoint

PR103 recovery and PR102 → PR104 UI are being consolidated with all original
ancestry and both DEV-LOG histories retained. [Integration plan](../reliability-cockpit/docs/NADI-UI-INTEGRATION-103-102-104.md)
records immutable heads, combined validation and normal PR/main CI gates.
The existing development appearance is PO accepted; source commit/push/merge is
explicitly authorized only after review and CI. At this preparation checkpoint
source integration is PENDING final exact-head qualification; final merge state
belongs to the GitHub handoff. Actual observed runtime already serves PR104 with
controller/bootstrap PR103; source integration does not restart or replace it.
Operational F03/Phase1, engineer method/threshold decisions and ON HOLD items
remain unchanged. Historical pending/not-promoted entries retain their dated scope.


## 19 October 2026 — Verified PR105 source integration and next batch

Main `8bb1bcb2c485feeb792235c64b5aef6bbce5e3cc` includes [PR105](https://github.com/johnd-creator/reliability-knowledge-starter/pull/105), merged normally on 19 October. Original PR103/PR102 heads are MERGED; PR104 is CLOSED/SUPERSEDED through PR105, with all three original heads preserved as main ancestors. Both DEV-LOG histories remain intact.

[Candidate CI](https://github.com/johnd-creator/reliability-knowledge-starter/actions/runs/39248372814) and [post-merge main CI](https://github.com/johnd-creator/reliability-knowledge-starter/actions/runs/39249394137) are terminal SUCCESS on their exact SHAs: 530 backend tests plus 14 contracts, zero skips; frontend checks/lint/types/build and 1,300 synthetic browser assertions pass. These supersede the earlier preparation checkpoint's PENDING source-merge status.

The accepted development appearance remains application PR104 `fc33515a3cd0ec4bd9fad81c59e65babe397c2b3`, with installed controller/bootstrap PR103 `1ec93d6f3507321617903d169451d77fdcc1216e`. Source integration did not deploy/restart it. Read-only verification preserved 35 container identities/states/ports, serving tracked source/PIDs and unrelated dirty files. Visibility and operational acceptance remain independent of source merge.

The user deferred PdM engineer validation; no method/threshold signoff or domain decisions are inferred. The next authorized batch prepares (1) this status reconciliation, (2) reproducible Phase1 identity/provenance/stale-or-missing reliability fixes, and (3) F-03 recovery/backup/rollback closure evidence. It permits isolated code/docs/tests only; new commit/push/merge, operational migration/grant/security changes, deploy/restart and restore into active databases are not authorized. Linear reconciliation is handled separately.

Phase1 retains the historical CURRENT/PARTIAL label; current monitoring approval after the13October expiry is NOT ESTABLISHED in reviewed committed evidence. The accepted single Coal Feeder pilot is not a full-registry mapping approval; wider identities need attributable evidence. Old monitoring expiry and condition freshness policies require explicit current disposition, not invented thresholds. Astra F-03 is distinct from AUTH-F03: its recovery work remains unmerged in PR94–100 and operationally NO-GO. No F-03 closure or engineer acceptance is claimed by this checkpoint.


### Local follow-up qualification —19 October2026

[Phase1/F03 preparation report](../reliability-cockpit/docs/NADI-PHASE1-RELIABILITY-F03-PREP-01.md): independent source review exposed two P2 aggregate/detail and restored-state gaps, reproduced and fixed locally; follow-up review found no new blocker. Final focused169/169 tests pass with zero skips on both isolated PostgreSQL16.14 and18.6; Maximo offline208/208 and canonical14/14 pass. All original35 containers, dirty worktrees, preview source/listeners and installed controller were rechecked unchanged. No new commit/push/PR/merge/deploy or active DB/security change. Phase1 software candidate ready for review/exact-head CI after authorized publication; current monitoring approval after13Oct expiry NOT ESTABLISHED, attributable owner disposition needed. F03 OPEN/NO-GO; its unmerged recovery stack/global-metadata/operational gates remain separate. PdM engineer validation stays deferred.


## 21 October 2026 — PdM manual follow-up package candidate

Verified baseline main44bc1def (PR108). FR-03/04/UI-04
[NADI-PDM-MANUAL-FOLLOW-UP-01](../reliability-cockpit/docs/nadi-pdm-manual-follow-up-01.md)
implements origin, manual engineer narrative/follow-up and reported-unverified SR
references using existing application workflows. Scoped tests/independent review
qualify a branch/draft PR only; exact publication SHA and CI are recorded in handoff.
No merge, active visibility, operational engineering acceptance, Maximo writes or
F03/PR107 integration is implied. Source/runtime/checkpoints above remain historical.


## 21 October 2026 — local factual-error and staged-history candidate

NADI-PDM-HISTORY-STAGING-01 is implemented locally on PR109/main891dfee8.
Executive Overview distinguishes403 capability/scope,401 session and actual
upstream/network unavailability without changing access policy. Offline XLS/XLSX
staging preserves source cells/dates/units/formula cache and identifies existing
partial events; a maximum25-record pilot is restricted to disposable application
copies and the existing validated CREATE/audit/receipt path. No guard increase,
canonical mapping, active-demo mutation, publication or deployment is implied.
[Scope, gates, qualification and next activation](../reliability-cockpit/docs/nadi-pdm-history-staging-01.md).

## 21 October 2026 — complete PdM source history, isolated candidate

NADI-PDM-HISTORY-COMPLETE-01: IMPLEMENTED locally and TESTED on disposable copies;
7 workbooks/200 sheets/173,147 physical cells preserved as25,278 navigable provisional
source groups. Existing32 sample records linked, not duplicated; old35 inspections/
46 revisions/4 Cases preserved in qualification. Compact owning-store migration 007
and13-table recovery roundtrip tested. Not published/merged/active/UAT accepted.
Next: independent final review and authorized publication/CI, then separately
approved migration/controller activation and full-history demo adapter/import.
Canonical mapping, historical chart, engineering qualification and cloud transfer
remain distinct future acceptance. [Evidence](../reliability-cockpit/docs/nadi-pdm-complete-history-01.md).

### NADI-PDM-SIMPLIFICATION-SPRINT-01 — 31 October 2026 isolated candidate

The Product Owner accepted the PR113 blueprint direction and authorized S1-01–S1-05
frontend implementation/testing/Draft PR. [Sprint evidence](../reliability-cockpit/docs/NADI-PDM-SIMPLIFICATION-SPRINT-01.md)
records five-entry navigation, Register/history/editor/detail simplification and
optional contextual Engineering. Implementation/testing, exact-head CI, senior
review, PO visual acceptance, merge and active visibility remain distinct.
No Phase0–5 history, source engineering gate, F03/PR107 or future KPI plan changes.
Next: senior review → PO UX acceptance → separately authorized F23/F24 runtime
compatibility and activation. Localhost remains on its existing preview.

### Sprint 1 one-PR integration — 31 October 2026

The Product Owner consolidated blueprint/Sprint/parity and conditional local
acceptance into PR114 based on main; PR113 is superseded without merge. Phase0–5
history and engineering gates remain. [One current acceptance report](../reliability-cockpit/docs/NADI-PDM-SPRINT1-ONE-PR-DELIVERY.md)
separates exact-source/CI qualification from authenticated local activation and PO UX.


### 1 November 2026 — integrated Sprint3 development qualification

Sprint3 implements read-only exactasset Maximo/approved PI evidence navigation in
one [stacked Draft PR116](https://github.com/johnd-creator/reliability-knowledge-starter/pull/116),
parent PR115 exact3a01e842. [Delivery and preservation](../reliability-cockpit/docs/NADI-PDM-SPRINT-03-DELIVERY.md)
retain Phase0–5 history, current phase/source approval boundaries and F01–F24.
Sprint2 remains the active local visual-review candidate; Sprint3 is isolated.
Next: exact-head technical CI/review → consolidated PO visual review → separately
requested activation. Full mapping inventory/history/DCS and Sprint4 failure,
exposure and repair definitions remain gated; no automatic KPI implementation.


### 1 November2026 — Sprint4 Reliability Performance technical foundation

[Draft PR117](https://github.com/johnd-creator/reliability-knowledge-starter/pull/117)
is stacked on PR116 exact3778584. [Delivery](../reliability-cockpit/docs/NADI-PDM-SPRINT-04-DELIVERY.md)
records offline synthetic functional event/exposure/active-repair contracts and
calculation qualification; Laporan exposes an operationally disabled readiness
workflow using existing exactasset source access. Phase0–5 history, M0–M8, source
ownership, M02/comparability and all method decisions remain unchanged/pending.
Next: exact-head technical CI/review → consolidated PO/source/engineer decisions.
[Sprint5 handoff](../reliability-cockpit/docs/NADI-SPRINT5-STABILIZATION-HANDOFF.md)
is a proposal; Sprint5 is not started. No real KPI publication or activation.


### 1 November2026 — Sprint5 integrated stabilization candidate

Separate owner task authorizes Sprint5 on exact PR117988af8d. Phase0–5/M0–M8
history stays unchanged. [Delivery](../reliability-cockpit/docs/NADI-PDM-SPRINT-05-DELIVERY.md)
qualifies integrated PdM/evidence/disabled-reliability journeys and prepares
[consolidated human UAT](../reliability-cockpit/docs/NADI-SPRINT5-UAT-CHECKLIST.md).
Next decision is PO/engineer review; exact-head technical CI/review do not grant
methods, operational eligibility, merge or local/QA/production activation. Active
Sprint2 is preserved. No automatic following-sprint implementation.


## 2 November 2026 — WO/SR classification reconciliation

NADI-MAXIMO-WO-SR-CLASSIFICATION-01 is an isolated candidate stacked on Draft
PR118 (`0a10fe10bf2c9cd2158b5c47ed691f8b9404a7a0`). Retained evidence and
FLOW reference reconciliation support a conservative WO DTO/UI correction; SR
read authorization remains proposed. No runtime/source/storage activation.
[Lineage, decisions and preservation](../reliability-cockpit/docs/NADI-WO-SR-CLASSIFICATION-01.md).
Technical qualification and owner acceptance are independent; final CI/review
receipts are recorded on the delivery PR. MTBF/MTTR and cross-inspection trends
remain NOT_ELIGIBLE.


## 2 November 2026 — NADI-WO-DETAIL-ENHANCEMENT-01 candidate

Stacked on Draft PR119 (`119ba2f1472facedd71433d65b74f3b7d64a6434`):
WO identity/status, six-group source detail, explicit Asia/Jakarta presentation,
original ISO audit text and precise missing/unmapped/unverified/unexposed states.
Additive allowlisted read detail and tested future local projection correction
retain report/schedule/failure scalars without schema changes. Existing actual
dates remain unavailable in the audited WO path; no source acquisition or
operational reprojection is authorized. MTBF/MTTR remain NOT_ELIGIBLE.
Implementation/synthetic qualification, exact-head CI, local activation and owner
UAT are separate milestones. Activation is conditional on all mandatory gates;
no current claim of deployment, merge or PO acceptance.
[Requirements, lineage and boundaries](../reliability-cockpit/docs/NADI-WO-DETAIL-ENHANCEMENT-01.md).


## 2 November 2026 — PR120 revised access/activation candidate

The task adds separately owned Factual READ permissions and scoped Beranda/Asset/WO
readers, without changing Engineering write scope or domain eligibility. Local-only
stacked CI recognition is a separately approved policy; production main qualification
remains unchanged. Source/testing, grant approval, installation, local activation and
real UAT remain separate milestones. No Phase advancement, method approval or new
PdM Log Book is inferred. [Owning report](../reliability-cockpit/docs/NADI-PR120-FINAL-UNBLOCK-01.md).

Owner amendment, 2 November 2026: approved Dashboard/Asset/Maintenance READ across
the registered BSR/IP population supersedes the initial one-asset proposal. PR120
adds an explicit registered scope and maintenance-only aggregate read model. This
is candidate implementation, not merged/visible/accepted scope; all activation,
recovery and actual UAT gates remain. No additional roadmap phase is implied.

## 2026-11-02 asset hierarchy implementation checkpoint

FR-02 / UI-03 [NADI-ASSET-HIERARCHY-01](../reliability-cockpit/docs/NADI-ASSET-HIERARCHY-01.md)
is an implementation candidate for bounded retained Maximo hierarchy, with
hermetic scope/API and synthetic browser verification. Live visibility, hosted
exact-head qualification, merge and PO acceptance require separate evidence.
Retained gaps and role semantics remain unresolved; no collection, Registry
import, grant change or phase advancement is claimed. Logbook PdM remains HOLD.

## NADI source integration 2026-11-02

Owner-authorized Sprint/WO source integration PR114–120 and hierarchy PR122 is
MERGED. [Evidence and remaining gates](../docs/NADI-NIGHT-INTEGRATION-20261102.md) supersede earlier open/draft
source checkpoints only. The bounded live Maximo pilot verifies the existing
read path without importing data; full hierarchy population and role semantics
remain PARTIAL/UNKNOWN. Runtime remains PR119; Phase1, M02/Q01–Q10 and PO/operational
acceptance do not advance. Logbook PdM remains HOLD.


### Scoped source-ingestion follow-up — 2026-11-03 WIB

The approved registered CS01 gap-root subset was paged against Maximo, with capped
groups refined until that subset was exhausted. New technical child rows passed
fresh private backup/independent isolated restore and exact-packet normal-writer
rehearsal before append to the existing Maximo-owned Collector/Mart. Old master,
Registry, mapping, ledger and asset-cursor fingerprints remain unchanged; the run
is PARTIAL and does not advance global cursors. No Registry import, role inference,
WO backfill, source write or service change. Full population/role acceptance stays
PARTIAL/UNKNOWN and local PR120 activation stays BLOCKED. Evidence and cardinalities
remain private; see the [integrated source report](../docs/NADI-NIGHT-INTEGRATION-20261102.md) for the bounded method.


### NADI-HIERARCHY-CHILD-UNIT-READ-20261103 — source investigation

The explicitly approved finite BSR/IP parent investigation without a child unit
predicate is complete. A paired CS01 query reproduces exclusion of the discovered
relations; child eq11 remains absent in API responses, not verified as stored null,
empty or another unit. Projection controls, pagination/deduplication and preservation
checks passed. This read did not ingest data or change default Collector scope,
Registry, grants, credentials or services. Earlier approved technical-row append
is separate. Runtime stays PR119; controller admission and candidate live UAT remain
blocked. PR121 is Draft/superseded and Logbook PdM HOLD. Domain input describes an
unnamed tier above system, then system/subsystem/asset/equipment; source role mapping
is UNKNOWN and Registry membership does not imply physical roots. See [source report](../docs/NADI-NIGHT-INTEGRATION-20261102.md)
for method and limits; raw evidence and counts remain private.

### NADI-HIERARCHY-CHILD-CANONICAL-INGEST-20261103 — authorized append

The owner separately approved ingestion of the closed, previously verified child
allowlist. After fresh consistent backup, independent isolated restore, denied-write
tests and full-packet rollback/insert/replay rehearsal, an insert-only outer
transaction appended missing AssetMaster facts through the existing MartWriter in
the Maximo-owned Mart. Source IDs and direct parent references are preserved; missing
child unit remains UNKNOWN without parent/plant fallback. Legacy Equipment, Registry,
old facts, mappings, ledger, asset cursors and WO classifications are preserved.
Default acquisition scope and scheduled workers are unchanged. The reviewed NADI
hierarchy reader passed on the isolated data, and the configured live SELECT-only
reader verified the stored facts. This is data availability, not live hierarchy UI
or Engineer UAT acceptance. All existing containers remain preserved; PR119 runtime,
controller compatibility STOP, UNKNOWN roles, PARTIAL global coverage and Logbook
PdM HOLD remain. Counts, raw identities and recovery evidence remain private.
