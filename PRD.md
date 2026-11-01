# NADI Product Requirements Document

Version: 1 · Updated: 2026-10-10 · Task: NADI-DOC-FOUNDATION-01.
Product Owner direction is recorded below; detailed designs remain review candidates.
This document specifies the product, not deployment authorization or completed UAT.

## 1. Vision and business objectives

NADI — Reliability Data Platform integrates factual data and governed engineering
evidence for PLTU Banten 1 Suralaya. It supports traceable reliability and maintenance
decisions while preserving the Shared Data Foundation's source ownership.

Objectives: make factual asset context easy to find; preserve measurements and
reasoning through independent review; connect reviewed findings to accountable
local recommendations; expose evidence limitations; and retain a history usable by
future engineers. Quantified business benefit targets require an agreed baseline;
no availability, failure-reduction or prediction-accuracy benefit is claimed here.

## 2. Users

| Product persona | Primary need |
|---|---|
| Reliability Manager | Portfolio context, evidence limitations and follow-up visibility |
| Reliability Engineer | Asset investigation, cases and supported interpretations |
| PdM Engineer | Measurement points, episodic histories and diagnostic evidence |
| Maintenance Engineer | Maintenance context and informational existing WO references |
| Engineering Reviewer | Independent version-bound review and decision history |
| System Administrator | Authorized account, configuration and audit administration |

Personas are not an implemented permission matrix. Current trusted-session roles,
asset scopes and review exclusions are defined by the existing Engineering contracts;
future role mapping requires separate approval and tests.

## 3. Requirements and traceability

IDs below are stable. All are product requirements from the task unless explicitly
marked PROPOSED. Their presence is not implementation acceptance. Status evidence
lives in [the roadmap](plans/NADI-ROADMAP.md) and [development log](DEV-LOG.md).

| ID | Functional requirement | UI specification | Delivery dependency / acceptance |
|---|---|---|---|
| FR-01 | Preserve factual Executive Overview and approved semantics | UI-01 | UX-04; factual route/data regression |
| FR-02 | Asset register, health overview and contextual detail | UI-02/03 | UX-05; exact asset identity, unknown states |
| FR-03 | PdM measurement and investigation workspace | UI-04 | UX-06; PR #63 R01–R08/Q01–Q10 gates |
| FR-04 | Attributed cases, inspections, evidence, independent review, revision/audit history | UI-05 | Phase 2; trusted identity, application persistence, engineer UAT |
| FR-05 | Reviewed local recommendations and follow-up | UI-06/07 | UX-07; existing WO references only |
| FR-06 | Governed reports with explicit scope and provenance | UI-08 | PLANNED; report definitions and export policy |
| FR-07 | Integration trust and technical navigation | UI-09 | UX-03; preserve factual routes and ownership |
| FR-08 | Bounded administration | UI-10 | PLANNED; approved product role mapping |
| FR-09 | Future authenticated access to application pages | UI-11 | UX-08 QA login presentation only; global enforcement needs separate approved task |
| FR-10 | One primary HTTPS development address with accurate status | Shared shell | UX-01; PR #62 development acceptance, independent merge state |

The corresponding [page specs](docs/design/NADI-UI-SPEC.md) give testable behavior.
The [authority and decision register](docs/NADI-DOC-FOUNDATION-01.md) records
provenance and conflicts; technical ADRs/contracts retain their scoped authority.

## 4. Executive Overview — FR-01

Maintain the existing factual dashboard. Future layout includes KPI cards,
reliability overview, maintenance statistics, asset condition summaries, historical
charts and management attention indicators. Each metric needs a definition,
population, period, unit, evidence path and missing-data behavior.

Accepted Maintenance Activity is not Repeat Failure. Raw source status is neutral.
Health/risk summaries require approved engineering rules and sufficient evidence;
illustrative concept numbers cannot become values. Preserve
[factual V1 semantics](reliability-cockpit/docs/nadi-v1-release-candidate.md) and
[KPI evidence boundaries](reliability-cockpit/docs/nadi-kpi-evidence-catalog.md).

## 5. Asset Health — FR-02

The target primary asset workspace includes Asset Register, health overview, Asset
Detail, technical information, maintenance history, PdM evidence, recommendations
and existing WO references. Preserve current `/assets`, canonical detail and
`/asset-health` functionality while future navigation is reviewed.

Asset Detail follows the Product Owner's declared visual target in this order:

1. Asset Header.
2. Health Summary Cards.
3. Asset Details.
4. PdM Condition Summary.
5. WO History.
6. Recommendations / Actions.

Dependencies: governed Maximo Asset Registry and WOs, approved PI condition evidence,
manual PdM inspections, NADI Engineering records and recommendations. Equipment
identity must be exact. Broader technical equipment is not automatically registered.
UNKNOWN means unavailable/unverified; NOT ASSESSED means no supported assessment.
An empty WO history is not proof of no failures. No fabricated health score,
criticality or operating status. The PO-confirmed official reference is
[existing konsep4.png](konsep4.png), verified under FIX-02. The six-section layout
matches the reference; implemented UI fidelity remains a separate acceptance gate.

## 6. PdM Center — FR-03

Target capabilities: method navigation, measurement history/point selection, actual
measurement timestamps, trending, findings, engineering interpretation, authorized
spectrum/waveform references and IR thermograms, independent review and linked
recommendations. Candidate methods: Vibration, IR Thermography, MCSA, Tribology;
other methods require engineering validation.

Preserve the [merged NADI-PDM-REQ-01 requirements](reliability-cockpit/docs/nadi-pdm-requirements-01.md)
from PR63. Merge does not approve the candidate method fields or thresholds.
R01–R08 cover episodic events, point/instrument context, original values/units/times,
diagnostic references, separated interpretation/review, controlled Excel mapping,
existing-WO context and comparability. Q01–Q10 all remain PENDING_ENGINEER_VALIDATION:
samples, export formats, instrument metadata, point identity, severity definitions,
PD meaning, “30% acr”, inspection cadence and exact Maximo abnormality semantics.
M01–M07 remain the proposed Phase 2 measurement/investigation backlog.

Portable readings are not continuous or assumed daily. Plot actual timestamps;
missing intervals remain missing. Do not merge portable and DCS/PI series without
reviewed point, quantity, unit, bandwidth, method and operating-context comparability.
PD must not be equated with DGA. Existing enums do not approve engineering methods.
No workbook parser, source acquisition, threshold or diagnosis is approved here.

## 7. Engineering Workspace — FR-04

Existing merged foundations include Engineering Cases, inspections, bounded
evidence references, independent review, revision history, audit history and local
recommendations. Browser-memory DEMO routes differ from authenticated persisted QA.
The latter uses isolated synthetic context and existing test data.

Measurements, observations, interpretations and review decisions remain distinct.
Accepted review does not convert human judgment into source fact. Preserve exact
asset binding, immutable versions, concurrency handling and server-enforced reviewer
independence. See [ADR006](reliability-cockpit/docs/adr/006-engineering-workspace.md),
[inspection workflow](reliability-cockpit/docs/manual-inspection-workflow.md) and
[integration acceptance](reliability-cockpit/docs/nadi-e-integration-02.md).
Development acceptance has evidence; real engineer UAT and operational activation
remain unproven/gated. Do not report them as passed.

## 8. Recommendations and Action Board — FR-05

Target flow: Finding → Engineering Interpretation → Independent Review →
Recommendation → Follow-Up → Existing WO Reference → Effectiveness Review.
An existing WO reference is optional context, not a prerequisite to invent a WO.

Recommendations are NADI-owned records. Preserve reviewed case/evidence versions,
responsible person, rationale, target date, local follow-up and independent completion
verification. Effectiveness requires supported outcome evidence; local completion
does not prove operational effectiveness. Maximo WOs remain read-only references;
no create, approve, assign, update, close or cancel action is allowed.
See [recommendation lifecycle](reliability-cockpit/docs/recommendation-workflow.md).

## 9. Reports, integration and administration — FR-06–08

Reports require approved definitions, filters, provenance, as-of time and export
privacy policy. System Integration consolidates existing Data Trust and technical
surfaces without changing their domains or starting source requests. Administration
must expose only authorized application capabilities; a system administrator does
not gain Mart/source write authority or an independent-review override.
These complete product screens are planned, not established by existing APIs/CLIs.

## 10. Login and authentication — FR-09

Eventually application pages should require authenticated access. **Design the
global login page first; do not activate global enforcement in this phase.** Keep
factual development screens easy to access. Existing `/login` is a development QA
entry, not an implemented global access policy.

Preserve HTTPS, Secure/HttpOnly/SameSite cookies, trusted Origin, CSRF protection,
server-derived roles/scopes, revocation and session expiry. No client-side role
selector establishes authority. Existing isolated Engineering gates remain intact.
Activation requires a separately approved task covering routing, account onboarding,
recovery, session policy, provisioning and regression. Local username/password is the
current initial-QA path; enterprise SSO is a future option, not an invented blocker.

## 11. Nonfunctional requirements

| ID | Requirement | Acceptance gate |
|---|---|---|
| NFR-01 | Clear provenance and unknown states | Every operational value is evidence-backed; DEMO is explicit |
| NFR-02 | Accessible, responsive interactions | Keyboard/focus, labels, non-color cues, readable charts and 390/768/1440 review; contrast verified before approval |
| NFR-03 | Bounded loading and failure behavior | Preserve navigation; scoped error/retry; no fabricated success or silent fallback |
| NFR-04 | Durable Engineering history | Persist approved records/revisions/audit; prove recovery in authorized isolated tests |
| NFR-05 | Safe concurrency and authorization | Stale-version conflict, independent review, revocation and denied scope tested |
| NFR-06 | Maintainable development | Task/PR trace, exact-head CI, visible runtime SHA, separate PO acceptance |
| NFR-07 | Performance and operational observability | Bounded paging/requests and observable API states; numeric performance budget remains TBD by measurement |

## 12. Data and security governance

Contracts own identity, units, timestamps and nullability. Source acquisition belongs
to collectors; source clients/credentials must not enter NADI consumers. Mart access
is SELECT-only; human records use the existing application owner. No new operational
store is implied. Controlled test fixtures are synthetic and never source truth.

No invented scores, thresholds, risk classes or predictions. Preserve accepted scope,
raw status semantics, freshness governance, unresolved relationships and source guards.
No operational policy activation, extension, reset or rollback is authorized here.
Secrets, source payloads and personal data must not be placed in GitHub or design
references. The [root safety rules](AGENTS.md) remain binding.

## 13. Acceptance and open dependencies

Implementation acceptance requires requirement IDs → changed artifacts → scoped
tests → exact tested SHA/CI → runtime observation → separately recorded PO decision.
IMPLEMENTED, TESTED, MERGED, VISIBLE and ACCEPTED are independent, not synonyms.
Design approval cannot satisfy a runtime or engineering evidence gate.

The five [official PNG references](docs/design/references/README.md) are AVAILABLE
and their mapping is PO-confirmed under FIX-02; no ZIP/JPG or duplicate is required.
Open dependencies: token/contrast and navigation review;
PR #62/#63 are merged; remaining gates include Q01–Q10 engineer validation; approved assessment semantics;
authorized operational identity/application writer/storage/scanner provisioning;
real engineer UAT; report definitions and product role matrix; measured performance
targets; global authentication activation task. Phase 1 operator-review results are
UNKNOWN where no result is available, with the existing expiry preserved.

## Bundle A delivery checkpoint — 2026-10-10

FR-01, FR-07, FR-10 and NFR-01/02/03/06 have a frontend implementation candidate
against merged main963e7a8. [Bundle A review](reliability-cockpit/docs/nadi-ux-bundle-a.md)
records its bounded regression and runtime evidence. FR-01 preserves the same
Decision Overview contract and 7/30/90-day filters; query-as-of is explicitly distinct
from source freshness. No portfolio health/risk calculation or global authentication
activation is introduced. The sidebar exposes planned modules honestly; Engineering
placement and actual visual acceptance require Product Owner review. UX-05–09 and
PR63 engineer-validation gates retain their existing scope/status.

## Bundle B delivery checkpoint — 2026-10-10

FR-02/03/05 now have a [Bundle B frontend implementation candidate](reliability-cockpit/docs/nadi-ux-bundle-b.md) on main160737b / MERGED PR65. Asset identity and factual
APIs remain unchanged. The working PdM, Recommendation and Action Board surfaces
reuse authenticated isolated QA contracts; their data is explicitly SYNTHETIC.
Operational APIs/identity/writer activation, approved method/point/comparability,
attachment custody and engineer UAT are still dependencies. UI completion grants no
engineering approval. Commands reuse existing authorized Engineering workflows;
there is no new Maximo action, risk metric or global login enforcement.


## Bundle C — login presentation and development acceptance — 2026-10-10

The Product Owner's Bundle C directive grants provisional development acceptance
for Bundle B / PR66 and schedules final visual review for Monday, 12 October 2026.
PR66 is MERGED into main `cc90fc73bea6ae399383d8538035c6454dc7e65a`; existing
features, QA records/session and operational infrastructure passed main synchronization.
Final visual polish can be corrected; no operational PdM acceptance is inferred.

UX-08 implements presentation polish of the existing `/login` and reusable QA
sign-in form: original NADI logo, navy/green V1 layout, required-field guidance,
loading/error/expiry/password-change visuals and keyboard accessibility. FR-09 global
access remains a future requirement; no global redirect/enforcement, backend/cookie/
CSRF/RBAC/session-policy change, account provisioning or default credentials.
UX-09 is preparation/regression evidence, not final Product Owner acceptance.
See [Bundle C implementation/readiness](reliability-cockpit/docs/nadi-ux-bundle-c.md).

## Engineering Advisory & Distribution — binding PO scope, 2026-10-11

NADI-ENG-BUNDLE-A adds FR-11 structured Case Management (ENG-UX-01/02), FR-12
reviewed immutable advisory publication (ADV-01), FR-13 authenticated scoped
recipient readability/acknowledgement (ADV-02), and FR-14 existing local follow-up
traceability (ADV-03). ADV-04 real distribution remains future gated work.
Operations and Maintenance are audience categories, not fabricated operational
accounts/roles. Browser inputs cannot grant roles or choose their own audience.

Acceptance: exact asset access on list/detail/history/mutation; trusted server
identity and independent version-bound review/publication; source observations,
hypotheses, conclusion, evidence limitations and recommended follow-up remain
separate. Idempotency, stale-revision recovery, immutable snapshots, withdrawal,
explicit acknowledgement audit and denied-access tests must pass. In-app availability
is not delivery; acknowledgement is not recommendation acceptance or authorization.
Local planned/completed/independently verified follow-up never proves physical work.
No Maximo mutation, real notification, source request, global login or operational DB
migration is authorized. Delivery is SYNTHETIC QA pending PO/engineer UAT and rollout.
The [official track](plans/NADI-ROADMAP.md#engineering-delivery-track--nadi-eng-bundle-a--2026-10-11)
owns statuses and dependencies.

FR-11–FR-14 implementation candidate: structured Cases, reviewed version-bound
Advisories, QA recipient receipt and existing Recommendation/Action Board controls
are implemented on `codex/nadi-eng-bundle-a`. The source decision requires an
approved same-asset Case AND Recommendation. QA audience exercise policy is
server-owned and does not represent plant organizational grants. An explicit
QA-only schema prerequisite broadens the existing human-record constraint;
operational migration/activation remains gated. See
[Engineering implementation decision](reliability-cockpit/docs/nadi-eng-bundle-a.md).

### Integration-01 development checkpoint — 11 October 2026

PR67 Login presentation and PR68 Case/Advisory/recipient workflow are integrated in
one QA candidate from latest main, without merging the source PRs. Existing
requirements and separate global-login/operational/UAT gates are unchanged.
[Integration evidence](reliability-cockpit/docs/nadi-eng-integration-01.md) verifies
persistent synthetic workflow, trusted inline login, factual regression and safe
source rollback. Development QA PASS is separate from final Product Owner acceptance.

## FR-15 — Bahasa Indonesia dan panduan istilah (NADI-UX-ID-01)

Bahasa Indonesia menjadi bahasa utama presentation layer NADI, termasuk navigasi,
form, validasi, state pemuatan/kosong/error, pesan workflow dan label aksesibilitas.
PdM, FMEA, RCFA, Maximo, PI, Work Order, ACK dan istilah industri yang relevan tetap
terlihat. `/panduan/istilah` menyediakan pencarian padanan Indonesia/Inggris,
pengertian sederhana dan contoh dalam NADI, tanpa akses atau mutasi database.

Label bukan nilai kontrak: enum/status API, URL, satuan/timestamp, identitas,
isi evidence pengguna dan rekam tersimpan tidak diterjemahkan. `APPROVED` tampil
sebagai **Rekam disetujui**, bukan izin kerja. `ACK` hanya konfirmasi penerimaan;
`COMPLETED` lokal berbeda dari `VERIFIED`. `UNKNOWN`, `NOT ASSESSED` dan QA sintetis
harus tetap dapat dibedakan dari bukti faktual. Definisi kandidat metode/batas
engineering memakai penanda **Menunggu Validasi Engineer**.

Acceptance kandidat: regresi payload/protokol dan workflow, keyboard/kontras,
responsif 1440/768/390 serta CI exact-head; bahasa/visual PO dan engineer UAT tetap
merupakan gate terpisah. [Laporan implementasi](reliability-cockpit/docs/nadi-ux-id-01.md)
memisahkan pengujian komponen terisolasi dari visibility runtime persisten.
Tidak ada global authentication enforcement atau aktivasi operasional baru.


## FR-09 fullscreen Engineering QA entry — NADI-UX-LOGIN-01

`/login` is standalone without AppShell, sidebar, topbar or dashboard links. Successful existing authentication opens `/engineering/local`. Current-session logout and local-workspace expiry return to fullscreen login after clearing prior-user views. Existing factual development access and server QA/security policy remain unchanged. This UX correction is not activation of global authentication, production acceptance or engineer UAT.

[Implementation, boundaries and evidence](reliability-cockpit/docs/nadi-ux-login-01.md).

## FR-03/04 — PdM native input development checkpoint — 2026-10-13

[NADI-PDM-CENTER-INPUT-01](reliability-cockpit/docs/nadi-pdm-center-input-01.md)
adds a candidate native multi-point InspectionDraft v1.1 form, globally authorized
server register/event filters, page-scoped raw-sample scatter, existing independent
review and exact-revision Case evidence handoff. Original values/types/units/time,
UNKNOWN/NOT_ASSESSED and informational WO ownership remain unchanged. AREA FAN,
AREA MILL and Logsheet 6 kV are candidate workflow contexts; workbook fields and
Q01–Q10 remain PENDING_ENGINEER_VALIDATION. No live activation, schema migration,
Excel import, diagnosis, threshold or cross-inspection/PI comparability approval.
Implementation/testing, DRAFT PR, engineer approval and operational acceptance are
independent gates; see the report and official roadmap for actual delivery evidence.

PdM server-filter proof is mandatory for this candidate; older QA backends cannot
silently ignore filters. No frontend-only preview pairing or runtime activation
is approved here. Native drafts and failed intent IDs recover only for the same
trusted identity/scope and original edit revision.

## FR-03 workbook candidate preparation — 2026-10-15

[WORKBOOK-01](reliability-cockpit/docs/nadi-pdm-workbook-01.md) verifies the three
original engineer workbooks and implements three restricted candidate header
profiles. Nine direct fields retain original unit tokens; values, point identity
and time are not prefilled. Context selection never chooses/approves the method.
This does not approve all workbook variants, import calculated/diagnostic columns,
activate warning thresholds or change InspectionDraft v1.1. Engineer mapping,
Q01–Q10 and operational UAT remain pending; the general form stays available.

## PdM workbook checkpoint — 15 Oktober 2026 / WORKBOOK-02

[WORKBOOK-02](reliability-cockpit/docs/nadi-pdm-workbook-02.md) menambah empat keluarga Vibration dan dua konteks CEP provisional pada kandidat PR85. Total48 DIRECT (9 lama +39 baru),3 label temperatur berunit unresolved; seluruh profil menunggu engineer. IR Window bukan bukti IRT lengkap; OTHER provisional tidak mengaktifkan metode operasional. Tidak ada historical import, scoring, cross-inspection trend atau perubahan boundary keamanan.

## FR-07 checkpoint — 15 Oktober 2026

[System Integration Center candidate](reliability-cockpit/docs/nadi-integration-ui-01.md)
implements `/system-integration` in development from the existing read-only DTOs.
Availability, collection/source/projection freshness, identity, quality and
Registry/technical populations remain independent. It preserves Data Trust and
all technical routes; no source or operational control is added. Production
reading is not activated pending deployment authentication/authorization review.
Synthetic implementation/tests are distinct from Product Owner, operational
availability/freshness acceptance and engineer approval. Reports/Administration
complete product screens remain planned.

## FR-06 candidate checkpoint — 15 Oktober 2026

[Reports Center V1](reliability-cockpit/docs/nadi-reports-ui-01.md) implements
development-only `/reports` with two candidate previews: Data Coverage
(DataTrustView; no period filter) and Maintenance Activity (DecisionOverviewView;
7/30/90 days). Definitions remain DEVELOPMENT CANDIDATE — NOT OPERATIONALLY
APPROVED. Registry/technical populations, evidence classes, original time bases,
unknowns and chronology's independent bucket scope are retained. No new KPI,
export/distribution, schema, authentication activation or runtime promotion.
Production readers remain blocked pending deployment access review.

## FR-08 architecture readiness — NADI-ADMIN-READINESS-01 / 16 Oktober 2026

[Administration architecture](reliability-cockpit/docs/nadi-admin-readiness-01.md)
and [candidate matrix](reliability-cockpit/docs/nadi-admin-authorization-matrix.md)
are review-ready documentation from main5af41294745d7eb78eb14f617cacdbc223844564.
Existing AUTHOR/REVIEWER/ADMIN, QA login/session and private operator services are
distinct from a product account directory or web administrator. Seven missing API
contract groups and12 pending PO/security/operator decisions are recorded in the
[proposed plan](reliability-cockpit/docs/nadi-admin-implementation-plan.md). All
organizational mappings remain PROPOSED. No Administration UI/API, account/grant/
recovery operation, global authentication, source privilege or deployment is
implemented or activated by this task; ADMIN cannot override independent review.


## FR-03/04 — manual PdM package1–3 candidate — 21 October 2026

PO authorized origin of work, manual engineer analysis/follow-up text and reported
SR references on main44bc (PR108), followed by review, branch push and draft PR
when GO. [NADI-PDM-MANUAL-FOLLOW-UP-01](reliability-cockpit/docs/nadi-pdm-manual-follow-up-01.md)
extends FR-03/04 and NFR-01/04/05. Work origin can be department request or own PM52
finding, without mandatory operator approval. Analysis is human narrative; actual
measurements/observations/hypotheses stay separate. SR is reported-unverified,
distinct from WO, with no lookup/create/write to Maximo. Existing roles/session,
asset identity, audit/CAS/review and application JSON store are reused. Legacy
absence is not backfilled. Publication/CI, merge, visibility and operational/UAT
acceptance remain distinct; merge/activation/security changes are not authorized.


## 21 October 2026 — local factual-error and staged-history candidate

NADI-PDM-HISTORY-STAGING-01 is implemented locally on PR109/main891dfee8.
Executive Overview distinguishes403 capability/scope,401 session and actual
upstream/network unavailability without changing access policy. Offline XLS/XLSX
staging preserves source cells/dates/units/formula cache and identifies existing
partial events; a maximum25-record pilot is restricted to disposable application
copies and the existing validated CREATE/audit/receipt path. No guard increase,
canonical mapping, active-demo mutation, publication or deployment is implied.
[Scope, gates, qualification and next activation](reliability-cockpit/docs/nadi-pdm-history-staging-01.md).

## NADI-PDM-HISTORY-COMPLETE-01 — source-preserving historical coverage

Authorized implementation/test scope: preserve all relevant supplied Excel content
as navigable source history, including explicit unresolved dates/units/formulas,
compact provenance, safe retries and recoverable import. Source occurrences are
not new approved inspections, canonical asset mappings or diagnostic trends.
Acceptance requires per-source/sheet/physical-cell reconciliation, bounded authorized
reads, immutable links to prior samples, unchanged user revisions and isolated
recovery proof. Local full-source tests pass; live migration/import, publication,
engineer UAT and chart implementation remain separate.
[Detailed contract and qualification](reliability-cockpit/docs/nadi-pdm-complete-history-01.md).

Receipt integrity acceptance (22 October 2026): each committed source-to-existing-
record alias must be preserved as immutable receipt evidence. Replay must reject
missing/changed aliases after recovery, preserve legitimate later user revisions,
and never silently reconstruct links. This correction is implemented/tested only
in disposable copies; demo-target activation/import remains separately gated.

## Sprint 1 product simplification — 31 October 2026

The Product Owner authorized PR113's engineer-first direction. FR-03/04/05/07 now
have an isolated S1-01–S1-05 frontend candidate: five primary work areas, distinct
native/Excel history, continuous measurement entry and optional contextual Case.
[Implementation and preservation evidence](reliability-cockpit/docs/NADI-PDM-SIMPLIFICATION-SPRINT-01.md).
This is not PO visual/UAT acceptance or deployment. Existing contracts, review,
source read-only boundaries and runtime-only F23/F24 release gates remain in force.

## Approved runtime parity preservation — 31 October 2026

The authorized PR114 consolidation carries existing F23 display-only interpretation/
estimate and F24 explicit local-demo account policy, retaining raw custody, standard
authentication and source read-only semantics. No global password-policy reduction
or automatic diagnosis/Recommendation/WO write. [Current integrated acceptance](reliability-cockpit/docs/NADI-PDM-SPRINT1-ONE-PR-DELIVERY.md)
records source qualification separately from conditional live and PO acceptance.


## 1 November 2026 — PdM Sprint2 bounded usability candidate

S2-01–S2-05 implement the accepted Sprint1 visual direction: Register1/5/10 with
unchanged2MiB budget, native exact history context and distinct source history,
honest trend eligibility, compact M02 decisions and a disposable independent-review
workflow. [Integrated specification and evidence](reliability-cockpit/docs/NADI-PDM-SPRINT-02-DELIVERY.md)
retains F01–F24. This is a stacked candidate on unmerged PR114 AA; no schema/DTO/
auth change, new source request, trend policy, live cutover or phase completion.
Engineer method sign-off and PO acceptance remain PENDING.


## 1 November 2026 — FR-02/FR-07 asset evidence candidate

Sprint3 reuses existing exactasset maintenance and approved PI latest contracts,
adds contextual PdM return links and source/quality/clock disclosures, and preserves
five primary entries and Engineering workflows. Full mapping inventory is blocked
by current grants; historian history is NOT_QUALIFIED and KPI readiness remains
NOT_ELIGIBLE. [Implementation, limits and evidence](reliability-cockpit/docs/NADI-PDM-SPRINT-03-DELIVERY.md)
are distinct from deferred PO UI/UX, method/source-owner acceptance and activation.
