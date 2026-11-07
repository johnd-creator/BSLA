"""Manual resumable 50-row keyset sweep with an independent source verification pass.

Maximo numeric assetid filtering/order were verified by a bounded source probe.
No page-number links are retained or replayed. Every observed page is staged
atomically before advancing its numeric checkpoint. Ordinary sync cursors and
Registry membership are never touched. Staging is not an operational new DB.
"""
from collections import Counter
from datetime import datetime,timezone,timedelta
import hashlib,json,time
from src.adapters.maximo.mappers import equipment_from_payload
from src.adapters.maximo.oslc_client import ASSET_DETAIL_FIELDS,oslc_pop_integer,oslc_timestamp
from src.repositories.asset_inventory_sweep import SweepStore
from src.repositories.asset_inventory import AssetInventoryStore
from src.services.asset_inventory import local_payloads,resolve_scope,classify

VERIFY_FIELDS=('assetid','assetnum','siteid','orgid','eq11','parent','changedate','status','description','assettype')
class SweepGuard(ValueError):pass

def signature(raw):
    value={k:raw.get(k) for k in VERIFY_FIELDS}
    value['assetid']=oslc_pop_integer(raw,'assetid')
    changed=oslc_timestamp(value.get('changedate'))
    value['changedate']=changed.isoformat() if changed else value.get('changedate')
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def version_only_advanced(summary, full):
    """Accept a newer exact snapshot only when all verified business fields agree.

    Some active source assets advance changedate between the list and exact GET.
    This is not an atomic source snapshot. Keep the newer full payload, and audit
    the observation; changed business fields or missing/regressing versions fail.
    """
    if any(summary.get(k) != full.get(k) for k in VERIFY_FIELDS if k not in ('changedate', 'assetid')):
        return False
    if oslc_pop_integer(summary, 'assetid') != oslc_pop_integer(full, 'assetid'):
        return False
    before = oslc_timestamp(summary.get('changedate'))
    after = oslc_timestamp(full.get('changedate'))
    if before is None or after is None:
        return False
    if before.tzinfo is None: before = before.replace(tzinfo=timezone.utc)
    if after.tzinfo is None: after = after.replace(tzinfo=timezone.utc)
    return after > before


def clean(raw):
    # Only approved business scalar fields enter staging; no hrefs/cookies/person fields.
    result={k:v for k,v in raw.items() if k in ASSET_DETAIL_FIELDS and isinstance(v,(str,int,float,bool,type(None)))}
    result['assetid']=oslc_pop_integer(raw,'assetid')
    return result

def business_signature(raw):
    # The full approved scalar projection is compared, not only hierarchy fields.
    values = clean(raw)
    values = {k: values.get(k) for k in ASSET_DETAIL_FIELDS if k != 'changedate'}
    return hashlib.sha256(json.dumps(values,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


def validate_page(rows,*,lower,upper,size=50):
    if len(rows)>size:raise SweepGuard('PAGE_SIZE_MISMATCH')
    previous=lower;names=set();result=[]
    for raw in rows:
        identity=oslc_pop_integer(raw,'assetid');name=raw.get('assetnum')
        if identity is None or not previous<identity<=upper:raise SweepGuard('NON_MONOTONIC_ASSETID')
        if not isinstance(name,str) or not name or name!=name.strip() or len(name)>60 or name in names:raise SweepGuard('DUPLICATE_OR_INVALID_ASSETNUM')
        if (raw.get('siteid'),raw.get('orgid'))!=('BSR','IP'):raise SweepGuard('SOURCE_SCOPE_MISMATCH')
        names.add(name);previous=identity;result.append((identity,clean(raw),signature(raw)))
    return result

def source_page(client,where,fields,*,order='+assetid',size=50):
    pages=client.iterate_pages('mxapiasset',where=where,required_scope='siteid="BSR"',
        select=list(fields),order_by=order,page_size=size,max_pages=1,identity_field='assetid',strict_members=True,allow_resource_links=False)
    try:return next(pages,[])
    finally:pages.close()

def publish_sweep(store,reference,sweeps,identity):
    run=sweeps.get(identity)
    if run.state!='VERIFIED':raise SweepGuard('UNVERIFIED_PUBLICATION_BLOCKED')
    started=datetime.now(timezone.utc)
    fresh={r['assetnum']:r for r in sweeps.verified_payloads(identity)}
    payloads={r['assetnum']:r for r in local_payloads(store._db)}
    for name,row in fresh.items():
        old=oslc_timestamp(payloads.get(name,{}).get('changedate'));new=oslc_timestamp(row.get('changedate'))
        if old and old.tzinfo is None:old=old.replace(tzinfo=timezone.utc)
        if new and new.tzinfo is None:new=new.replace(tzinfo=timezone.utc)
        if old is None or (new is not None and new>=old):payloads[name]=row
    admitted=resolve_scope(payloads.values());inventory=AssetInventoryStore(store._db)
    result={'mode':'MANUAL_KEYSET_VERIFIED','sweep_id':identity,'errors':0,'full_source_baseline_complete':True,
        'stop_reason':'SOURCE_EXHAUSTED_AND_VERIFIED','source_rows':len(fresh),'inserted':0,'updated':0,'unchanged':0,
        'source_verification':'NUMERIC_ASSETID_KEYSET_ID_VERSION_RECHECK_AND_CHANGEDATE_TAIL',
        'source_verified_at':run.updated_at.isoformat(),'version_advance_observations':run.result.get('version_advance_observations',0),'scope':{'site':'BSR','org':'IP','unit':'CS01'}}
    for name,basis in sorted(admitted.items()):
        if name in fresh:
            result[store.upsert_equipment_manual(equipment_from_payload(fresh[name]),raw=fresh[name])]+=1
        category,proof=classify(name,reference)
        inventory.upsert(name,category,basis,proof,started,seen_in_source=name in fresh)
    inventory.deactivate_outside(admitted)
    result.update(inventory_assets=len(admitted),category_counts=dict(Counter(classify(n,reference)[0] for n in admitted)),retained_not_seen_in_scan=len(set(admitted)-set(fresh)))
    inventory.record_scan(result,started);sweeps.save_result(identity,result,published=True)
    return result

def collect_sweep_batch(client,store,reference,*,identity=None,new=False,max_requests=40,max_seconds=150,page_size=50,monotonic=time.monotonic,publish=True):
    if page_size not in (10,25,50):raise ValueError('checkpoint pages must be 10, 25 or 50 rows')
    if not 2<=max_requests<=50 or not 1<=max_seconds<=180:raise ValueError('batch budgets require 2..50 GETs and 1..180 seconds')
    sweeps=SweepStore(store._db);result={'errors':0,'requests':0,'full_source_baseline_complete':False,'stop_reason':'BATCH_LIMIT','page_size':page_size}
    with store.work_order_recovery_lock() as acquired:
        if not acquired:return {**result,'stop_reason':'SOURCE_BUSY'}
        run=sweeps.choose(reference['sha256'],identity=identity,new=new);identity=run.id
        if run.state=='PUBLISHED':return {**run.result,**sweeps.summary(identity),'requests':0,'stop_reason':'ALREADY_PUBLISHED'}
        result['version_advance_observations']=run.result.get('version_advance_observations',0)
        before=client.request_telemetry['business_requests'];start=monotonic()
        def available(count=1):
            return monotonic()-start<max_seconds and client.request_telemetry['business_requests']-before+count<=max_requests
        def upper_bound():
            rows=source_page(client,'siteid="BSR"',VERIFY_FIELDS,order='-assetid',size=1)
            if not rows:raise SweepGuard("UNEXPECTED_EMPTY_SOURCE_SCOPE")
            return validate_page(rows,lower=0,upper=2**63-1,size=1)[0][0]
        try:
            with client.bounded_requests(max_requests):
                if run.state=='INITIALIZING' and available():sweeps.initialize(identity,upper_bound())
                while available():
                    run=sweeps.get(identity)
                    if run.state in ('VERIFIED','PUBLISHED'):break
                    if run.rounds>3:raise SweepGuard('SOURCE_POPULATION_KEEPS_CHANGING')
                    changes=run.state=='CHANGES'
                    cursor=run.collect_cursor if run.state=='COLLECTING' else run.delta_cursor if changes else run.verify_cursor
                    where=f'siteid="BSR" and assetid>{cursor} and assetid<={run.upper_id}'
                    if changes:
                        begun=run.started_at
                        if begun.tzinfo is None:begun=begun.replace(tzinfo=timezone.utc)
                        floor=(begun-timedelta(minutes=5)).isoformat(timespec='seconds')
                        where=f'siteid="BSR" and assetid>{cursor} and changedate>="{floor}"'
                    rows=source_page(client,where,ASSET_DETAIL_FIELDS,size=page_size)
                    records=validate_page(rows,lower=cursor,upper=2**63-1 if changes else run.upper_id,size=page_size)
                    if run.state=='COLLECTING':
                        for _,payload,_ in records:equipment_from_payload(payload)
                        sweeps.save_collect_page(identity,cursor,records)
                    elif records:
                        # Refresh a changed or newly moved-into-BSR ID exactly. If a
                        # batch ends, verified cursor remains before this whole page.
                        ready=True; verified=[]
                        for assetid,payload,digest in records:
                            staged=sweeps.stage(identity,assetid)
                            if staged is not None and business_signature(staged.payload)==business_signature(payload):
                                if staged.signature!=digest:
                                    if not version_only_advanced(staged.payload,payload):
                                        raise SweepGuard('SOURCE_VERSION_REGRESSED_DURING_VERIFICATION')
                                    equipment_from_payload(payload)
                                    sweeps.refresh_stage(identity,assetid,payload,digest)
                                    result['version_advance_observations']+=1
                                verified.append((assetid,digest));continue
                            if not available():ready=False;break
                            full=source_page(client,f'siteid="BSR" and assetid={assetid}',ASSET_DETAIL_FIELDS,size=2)
                            actual=validate_page(full,lower=assetid-1,upper=assetid,size=2)
                            if len(actual)!=1:raise SweepGuard('SOURCE_CHANGED_DURING_VERIFICATION')
                            _,current,current_digest=actual[0];equipment_from_payload(current)
                            sweeps.refresh_stage(identity,assetid,current,current_digest)
                            if business_signature(current)!=business_signature(payload):
                                raise SweepGuard('SOURCE_CHANGED_DURING_VERIFICATION')
                            if current_digest!=digest:
                                if not version_only_advanced(payload,current):raise SweepGuard('SOURCE_CHANGED_DURING_VERIFICATION')
                                result['version_advance_observations']+=1
                            verified.append((assetid,current_digest))
                        if not ready:break
                        sweeps.save_verify_page(identity,cursor,verified,changes=changes)
                    else:
                        if changes:sweeps.finish_changes(identity,cursor)
                        else:
                            if not available():break
                            sweeps.finish_or_extend(identity,cursor,upper_bound())
        except Exception as error:
            result['errors']=1
            result['stop_reason']=str(error) if isinstance(error,SweepGuard) else ('RESPONSE_SIZE_CAP' if 'oversized body' in str(error) else type(error).__name__)
        result['requests']=client.request_telemetry['business_requests']-before
        sweeps.save_result(identity,result,requests=result['requests'])
        summary=sweeps.summary(identity)
        result.update(summary)
        if summary['state']=='VERIFIED' and not result['errors']:
            result['stop_reason']='SOURCE_EXHAUSTED_AND_VERIFIED'
            if publish:return {**publish_sweep(store,reference,sweeps,identity),**sweeps.summary(identity),'requests':result['requests']}
        return result
