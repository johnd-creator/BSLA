"""Versioned candidate inputs. No retained schema or operational approval."""
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr

Ref = Annotated[StrictStr, Field(min_length=1, max_length=200, pattern=r'^\S(?:.*\S)?$')]
Hours = Annotated[StrictStr, Field(pattern=r'^(?:0|[1-9][0-9]{0,11})(?:\.[0-9]{1,6})?$')]
class Model(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
class Clock(Model):
    original: Annotated[StrictStr, Field(min_length=1,max_length=80)] | None
    precision: Literal['SECOND','MICROSECOND','MINUTE','DATE','UNKNOWN']
class Evidence(Model):
    evidence_ref: Ref
    source_record_id: Ref
    revision: Annotated[StrictInt, Field(ge=1)]
    source_system: Literal['SYNTHETIC']
    qualification: Literal['SYNTHETIC_VERIFIED','UNVERIFIED']
class Scope(Model):
    canonical_asset_id: Ref
    site: Ref
    organization: Ref
    population_ref: Ref
    identity_evidence: Evidence
class Window(Model):
    start: Clock
    end: Clock
    timezone: Ref
class Policy(Model):
    definition_id: Ref
    version: Ref
    approval: Literal['SYNTHETIC_APPROVED','PENDING_ENGINEER_VALIDATION']
    failure_definition: Ref
    exposure_definition: Ref
    repair_definition: Ref
    evidence: Evidence
    window_rule: Literal['HALF_OPEN_FULLY_CONTAINED']
    duplicate_rule: Literal['EXPLICIT_LINKS_ONLY']
    overlap_rule: Literal['REJECT']
    reopened_rule: Literal['REJECT']
    censored_rule: Literal['REJECT']
    waiting_planned_rule: Literal['EXCLUDE_EXPLICIT_QUALIFIED','PENDING']
class Record(Model):
    record_id: Ref
    revision: Annotated[StrictInt, Field(ge=1)]
    supersedes_revision: Annotated[StrictInt, Field(ge=1)] | None
    duplicate_of: Ref | None
    scope: Scope
    definition_version: Ref
    evidence: Annotated[list[Evidence],Field(min_length=1,max_length=20)]
class Failure(Record):
    kind: Literal['FUNCTIONAL_FAILURE','MAINTENANCE_ACTIVITY']
    qualification: Literal['SYNTHETIC_VERIFIED','UNVERIFIED']
    occurred_at: Clock
    work_type: Ref | None
    work_order_refs: Annotated[list[Ref], Field(max_length=20)]
class Exposure(Record):
    start: Clock
    end: Clock
    operating_hours: Hours | None
    unit: Literal['h']
    quality: Literal['QUALIFIED','BAD','UNKNOWN']
class RepairInterval(Model):
    interval_id: Ref
    kind: Literal['ACTIVE','WAITING','PLANNED']
    start: Clock
    end: Clock
    evidence: Annotated[list[Evidence],Field(min_length=1,max_length=20)]
class Repair(Record):
    failure_event_id: Ref
    state: Literal['COMPLETED','OPEN','CENSORED','REOPENED']
    reopened_from: Ref | None
    repair_started_at: Clock
    restored_at: Clock
    intervals: Annotated[list[RepairInterval],Field(max_length=100)]
class Outage(Record):
    failure_event_id: Ref | None
    kind: Literal['TOTAL_OUTAGE','WAITING','PLANNED']
    start: Clock
    end: Clock
class Packet(Model):
    contract_version: Literal['s4-candidate-1']
    execution_mode: Literal['SYNTHETIC_TEST_ONLY']
    label: Literal['SYNTHETIC ONLY — NOT PLANT DATA']
    scope: Scope
    window: Window
    policy: Policy
    failure_inventory_complete: StrictBool
    failure_inventory_evidence: Evidence
    repair_inventory_complete: StrictBool
    repair_inventory_evidence: Evidence
    exposure_coverage_complete: StrictBool
    exposure_coverage_evidence: Evidence
    failures: Annotated[list[Failure],Field(max_length=1000)]
    exposures: Annotated[list[Exposure],Field(max_length=1000)]
    repairs: Annotated[list[Repair],Field(max_length=1000)]
    outages: Annotated[list[Outage],Field(max_length=1000)]

DecimalResult = Annotated[StrictStr, Field(pattern=r'^[0-9]+(?:\.[0-9]+)?(?:E[+-]?[0-9]+)?$')]
class MetricResult(Model):
    metric: Literal['MTBF','MTTR']
    value: DecimalResult | None
    unit: Literal['h']
    synthetic_status: Literal['QUALIFIED_SYNTHETIC','NOT_ELIGIBLE']
    reasons: list[Ref]
    numerator_hours: DecimalResult | None
    denominator: Annotated[StrictInt,Field(ge=0)] | None
    included_ids: list[Ref]
class Receipt(Model):
    kind: Ref
    record_id: Ref
    reason: Ref
    revision: Annotated[StrictInt,Field(ge=1)] | None = None
    superseded_by: Annotated[StrictInt,Field(ge=1)] | None = None
    target: Ref | None = None
    work_type: Ref | None = None
    hours: DecimalResult | None = None
    active_hours: DecimalResult | None = None
    episode: Ref | None = None
    kind_claim: Ref | None = None
class Result(Model):
    contract_version: Literal['s4-result-1']
    execution_mode: Literal['SYNTHETIC_TEST_ONLY']
    operational_eligibility: Literal['NOT_ELIGIBLE']
    metrics: Annotated[list[MetricResult],Field(min_length=2,max_length=2)]
    audit: list[Receipt]
    label: Literal['SYNTHETIC ONLY — NOT PLANT DATA'] | None = None
    operational_reason: Ref | None = None
    scope: Scope | None = None
    window: Window | None = None
    definition: Policy | None = None
    input_sha256: Annotated[StrictStr,Field(pattern=r'^[0-9a-f]{64}$')] | None = None
    arithmetic: Literal['DECIMAL_28_HALF_EVEN'] | None = None
    source_lineage: Packet | None = None
