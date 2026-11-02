# Reliability KPI Computation

KPIs are computed by the cockpit from normalized data — they are NOT direct
Maximo fields. Formulas use explicit units (vendor-neutral).

| Metric | Formula | Unit | Inputs |
|---|---|---|---|
| MTBF | operating_hours / failures | hours | failure_count, total_operating_hours |
| MTTR | downtime_hours / failures | hours | failure_count, total_downtime_hours |
| AVAILABILITY | (total - downtime) / total × 100 | percent | total_operating_hours, total_downtime_hours |
| PM_COMPLIANCE | completed / scheduled × 100 | percent | pm_scheduled, pm_completed |

When `failures == 0`, MTBF/MTTR value is `null` (not zero) — a null indicates
"no failures observed in the window" rather than an absence of data.

Availability over a period uses operating hours + downtime hours as the
denominator. Period windows are explicit (`period_start`, `period_end`).

## Data gaps

- Failure count currently comes from work-order failure data
  (`work_order.failure_code`); the Maximo FAILURECODE master is still
  read-forbidden. Until it is verified, MTBF/MTTR reflect reported CM work
  orders with failure codes only.
- No downtime-report object yet; downtime is taken from
  `work_order.downtime_hours` / `equipment.downtime_total_hours`.
- `PM_COMPLIANCE` requires `worktype=PM` work orders; scheduled/planned counts
  depend on the PM object (currently forbidden) as an improvement.
## 1 November2026 — source audit correction, behavior preserved

The earlier CM wording is narrower than actual `_aggregate`: it counts **any
truthy failure_code** among work orders whose reported_at date lies in the inclusive
day window; it does not check CM. Missing downtime contributes0 and operating hours
are the legacy proxy `max(inclusive calendar hours − summed downtime,0)`. Legacy
MTTR uses total downtime divided by that code-based count. Sprint4 leaves the code,
store, API and metrics unchanged. These proxies do not meet the proposed qualified
functional-failure, operating-exposure or active-repair contracts.
