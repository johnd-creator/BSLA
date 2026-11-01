# Sprint4 proposed offline foundation

**SYNTHETIC TEST ONLY.** Not an active shared source contract, retained schema,
application service or authorization to evaluate/publish real KPIs. Application
runtime never imports this package. Operational eligibility always NOT_ELIGIBLE.

Models in `models.py` generate `packet.schema.json`, version `s4-candidate-1`.
Strict finite decimal-string hours (`h`), typed nullable original clocks/precision,
exact canonical asset+site/org+population, definition versions and source record/
revision/qualification lineage are mandatory. Synthetic policy approval is named
SYNTHETIC_APPROVED and cannot represent an engineer sign-off. Only synthetic source
lineage is accepted, and the engine rejects non-synthetic asset identity. No input
or output is persisted, no wall clock/network/DSN/business store is read, no app
route is mounted. Window validation uses the installed Python IANA timezone data;
a future operational reproducibility contract must pin/review that data version.

Supported *candidate synthetic policy* (not an approved operational method):

- Half-open failure window [start,end), timezone-aware precise original clocks,
  window IANA timezone/offset agreement. Window end is the deterministic cutoff;
  no now() or source-change clock substitution. Repair/exposure/outage intervals
  must be fully contained; unknown/date-only/naive/overflow clocks reject.
- Event identity is independent of WO. Explicit verified MAINTENANCE_ACTIVITY
  (PM/CM/other) is excluded; unverified classification blocks. Functional events
  count by distinct IDs; shared/child WO never defines a denominator.
- Same-ID/revision identical replay is excluded with a receipt. Conflicting replay
  or missing explicit supersession chain rejects; a complete explicit chain selects
  the final revision while preserving all earlier evidence. Duplicate links must
  identify an existing non-duplicate record and have consistent semantic content;
  no latest-arrival, fuzzy, time-based or WO-only grouping.
- Exposure coverage partitions the whole window without gaps/overlaps. Supplied
  measured operating hours need qualified evidence and cannot exceed the observed
  span or contradict known total outage. The capacity check only rejects a
  contradiction: it NEVER derives replacement operating hours. Zero exposure is
  NOT_ELIGIBLE, distinct from positive exposure with NO_FAILURES_OBSERVED.
- Completed repair episodes link qualifying in-window failures and start no earlier
  than failure onset. Explicit ACTIVE/WAITING/PLANNED intervals partition repair
  start→restoration. Waiting/planned exclusions require the explicit synthetic rule;
  no gap filling. Active intervals sum as exact integer microseconds before one
  decimal conversion; output arithmetic uses an explicit28-digit HALF_EVEN context
  independent of caller traps/precision/exponent bounds.
- Unresolved interval/episode envelope overlaps, contradictory standalone waiting/planned versus active claims, open/censored/reopened repair, multiple
  restorations for one failure, cross-window episodes and contradictory total
  outage fail closed. They are supported as explicit NOT_ELIGIBLE cases, not by
  inventing a new exclusion/attribution rule. New rules need separate approval.
- MTBF=qualified hours/distinct functional events. Positive complete exposure and
  zero events yields null+NO_FAILURES_OBSERVED. MTTR=active repair hours/completed
  episodes, distinct from total downtime. No completed episodes yields null+
  NO_COMPLETED_REPAIR_EPISODES. Never0/infinity for an absent denominator.

Every result includes scope/window/policy, original full source/revision lineage,
input SHA256, included IDs and sorted replay/supersession/exclusion receipts.
Receipts may identify a candidate interval even when another gate blocks the total;
only a metric's synthetic_status/included_ids determines numerical qualification.
MTBF/MTTR input gates are independent where meaningful (e.g. missing exposure
blocks MTBF but does not convert correct repair evidence into missing repair).
Common identity/version/policy contradictions block both.

Limits:2MiB JSON input, at most1000 records per type,100 intervals per repair,
20 evidence refs per record. Oversized/malformed packets produce null metrics with
explicit invalid-contract reason and no raw input/error leakage. No parser guesses
source objects or acquires historian data. Proposed operational adoption requires
source-owner/method approval and a separately reviewed contract/evaluation boundary.

Run from `reliability-cockpit`:
`PYTHONPATH=.:tests python -m unittest test_sprint4_foundation -v`.

Hand reference `reference-expected.synthetic.json` is independently specified:
600 supplied operating hours /2 functional events=300h MTBF;4 active repair hours /
2 completed episodes=2h MTTR. Calendar744h, waiting A2h, shared/child WO and total
outage are not substitute numerators/denominators. Generated visual reference is
imported only by test entry/fixture, never by application components.
