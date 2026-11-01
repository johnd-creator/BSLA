"""Pure deterministic SYNTHETIC-only foundation. No IO, store, clock or app hook.

All outputs remain operationally NOT_ELIGIBLE. Candidate numerical results only
qualify a synthetic reference under the packet's explicitly synthetic policy.
"""
import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, Context, localcontext, ROUND_HALF_EVEN, InvalidOperation, DivisionByZero, Overflow
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from pydantic import ValidationError
from .models import Packet

MAX_BYTES = 2 * 1024 * 1024
class Rejected(ValueError):
    pass

def instant(clock):
    value=clock.original
    if clock.precision not in {'SECOND','MICROSECOND'} or not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})',value):
        raise Rejected('INCOMPLETE_OR_IMPRECISE_CLOCK')
    offset=re.search(r'([+-])(\d{2}):(\d{2})$',value)
    if offset and (int(offset[2])>23 or int(offset[3])>59 or offset[0]=='-00:00'):raise Rejected('INVALID_OR_UNKNOWN_UTC_OFFSET')
    try:
        stamp=datetime.fromisoformat(value)
    except ValueError:
        raise Rejected('INVALID_CLOCK') from None
    if clock.precision=='SECOND' and stamp.microsecond:
        raise Rejected('CLOCK_PRECISION_CONTRADICTION')
    try:return stamp.astimezone(timezone.utc)
    except (OverflowError,ValueError):raise Rejected('CLOCK_UTC_OVERFLOW') from None

def microseconds(start,end):
    delta=end-start
    return (delta.days*86400+delta.seconds)*1000000+delta.microseconds

def hours(start,end):
    return Decimal(microseconds(start,end))/Decimal(3600000000)

def qualified(evidence):
    return all(e.qualification=='SYNTHETIC_VERIFIED' for e in evidence)

def _evaluate(packet):
    receipts=[]
    def receipt(kind,record_id,reason,**detail):
        receipts.append(dict(kind=kind,record_id=record_id,reason=reason,**detail))
    common=[]; bf=[]; tr=[]
    def block(bucket,reason):
        if reason not in bucket:bucket.append(reason)
    try:
        start,end=instant(packet.window.start),instant(packet.window.end)
        if start>=end:raise Rejected('INVALID_WINDOW')
        zone=ZoneInfo(packet.window.timezone)
        for clock,stamp in [(packet.window.start,start),(packet.window.end,end)]:
            if datetime.fromisoformat(clock.original).utcoffset()!=stamp.astimezone(zone).utcoffset():
                raise Rejected('WINDOW_TIMEZONE_OFFSET_MISMATCH')
    except (Rejected,ZoneInfoNotFoundError,ValueError) as error:
        return _result(packet,[],[],[],[],['INVALID_WINDOW_OR_TIMEZONE'],['INVALID_WINDOW_OR_TIMEZONE'],receipts)
    if not packet.scope.canonical_asset_id.startswith('asset:SYNTHETIC:'):
        block(common,'SYNTHETIC_SCOPE_REQUIRED')
    if packet.policy.approval!='SYNTHETIC_APPROVED' or not qualified([packet.policy.evidence,packet.scope.identity_evidence]):
        block(common,'POLICY_OR_IDENTITY_UNQUALIFIED')
    version=packet.policy.version
    all_records=packet.failures+packet.exposures+packet.repairs+packet.outages
    for record in all_records:
        if record.scope!=packet.scope or record.definition_version!=version:
            block(common,'MIXED_SCOPE_OR_DEFINITION_VERSION')
        if not qualified(record.evidence):
            block(common,'UNQUALIFIED_SOURCE_EVIDENCE')
    # Revision and replay handling is independent of arrival order, never latest-wins.
    def revisions(records,kind):
        groups=defaultdict(dict)
        for row in records:
            old=groups[row.record_id].get(row.revision)
            if old:
                if old!=row:block(common,'CONFLICTING_SAME_REVISION')
                else:receipt(kind,row.record_id,'IDENTICAL_REPLAY_EXCLUDED',revision=row.revision)
            else:groups[row.record_id][row.revision]=row
        result=[]
        for key in sorted(groups):
            versions=groups[key];ordered=sorted(versions)
            for i,rev in enumerate(ordered):
                row=versions[rev]
                if row.supersedes_revision!=(ordered[i-1] if i else None):
                    block(common,'UNRESOLVED_REVISION_CHAIN')
                if i<len(ordered)-1:receipt(kind,key,'EXPLICIT_SUPERSEDED_REVISION_EXCLUDED',revision=rev,superseded_by=ordered[i+1])
            result.append(versions[ordered[-1]])
        return result
    failures=revisions(packet.failures,'FAILURE');exposures=revisions(packet.exposures,'EXPOSURE')
    repairs=revisions(packet.repairs,'REPAIR');outages=revisions(packet.outages,'OUTAGE')
    def duplicates(records,kind):
        by_id={row.record_id:row for row in records};result=[]
        for row in records:
            if row.duplicate_of is None:result.append(row);continue
            target=by_id.get(row.duplicate_of)
            if target is None or target.duplicate_of is not None or target.record_id==row.record_id:
                block(common,'UNRESOLVED_DUPLICATE_LINK');continue
            # Explicit link alone cannot excuse contradictory time/value evidence.
            skip={'record_id','revision','supersedes_revision','duplicate_of','evidence','work_order_refs'}
            if row.model_dump(exclude=skip)!=target.model_dump(exclude=skip):
                block(common,'CONTRADICTORY_DUPLICATE');continue
            receipt(kind,row.record_id,'EXPLICIT_DUPLICATE_EXCLUDED',target=target.record_id,revision=row.revision)
        return result
    failures=duplicates(failures,'FAILURE');exposures=duplicates(exposures,'EXPOSURE')
    repairs=duplicates(repairs,'REPAIR');outages=duplicates(outages,'OUTAGE')
    selected_failures=[]
    if not packet.failure_inventory_complete or not qualified([packet.failure_inventory_evidence]):
        block(bf,'FAILURE_INVENTORY_INCOMPLETE');block(tr,'FAILURE_INVENTORY_INCOMPLETE')
    for row in failures:
        if row.qualification!='SYNTHETIC_VERIFIED':
            block(bf,'FAILURE_CLASSIFICATION_UNQUALIFIED');block(tr,'FAILURE_CLASSIFICATION_UNQUALIFIED');continue
        if row.kind=='MAINTENANCE_ACTIVITY':
            receipt('FAILURE',row.record_id,'ORDINARY_MAINTENANCE_EXCLUDED',work_type=row.work_type);continue
        try:stamp=instant(row.occurred_at)
        except Rejected as error:
            block(bf,str(error));block(tr,str(error));continue
        if not start<=stamp<end:
            receipt('FAILURE',row.record_id,'OUTSIDE_HALF_OPEN_WINDOW');continue
        selected_failures.append(row)
        receipt('FAILURE',row.record_id,'QUALIFYING_FUNCTIONAL_FAILURE',revision=row.revision)
    selected_ids={row.record_id for row in selected_failures}
    exposure_hours=[]
    if not packet.exposure_coverage_complete or not qualified([packet.exposure_coverage_evidence]):block(bf,'EXPOSURE_COVERAGE_UNQUALIFIED')
    spans=[]
    for row in exposures:
        try:
            a,b=instant(row.start),instant(row.end)
            if not start<=a<b<=end:raise Rejected('EXPOSURE_WINDOW_CONTRADICTION')
            if row.operating_hours is None or row.quality!='QUALIFIED':raise Rejected('OPERATING_EXPOSURE_MISSING_OR_BAD')
            value=Decimal(row.operating_hours)
            if value*Decimal(3600000000)>Decimal(microseconds(a,b)):raise Rejected('OPERATING_HOURS_EXCEED_OBSERVED_INTERVAL')
            spans.append((a,b,row.record_id));exposure_hours.append(value)
            receipt('EXPOSURE',row.record_id,'QUALIFIED_OPERATING_HOURS',hours=row.operating_hours,revision=row.revision)
        except Rejected as error:block(bf,str(error))
    position=start
    for a,b,key in sorted(spans):
        if a!=position:block(bf,'EXPOSURE_GAP_OR_OVERLAP')
        position=b
    if position!=end:block(bf,'EXPOSURE_GAP_OR_OVERLAP')
    if sum(exposure_hours,Decimal(0))==0:block(bf,'ZERO_OPERATING_EXPOSURE')
    active_microseconds=[];selected_repairs=[];active_spans=[];repair_spans=[]
    failure_times={r.record_id:instant(r.occurred_at) for r in selected_failures}
    if not packet.repair_inventory_complete or not qualified([packet.repair_inventory_evidence]):block(tr,'REPAIR_INVENTORY_INCOMPLETE')
    completed_by_failure=defaultdict(int)
    for row in repairs:
        if row.state=='COMPLETED':completed_by_failure[row.failure_event_id]+=1
    if any(n>1 for n in completed_by_failure.values()):block(tr,'MULTIPLE_RESTORATIONS_FOR_FAILURE')
    for row in repairs:
        if row.state!='COMPLETED' or row.reopened_from is not None:
            block(tr,'OPEN_CENSORED_OR_REOPENED_REPAIR');receipt('REPAIR',row.record_id,'REPAIR_UNRESOLVED');continue
        if row.failure_event_id not in selected_ids:
            block(tr,'REPAIR_FAILURE_LINK_UNQUALIFIED');continue
        try:
            a,b=instant(row.repair_started_at),instant(row.restored_at)
            if not start<=a<b<=end or a<failure_times[row.failure_event_id]:raise Rejected('REPAIR_WINDOW_OR_FAILURE_CLOCK_CONTRADICTION')
            spans=[];ids=set();row_microseconds=0;active_count=0
            for interval in row.intervals:
                if interval.interval_id in ids:raise Rejected('DUPLICATE_REPAIR_INTERVAL')
                ids.add(interval.interval_id)
                x,y=instant(interval.start),instant(interval.end)
                if not a<=x<y<=b or not qualified(interval.evidence):raise Rejected('REPAIR_INTERVAL_UNQUALIFIED')
                spans.append((x,y,interval.interval_id))
                if interval.kind=='ACTIVE':
                    active_count+=1;row_microseconds+=microseconds(x,y);active_spans.append((x,y,row.record_id))
                    receipt('REPAIR_INTERVAL',interval.interval_id,'CANDIDATE_ACTIVE_REPAIR_INTERVAL',episode=row.record_id)
                elif packet.policy.waiting_planned_rule!='EXCLUDE_EXPLICIT_QUALIFIED':raise Rejected('WAIT_PLANNED_POLICY_PENDING')
                else:receipt('REPAIR_INTERVAL',interval.interval_id,'EXPLICIT_'+interval.kind+'_EXCLUDED',episode=row.record_id)
            position=a
            for x,y,key in sorted(spans):
                if x!=position:raise Rejected('REPAIR_GAP_OR_OVERLAP')
                position=y
            if position!=b or not active_count:raise Rejected('INCOMPLETE_ACTIVE_REPAIR')
            active_microseconds.append(row_microseconds);selected_repairs.append(row);repair_spans.append((a,b,row.record_id))
            receipt('REPAIR',row.record_id,'COMPLETED_REPAIR_INCLUDED',revision=row.revision,active_hours=str(Decimal(row_microseconds)/Decimal(3600000000)))
        except Rejected as error:block(tr,str(error))
    last_envelope=None
    for a,b,key in sorted(repair_spans):
        if last_envelope is not None and a<last_envelope:block(tr,'OVERLAPPING_REPAIR_EPISODES')
        last_envelope=max(last_envelope,b) if last_envelope else b
    last_end=None
    for a,b,key in sorted(active_spans):
        if last_end is not None and a<last_end:block(tr,'OVERLAPPING_ACTIVE_REPAIR_EPISODES')
        last_end=max(last_end,b) if last_end else b
    total_outages=[]
    for row in outages:
        try:
            a,b=instant(row.start),instant(row.end)
            if not start<=a<b<=end:raise Rejected('OUTAGE_WINDOW_CONTRADICTION')
            if row.failure_event_id is not None and row.failure_event_id not in selected_ids:raise Rejected('OUTAGE_FAILURE_LINK_UNQUALIFIED')
            if row.kind=='TOTAL_OUTAGE':
                total_outages.append((a,b))
                for repair in selected_repairs:
                    if repair.failure_event_id==row.failure_event_id and not a<=instant(repair.repair_started_at)<instant(repair.restored_at)<=b:raise Rejected('OUTAGE_REPAIR_CONTRADICTION')
            if row.kind in {'WAITING','PLANNED'}:
                if row.failure_event_id is None:raise Rejected('UNLINKED_WAIT_OR_PLANNED_CLAIM')
                for repair in selected_repairs:
                    if repair.failure_event_id==row.failure_event_id:
                        for interval in repair.intervals:
                            if interval.kind=='ACTIVE' and max(a,instant(interval.start))<min(b,instant(interval.end)):raise Rejected('WAIT_PLANNED_ACTIVE_CONTRADICTION')
            receipt('OUTAGE',row.record_id,'NOT_ACTIVE_REPAIR_INPUT',kind_claim=row.kind,revision=row.revision)
        except Rejected as error:block(tr,str(error));block(bf,str(error))
    prior=None
    for a,b in sorted(total_outages):
        if prior is not None and a<prior:block(bf,'OVERLAPPING_TOTAL_OUTAGES');block(tr,'OVERLAPPING_TOTAL_OUTAGES')
        prior=max(prior,b) if prior else b
    for exposure in exposures:
        try:
            a,b=instant(exposure.start),instant(exposure.end)
            unavailable=sum(microseconds(max(a,x),min(b,y)) for x,y in total_outages if max(a,x)<min(b,y))
            if exposure.operating_hours is not None and Decimal(exposure.operating_hours)*Decimal(3600000000)>Decimal(microseconds(a,b)-unavailable):block(bf,'EXPOSURE_OUTAGE_CONTRADICTION')
        except Rejected:pass  # Original exposure validation already records the blocking reason.
    return _result(packet,selected_failures,selected_repairs,exposure_hours,active_microseconds,sorted(set(common+bf)),sorted(set(common+tr)),receipts)

def _result(packet,failures,repairs,exposure,active,bf,tr,receipts):
    def metric(name,values,records,reasons):
        total=sum(values,Decimal(0));denominator=len(records)
        divisor=Decimal(3600000000) if name=='MTTR' else Decimal(1)
        numerator=total/divisor
        if reasons:return dict(metric=name,value=None,unit='h',synthetic_status='NOT_ELIGIBLE',reasons=sorted(set(reasons)),numerator_hours=None,denominator=None,included_ids=[])
        reason='NO_FAILURES_OBSERVED' if name=='MTBF' else 'NO_COMPLETED_REPAIR_EPISODES'
        return dict(metric=name,value=str(total/(divisor*Decimal(denominator))) if denominator else None,unit='h',synthetic_status='QUALIFIED_SYNTHETIC',reasons=[] if denominator else [reason],numerator_hours=str(numerator),denominator=denominator,included_ids=sorted(r.record_id for r in records))
    raw=packet.model_dump(mode='json')
    return dict(contract_version='s4-result-1',execution_mode='SYNTHETIC_TEST_ONLY',label=packet.label,operational_eligibility='NOT_ELIGIBLE',operational_reason='ENGINEERING_POLICY_AND_SOURCE_EVIDENCE_NOT_APPROVED',scope=raw['scope'],window=raw['window'],definition=raw['policy'],input_sha256=hashlib.sha256(json.dumps(raw,sort_keys=True,separators=(',',':')).encode()).hexdigest(),arithmetic='DECIMAL_28_HALF_EVEN',metrics=[metric('MTBF',exposure,failures,bf),metric('MTTR',active,repairs,tr)],audit=sorted(receipts,key=lambda r:json.dumps(r,sort_keys=True)),source_lineage=raw)

def evaluate(document):
    """Bounded pure JSON input; preserve lineage, no operational execution path."""
    try:
        encoded=json.dumps(document,allow_nan=False).encode()
        if len(encoded)>MAX_BYTES:raise ValueError('payload')
        packet=Packet.model_validate(document)
    except (ValidationError,ValueError,TypeError,RecursionError):
        return dict(contract_version='s4-result-1',operational_eligibility='NOT_ELIGIBLE',execution_mode='SYNTHETIC_TEST_ONLY',metrics=[dict(metric=k,value=None,unit='h',synthetic_status='NOT_ELIGIBLE',reasons=['INVALID_OR_OVERSIZED_CANDIDATE_CONTRACT'],numerator_hours=None,denominator=None,included_ids=[]) for k in ['MTBF','MTTR']],audit=[])
    with localcontext(Context(prec=28,rounding=ROUND_HALF_EVEN,Emin=-999999,Emax=999999,capitals=1,clamp=0,traps=[InvalidOperation,DivisionByZero,Overflow])):
        return _evaluate(packet)
