"""Exact registered-cohort detail repair. No source requests or cursor writes.

Operational writes require separate owner approval, fresh backup/isolated restore
and durable private pre-commit checkpoints. This module is not a public endpoint.
"""
import copy
from src.canonical_identity import canonical_id
from src.adapters.maximo.actual_dates import version
from src.adapters.maximo.canonical_mappers import maintenance_event_from_payload
from src.repositories import models,mart_models
from src.services.local_mart_projector import _work_order_payload
from src.services.wo_actual_date_recovery import _locked_rows,_database_guard,_validate_plan,seal
from src.services.wo_actual_date_journal import slot,same
from src.services.mart import _next_update_time

PATHS=(('sources','maximo','wo_detail'),('sources','maximo','reportdate'),('sources','maximo','schedstart'),('sources','maximo','schedfinish'),('failure_code',))


def validate_plan(plan):
 if plan.get('format')!='wo-details-plan/1': raise ValueError('detail-specific plan required')
 _validate_plan({**plan,'format':'wo-actual-dates/1'})
 return plan


def plan_details(db,wonums):
 if not 1<=len(wonums)<=10 or len(set(wonums))!=len(wonums): raise ValueError('one to ten unique WOs required')
 items=[]
 with db.session() as s:
  for wonum in wonums:
   w=s.get(models.WorkOrderOrm,wonum);cid=canonical_id('maintenance_event','MXWODETAIL',wonum,'BSR','IP');m=s.get(mart_models.MaintenanceEventMartOrm,cid)
   if w is None or m is None or version(w.source_changed_at) is None or version(w.source_changed_at)!=version(m.source_changed_at): raise ValueError('exact equal source versions required; normal reconcile then replan')
   items.append({'wonum':wonum,'assetnum':w.equipment_id,'canonical_id':cid,'changedate':version(w.source_changed_at).isoformat()})
  plan={'format':'wo-details-plan/1','cohort':items};validate_plan(plan)
  for item in items:
   asset=canonical_id('asset','MXASSET',item['assetnum'],'BSR','IP');r=s.get(mart_models.ReliabilityAssetRegistryMartOrm,asset)
   if r is None or r.site_code!='BSR' or r.organization_code!='IP': raise ValueError('registered identity required')
 return plan


def snapshot(m): return {'sources':copy.deepcopy(m.sources),'failure_code':m.failure_code}


def put(document,path,value):
 node=document
 for key in path[:-1]:
  if node.get(key) is None: node[key]={}
  if not isinstance(node[key],dict): raise ValueError('detail container conflict')
  node=node[key]
 if value['present']: node[path[-1]]=copy.deepcopy(value['value'])
 else: node.pop(path[-1],None)


def signed(receipt):
 result=copy.deepcopy(receipt);result.pop('sha256',None);result['sha256']=seal(result);return result


def checkpoint(db,callback,receipt):
 if db.engine.dialect.name=='postgresql' and not callable(callback): raise ValueError('durable private checkpoint required')
 if callback: callback(signed(receipt))


def project_details(db,plan,*,approved_plan_sha256,expected_database,checkpoint_callback=None):
 validate_plan(plan)
 if seal(plan)!=approved_plan_sha256: raise ValueError('approved exact plan seal required')
 receipt={'format':'wo-detail-journal/1','state':'PREPARED','plan':copy.deepcopy(plan),'records':[]}
 with db.session() as s:
  _database_guard(s,db,expected_database)
  for item,w,m in _locked_rows(s,plan['cohort']):
   if version(w.source_changed_at)!=version(item['changedate']) or version(m.source_changed_at)!=version(item['changedate']): raise ValueError('detail source version conflict')
   before=snapshot(m);after=copy.deepcopy(before);record=maintenance_event_from_payload(_work_order_payload(w));source=record['sources']['maximo']
   for key in ('wo_detail','reportdate','schedstart','schedfinish'):
    # Existing independent non-null clocks are not silently replaced.
    current=slot(before,('sources','maximo',key))
    if key=='wo_detail' and current.get('value'):
     prior=current['value']
     if not isinstance(prior,dict) or prior.get('identity')!=source[key]['identity'] or version(prior.get('source_changed_at'))!=version(item['changedate']): raise ValueError('existing detail proof conflict')
     for name,previous in prior.get('fields',{}).items():
      incoming=source[key]['fields'].get(name,{})
      if (previous.get('value') is not None or previous.get('state')=='SOURCE_CONFIRMED_EMPTY' and previous.get('origin')=='MAXIMO_RESPONSE') and incoming.get('value')!=previous.get('value'): raise ValueError('conflicting retained field at equal source version')
    if key!='wo_detail' and current.get('value') is not None:
     if source.get(key) is not None and current['value']!=source[key] and (version(current['value']) is None or version(current['value'])!=version(source[key])): raise ValueError('existing retained detail clock conflict')
     continue
    put(after,('sources','maximo',key),{'present':True,'value':source[key]})
   if m.failure_code is None: after['failure_code']=record.get('failure_code')
   changes=[{'path':list(path),'before':slot(before,path),'after':slot(after,path)} for path in PATHS if not same(slot(before,path),slot(after,path))]
   if changes:
    m.sources=after['sources'];m.failure_code=after['failure_code'];m.mart_updated_at=_next_update_time(m.mart_updated_at)
   receipt['records'].append({'wonum':item['wonum'],'fields':changes,'containers':[{'path':list(path),'before':slot(before,path)} for path in (('sources',),('sources','maximo')) if not slot(before,path)['present'] or slot(before,path).get('value') is None]})
  s.flush();checkpoint(db,checkpoint_callback,receipt);s.commit()
 receipt['state']='APPLIED';return signed(receipt)


def rollback_details(db,receipt,*,expected_database,checkpoint_callback=None):
 if receipt.get('format')!='wo-detail-journal/1' or signed(receipt).get('sha256')!=receipt.get('sha256') or receipt.get('state') not in ('PREPARED','APPLIED','ROLLBACK_PREPARED','ROLLED_BACK'): raise ValueError('invalid detail journal')
 plan=validate_plan(receipt['plan']);entries={r['wonum']:r for r in receipt['records']}
 if len(entries)!=len(plan['cohort']) or set(entries)!={i['wonum'] for i in plan['cohort']}: raise ValueError('journal cohort mismatch')
 result=copy.deepcopy(receipt);pending=[];states=set()
 with db.session() as s:
  _database_guard(s,db,expected_database)
  for item,w,m in _locked_rows(s,plan['cohort']):
   if version(m.source_changed_at)!=version(item['changedate']) or version(w.source_changed_at)!=version(item['changedate']): raise ValueError('preserve newer source evidence')
   fields=entries[item['wonum']]['fields'];current=snapshot(m)
   if len({tuple(f['path']) for f in fields})!=len(fields) or any(tuple(f['path']) not in PATHS for f in fields): raise ValueError('journal write set invalid')
   is_before=all(same(slot(current,f['path']),f['before']) for f in fields)
   is_after=all(same(slot(current,f['path']),f['after']) for f in fields)
   rolled=receipt['state'] in ('ROLLBACK_PREPARED','ROLLED_BACK') and is_before
   if not (rolled or is_after) or receipt['state']=='ROLLED_BACK' and not rolled: raise ValueError('detail rollback conflict')
   if fields: states.add(rolled)
   if any(tuple(c['path']) not in (('sources',),('sources','maximo')) for c in entries[item['wonum']].get('containers',[])): raise ValueError('invalid container journal')
   if not rolled: pending.append((m,current,fields,entries[item['wonum']].get('containers',[])))
  if len(states)>1: raise ValueError('partial cohort conflict')
  if receipt['state']=='ROLLED_BACK': return result
  for m,current,fields,containers in pending:
   for f in fields: put(current,f['path'],f['before'])
   for c in reversed(containers):
    if slot(current,c['path']).get('value')=={}: put(current,c['path'],c['before'])
   if fields:
    m.sources=current['sources'];m.failure_code=current['failure_code'];m.mart_updated_at=_next_update_time(m.mart_updated_at)
  s.flush();result['state']='ROLLBACK_PREPARED';checkpoint(db,checkpoint_callback,result);s.commit()
 result['state']='ROLLED_BACK';return signed(result)
