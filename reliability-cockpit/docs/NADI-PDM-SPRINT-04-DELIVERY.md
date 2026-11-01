# NADI-PDM-SPRINT-04-DELIVERY

1 November2026. S4-00 audited before coding. IMPLEMENTED_AND_LOCALLY_QUALIFIED; final publication gates below.
Base: PR116 exact `3778584a7d4f97b98aae44cea37838a34b61f5d0`, open/Draft and
stacked on PR115→114. Parent backend/frontend run41293638999 PASS. Main verified
`f1fc4e8b395691a17fe6d986bf14c772d37c1f2c`. Isolated branch
`codex/nadi-pdm-sprint-04`; no parent branch or live source is changed.

## S4-00 — prerequisites and architecture

Authority: [Sprint3 delivery](NADI-PDM-SPRINT-03-DELIVERY.md),
[Sprint4 prerequisite handoff](NADI-SPRINT4-PREREQUISITE-HANDOFF.md),
[KPI contract plan](NADI-RELIABILITY-KPI-CONTRACT-PLAN.md),
[source/application ADR007](adr/007-source-read-only-application-boundary.md).
Read root/scoped instructions, context, PRD, design/roadmap/status and source
ownership before implementation. Graph Tier2 generation2026-11-01T10:06:18Z,
coverage checks plus direct source reads; graph completeness is not claimed.

| Existing capability / meaning | Candidate treatment / remaining owner decision |
| --- | --- |
| Legacy KpiService in Cockpit store | Preserve exact source/formula/API; legacy counts every truthy failure_code within reported_at inclusive calendar days, NOT specifically CM. Null downtime contributes0 and operating proxy=max(calendar-hours−downtime,0). No method approval inferred |
| Mart maintenance_event | Exact registered identity, conservative event_type/raw status and activity clocks; source activity is not a functional failure or repair episode |
| PI latest selected signal | Original value/quality/clocks, not operating-hour exposure or a qualified historian interval |
| Failure definition/identity | MISSING; reliability engineer + maintenance owner sign functional failure, IDs, evidence and duplicate/child handling |
| Exposure/observation coverage | MISSING; operations + historian owner + reliability sign operating-hour source, quality, gaps, scope and window |
| Active repair versus outage | AVAILABLE_UNAPPROVED raw activity times; maintenance + reliability sign repair/restoration/wait/planned/censor/reopen rules |
| Version/window/exclusion policy | MISSING; reliability owner + contract reviewer sign effective version, half-open window, timezone/precision and attribution |
| Authenticated source access | Reuse existing exactasset GET/gateway; no grant or authentication changes |
| Live Reliability Performance input | No qualified canonical failure/exposure/repair endpoint exists. UI remains NOT_ELIGIBLE; source activity drilldown stays distinct |

No prerequisite prevents a technically correct *offline synthetic foundation*.
None authorizes operational evaluation. Candidate models/engine/tests live under
`contracts/sprint4`, unreachable from app routes/services. Existing active shared
contracts, stores, migrations, source acquisition and collectors remain unchanged.
Proposed contracts are not a second operational store or approved semantic policy.

Synthetic policy explicitly supports exact scope/version, aware precise clocks,
complete nonoverlapping exposure coverage, explicit functional identities, explicit
revision chains/replay/duplicate links, active/wait/planned repair intervals. Reject
unsupported overlaps, censor/reopen/cross-window episodes without clipping, now(),
source-changedate fallbacks or inferred owner approval. Operational status always
NOT_ELIGIBLE, even when a synthetic reference calculation qualifies.

## Publication and exact-source receipt

One [Draft PR117](https://github.com/johnd-creator/reliability-knowledge-starter/pull/117),
base branch `codex/nadi-pdm-sprint-03`. Exact baseline is
`3778584a7d4f97b98aae44cea37838a34b61f5d0`. Reviewed technical checkpoint
`923b7acd495f851f16f0227b785748551554d0f4` is followed by the final fail-closed IANA
boundary fix/tests and documentation. The final immutable HEAD, hosted CI run and
independent carry-forward are recorded in the final qualification receipt on PR117;
those are required before target technical PASS. No automatic merge/activation.

## Integrated implementation — S4-01–S4-05

| Requirement | Technical implementation | Operational boundary |
| --- | --- | --- |
| S4-01 | Strict proposed Packet/Result JSON schemas, explicit scope/population/window/precision, source/revision lineage; failure/activity/exposure/repair/outage models | Isolated `contracts/sprint4`; no active shared-contract or retained-schema change |
| S4-02 | Pure offline MTBF: supplied qualified operating hours / distinct functional failure IDs; complete coverage, no calendar proxy; positive exposure with0failures→null+NO_FAILURES_OBSERVED | SYNTHETIC_TEST_ONLY; operational eligibility always NOT_ELIGIBLE |
| S4-03 | Exact integer-microsecond active repair accumulation / completed episodes, independent of waiting/total downtime; explicit policy/exclusions; deterministic Decimal28 | Unknown/censored/reopened/cross-window/overlapping/contradictory evidence rejects; no restoration fabricated from now/change dates |
| S4-04 | Existing Laporan → Kinerja Reliabilitas; exactasset + explicit timezone-aware period; readiness matrix; lazy authorized activity/source detail; existing catalog and URL/back context preserved | No live metric, failure/repair dataset or calculator endpoint exists; no calculation or synthetic input imported by app |
| S4-05 | Hand reference, strict input/output schemas, negative/overlap/revision/clock/scope/coverage tests, actual React browser and accessibility matrix, existing regressions and immutable preservation fences | Technical tests neither approve source facts nor grant engineering method/PO acceptance |

Source-contract audit: existing shared `failure.schema.json` describes an event
inferred from WO failure-code data, not a reviewed functional-failure contract.
Existing `downtime.schema.json`/Downtime domain describe derived source downtime
until a verified downtime-report object is available, not active repair. These and
legacy `reliability-kpi.schema.json`, Mart/API/source behavior remain unchanged.
No automatic conversion/adoption or discovery of forbidden FAILURECODE/PM objects.

## Synthetic calculation reference and edge cases

[Candidate contract and precise policy](../contracts/sprint4/README.md),
[input](../contracts/sprint4/reference-input.synthetic.json),
[independent expected results](../contracts/sprint4/reference-expected.synthetic.json),
[packet schema](../contracts/sprint4/packet.schema.json),
[result schema](../contracts/sprint4/result.schema.json).

| Synthetic reference only | Numerator / denominator | Expected |
| --- | --- | --- |
| MTBF |600 measured operating hours /2 distinct verified synthetic functional events |300h |
| MTTR |4 active repair hours /2 completed synthetic repair episodes |2h |
| Waiting example |2 waiting hours inside first4h repair envelope |Excluded only by explicit synthetic waiting/planned rule |
| Calendar span |744h within observation window |Never substituted for operating hours |
| Positive complete exposure / zero failures |600h /0 events |null + NO_FAILURES_OBSERVED |
| Zero exposure |0 supplied operating hours |null + ZERO_OPERATING_EXPOSURE; not evidence of a valid no-failure observation |

All calculation results remain operationally NOT_ELIGIBLE. The numerical example
is only a fixture under SYNTHETIC_APPROVED policy, not a plant result or sign-off.
The UI test-only demonstrator cannot be reached through application routes/imports.

Executable negative fixtures cover: PM/CM as activities versus separately qualified
functional failure, child/shared WO, identical replay, explicit duplicate links,
conflicting revision/replay, complete supersession chain and preserved old evidence;
missing/null/boolean/nonfinite/zero hours, exposure gaps/overlap/bad quality,
contradiction with total outage; invalid/partial/naive/date-only/unknown-offset/
UTC-overflow clocks, IANA offset mismatch, DST spring-gap/fall-fold instants, half-open boundaries; exact mixed asset/
site/org/population/units/versions; incomplete repair, waiting/planned policy pending,
interval gap/overlap, overlapping episode envelopes including waiting interleaving,
reopen/censor/multiple restoration and pre-failure repair; contradictory standalone
waiting/planned versus active repair. No implicit clipping, repair-time inference,
interpolation, mean-from-WO-pages or canonical promotion.

The engine records original input/scope/window/policy, source record revisions,
input hash, metric included IDs and replay/supersession/exclusion receipts. A
candidate interval receipt is not a global result PASS; the metric's eligibility
and included_ids govern numerical output. Arithmetic is deterministic under an
explicit Decimal Context, independent of caller precision/traps/exponents. Active
interval segmentation cannot change duration: sum exact integer microseconds
first, divide only after summation. The caller input is preserved and not mutated.

## Eligibility / missing-data and engineering decision register

No responsible person's name or approval date is invented. Role owners below must
identify their accountable reviewer. Every decision is PENDING, with no operational
policy approval, effective date or approved evidence dataset recorded in this task.

| Decision / input | Current classification | Accountable role(s) / required sign-off |
| --- | --- | --- |
| Exact registered equipment | AVAILABLE_VERIFIED only after permitted Asset read | Registry/source owner confirms identity/membership effective intervals |
| Observation period/population | AVAILABLE_UNAPPROVED user request | Reliability + Operations approve scope, window/timezone/precision/as_of/censor/boundaries |
| Functional failure definition | MISSING | Reliability + Maintenance sign definition/version and qualifying events/evidence |
| Failure IDs versus WO/child/duplicate | MISSING | Maintenance + Reliability define stable event identity, aliases, duplicate receipts |
| Revision/supersession/historical correction | MISSING | Contract reviewer + Reliability sign correction/recompute/audit policy |
| Measured operating hours/quality | MISSING | Operations + Historian owner establish approved source, unit h, quality and time basis |
| Exposure coverage, zero hours, outage contradictions | MISSING | Operations + Reliability sign completeness/gap/overlap/physical consistency rules |
| Active repair/restoration | MISSING for selected asset until qualified dataset exists | Maintenance + Reliability verify active intervals and actual restoration evidence; raw activity-clock fields can be absent/null |
| Waiting/planned versus outage | AVAILABLE_UNAPPROVED source capability only, not per-asset evidence | Maintenance + Reliability sign explicit exclusions, waits and planned/nonoperating semantics |
| Open/censored/cross-window episodes | MISSING | Reliability + Contract reviewer define eligible attribution/exclusion; candidate rejects |
| Reopen/multiple restorations | MISSING | Maintenance + Reliability define episodes and restoration ownership; candidate rejects |
| Interval and episode overlap | MISSING | Maintenance + Reliability reconcile overlap before enabling a different policy |
| Authorized failure/repair/exposure read model | BLOCKED | Data owner + Contract reviewer approve canonical contract, scope and access boundary |
| Operational publication/PO visuals | BLOCKED / pending | Engineer method/source sign-off and PO review are separate from CI or synthetic qualification |

## F01–F24 preservation evidence

All existing28 route entries, five primary navigation definitions, runtime backend,
legacy KPI engine/API, auth/session/RBAC/CSRF/Origin/gateway, collectors, active
shared contracts, migrations and controller/deploy bytes are unchanged from exact
parent3778584. Existing report catalog definitions/coverage/maintenance readers
remain; only ReportsCenter adds the contextual readiness subview and scoped CSS.

| ID | Preserved feature and evidence |
| --- | --- |
| F01 | Native typed measurements/original values and units; unchanged services/contracts + input suites |
| F02 | Native/provisional exclusivity/raw capture preserved; capture/workbook suites |
| F03 | Work-origin conditional department preserved; no PR107/Maximo recovery/acquisition change |
| F04 | Human analysis/follow-up narrative preserved; no source-fact interpretation conversion |
| F05 | Reported-unverified SR references preserved; no source request/write |
| F06 | Sprint2 Register1/5/10/2MiB hook unchanged; existing browser/backend suites |
| F07 | Same-inspection sample wrapper/plot unchanged; cross-inspection trend NOT_ELIGIBLE/M02 pending |
| F08 | Lazy provisional source/keyset/byte history unchanged; source-history tests retained |
| F09 | Migration007, source profiles/aliases and originals untouched; no replay/import |
| F10 | Author/reviewer workflow commands and independent review preserved; existing HTTP/PG/browser tests |
| F11 | Deliberate approved-native Case/frozen revision unchanged; no automatic Case |
| F12 | Provisional Case/plot exclusion unchanged; no RAW promotion or guessed mapping |
| F13 | Cases/investigation/review/audit accessible contextually; source/services/paths preserved |
| F14 | Recommendation/reported existingWO service unchanged; no Maximo create/update |
| F15 | Advisory/Inbox/ACK unchanged and available; existing regression gates |
| F16 | Intent receipts/CAS/audit/command hooks unchanged; HTTP integrity regression |
| F17 | Draft recovery and synchronous session/scope clearing unchanged; browser regressions |
| F18 | RBAC/CSRF/Origin/session/gateway/policy/middleware byte-identical to3a;403 is access, not outage |
| F19 | Attachment metadata/custody unchanged; detail source link grants no upload/download authority |
| F20 | All28 page entries and six Asset tabs byte-identical to parent377; no new route/frontend |
| F21 | FMEA/maintenance/health/overhaul/RCFA utility routes retained; exactasset maintenance improved only |
| F22 | Existing Beranda/DataTrust/report definitions/readers preserved; contextual Laporan readiness added, no KPI publication/portfolio bypass |
| F23 | Source interpretation/estimates/proofs and six existing parity pins unchanged |
| F24 | Accounts/sessions/auth/controller/deploy bytes unchanged; no reset/login/grant/session write in Sprint4 |


## Qualification receipts and known limits

Local qualification:36 foundation tests plus9 unchanged legacy KPI tests PASS;
existing full backend regression checkpoint844 tests PASS (220 optional-environment
skips locally), all19 frontend contract/lint gates PASS, TypeScript and Next build
PASS. The final exact-head CI reruns the complete configured backend with disposable
PostgreSQL plus all frontend/browser gates; its actual outcome and exact final
publication SHA are recorded in the final receipt on the single stacked Draft PR.
A document cannot embed its own Git object ID; the immutable PR-head/CI receipt
identifies this report's final source. Until those gates PASS, technical status is
pending. No claim of operational backup/restore or live Sprint4 UAT is made here.

Actual component browser qualification:6 scenario groups,10 screenshots and8
WCAG2A/AA/2.1A/AA tested states,390/768/1440 light/dark, theme-control pressed state,
readiness form/retry, exact asset/period return and browser back/forward, lazy source
detail, loading/empty/missing-asset/401/403/503 and scope clearing. Network requests
are intercepted GETs at `.invalid`; no calculator, /kpis, historian or real source
request. [Synthetic gallery](evidence/nadi-pdm-sprint-04/README.md). Automated
accessibility checks are bounded to tested states and do not certify human UAT.

Limits:2MiB offline input,1000 records per kind,100 intervals/repair; malformed and
oversized inputs reject. A1000-failure synthetic case qualifies600/1000=0.6h within
the gross5s regression budget; this is not an operational query/latency SLA. No
active store/query plan is changed or benchmarked. Result fixtures preserve source
claims but cannot establish a qualified real input dataset.

Independent code/security/data-contract review found and drove tests for offset
normalization/UTC overflow, ambient Decimal context, segmentation invariance,
outage-capacity/wait contradictions, zero-exposure distinction, episode envelope
and repeated-restoration ambiguity, non-vacuous import isolation and truthful
per-asset readiness. Final immutable review/CI receipts are on the Draft PR; no
critical/unresolved actionable issue may remain before target technical status.
This is bounded independent technical review, not a claimed exhaustive scan.

## Runtime preservation and Sprint5 handoff

Active local Sprint2 is preserved at https://localhost:3000, frontend/backend
`3a01e842b5bfca08a5d508b8988dc6deb32c2961`. Official read-only controller status
is captured before/after; final identity/store/controller readiness equality is
recorded in the PR receipt. No Sprint4 activation, accounts/session/grants change,
source request/acquisition, collector operation, retained schema/data mutation or
merge occurred. Existing unmerged branches/checkpoints remain intact.

Target after all technical gates: SPRINT4_TECHNICAL_FOUNDATION_PASS_KPI_NOT_ELIGIBLE.
This is not method approved, PO accepted, merged, activated or production ready.
[Proposed Sprint5 stabilization handoff](NADI-SPRINT5-STABILIZATION-HANDOFF.md) lists
signed policy/data/UI and future activation requirements. Sprint5 is not started.
