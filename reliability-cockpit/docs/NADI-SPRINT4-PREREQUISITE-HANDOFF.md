# Sprint4 data-contract handoff — NOT_ELIGIBLE

This is an offline prerequisite contract, not Sprint4 implementation or engineer
approval. Existing [KPI contract plan](NADI-RELIABILITY-KPI-CONTRACT-PLAN.md) retains
its authority and existing legacy metrics retain their original limited semantics.
No new KPI, threshold, diagnosis, health, severity or recommendation is computed.

| Input | Repository evidence now | Status / remaining owner decision |
| --- | --- | --- |
| Exact equipment identity / BSR/IP scope | Registered Asset + exact maintenance relationship; pilot mapping only | AVAILABLE_VERIFIED within recorded scope; source owner resolves others |
| Observation period | No approved operational window/exposure coverage contract | MISSING; reliability owner defines [start,end), boundaries/censoring and population |
| Failure-event ID / functional failure | WO/event IDs identify activities, not independently verified functional failures | MISSING; engineer defines stable failure/episode IDs, revisions, qualifying evidence |
| Source traceability | Canonical maintenance ID/WO/site/org/contract; raw vendor provenance narrower in public DTO | AVAILABLE_UNAPPROVED for failure traceability; validate event-to-source evidence |
| Preventive/corrective | Raw event_type/status values | AVAILABLE_UNAPPROVED; owner signs classification/version/exclusions; CM is not a failure |
| Ordinary activity versus failure | No authorized conversion from WO to functional failure | MISSING; no failure-code-master discovery/write |
| Operating exposure/hours and quality | PI latest signal does not supply operating exposure; calendar time is not operating time | MISSING; separately governed source contract, gaps/quality/time basis |
| Failure start | actual_start/source_changed_at not established failure onset | AVAILABLE_UNAPPROVED raw clocks; no fallback source-change-as-failure |
| Repair start/end | actual_start/finish are source activity claims only | AVAILABLE_UNAPPROVED; engineer verifies active repair/restoration and timezone/precision |
| Active repair versus total outage | duration/labor/downtime raw fields | AVAILABLE_UNAPPROVED; waits/planned downtime excluded only by signed policy |
| Incomplete clocks | Nullable source clocks preserved | MISSING policy; no midnight/zero/now filling or invented durations |
| Overlap | No approved episode-interval union/attribution | MISSING; no double count; preserve source episodes until reviewed |
| Reopened WO | One WO may span episodes; one failure may have child WO | MISSING; signed episode/supersedes rules, do not dedup solely by WO |
| Repeated status updates | Canonical current-snapshot PK upsert | AVAILABLE_UNAPPROVED for event reconstruction; snapshot is not full transition history |
| Duplicate events | Unique canonical source identity differs from unique failure identity | MISSING; accountable failure-ID and duplicate/supersedes evidence |
| Full mapping candidate detail / DCS | Existing gateway boundary / discovery-only integration | BLOCKED; independently authorized contract/source-owner scope required |

Proposed versioned record shapes for the future implementation:

- Equipment/window: canonical_asset_id, site/org, original start/end with timezone
  and precision, membership effective intervals, coverage evidence/version/owner.
- Failure: failure_event_id, exact asset, functional_failure_definition_version,
  occurred_at original clock/precision, source refs/revisions, verification status,
  parent/child/supersedes refs and exclusions with reasons.
- Repair: repair_episode_id, failure_event_id, repair_started_at, restored_at,
  active intervals, waiting/planned intervals, original clocks/quality/evidence,
  censor/reopen/overlap decisions. Total outage and active repair remain separate.
- Exposure: exact asset/window, operating hours or authorized operating intervals,
  explicit `h`, source/time/quality/coverage evidence, gaps/exclusions, policy version.

These are design prerequisites, not claims these fields are populated. Accepted
source contracts remain unchanged. `reliability-kpi-readiness.schema.json` requires
all17 prerequisite entries with status, evidence_ref, owner and definition_version,
rejects extra fields (including metric results). The pure offline readiness tool
validates completeness and **always NOT_ELIGIBLE** pending separately authorized
Sprint4 policy/implementation; synthetic complete fixtures cannot approve methods.

Executable fixtures cover raw PM/CM insufficient semantics, missing exposure,
unknown failure/repair clocks, overlap, reopened WO, duplicates and repeated status
updates as distinct blocking prerequisites. They do not simulate an approved KPI
formula. Before Sprint4: responsible engineer and source owners sign each scoped
version, then separately authorize technical implementation and its interval/event
validation tests. No automatic start after Sprint3.
