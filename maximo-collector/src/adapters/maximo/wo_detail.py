"""Bounded non-personal WO evidence. Absence is never source-confirmed null."""
from datetime import datetime, timezone
import math
from src.adapters.maximo.actual_dates import clock, version

# domain key: (verified MXWODETAIL scalar, maximum text length)
FIELDS = {
 'description':('description',4000), 'status_description':('status_description',300),
 'work_class':('woclass',80), 'priority':('wopriority',80), 'priority_description':('wopriority_description',300),
 'location_id':('location',160), 'source_parent':('parent',160), 'source_task_reference':('pctaskid',160),
 'wo_group':('wogroup',160), 'is_task':('istask',0), 'has_children':('haschildren',0),
 'reported_at':('reportdate',128), 'status_changed_at':('statusdate',128),
 'scheduled_start':('schedstart',128), 'scheduled_finish':('schedfinish',128),
 'target_completion':('targcompdate',128), 'estimated_duration_hours':('estdur',0),
}
CLOCKS={'reported_at','status_changed_at','scheduled_start','scheduled_finish','target_completion'}
BOOLS={'is_task','has_children'}


def field(key, value, present, origin):
 original=value
 if key in BOOLS and isinstance(value,str) and value.strip().lower() in ('0','1','false','true'):
  value=value.strip().lower() in ('1','true')
 if key in BOOLS or key=='estimated_duration_hours':
  if value=='': value=None
 state='SOURCE_NOT_YET_VERIFIED' if not present else 'SOURCE_CONFIRMED_EMPTY' if value is None or value=='' else 'SOURCE_VALUE'
 if origin=='LEGACY_COLUMN': state='RETAINED_LEGACY_VALUE' if value is not None else 'SOURCE_NOT_YET_VERIFIED'
 valid = value is None or (isinstance(value,str) and len(value)<=FIELDS[key][1])
 if key=='priority' and isinstance(value,(float,int)) and not isinstance(value,bool): valid=math.isfinite(value)
 if key in BOOLS: valid=value is None or isinstance(value,bool)
 if key=='estimated_duration_hours': valid=value is None or isinstance(value,(float,int)) and not isinstance(value,bool) and math.isfinite(value) and value>=0
 if not valid: value=None;state='SOURCE_VALUE_INVALID'
 result={'value':value,'state':state,'origin':origin,'epoch_seconds':None}
 if key in BOOLS: result['original_value']=original if isinstance(original,(str,bool)) and (not isinstance(original,str) or len(original)<=16) else None
 if key in CLOCKS and value not in (None,''):
  parsed=clock(value)
  if parsed['state']=='VALID': result['epoch_seconds']=version(value).timestamp()
  else: result['state']='SOURCE_TIMESTAMP_INVALID'
 return result


def evidence(member, *, origin='MAXIMO_RESPONSE'):
 return {'schema_version':1,'identity':{k:member.get(k) for k in ('wonum','assetnum','siteid','orgid')},
         'source_changed_at':member.get('changedate'),
         'collected_at':datetime.now(timezone.utc).isoformat() if origin=='MAXIMO_RESPONSE' else None,
         'fields':{key:{**field(key,member.get(source),source in member,origin),'source_changed_at':member.get('changedate')} for key,(source,_) in FIELDS.items()}}


def projected(member):
 proof=member.get('collector_wo_detail')
 if not isinstance(proof,dict):
  result=evidence(member); result["collected_at"]=None; return result
 expected={k:member.get(k) for k in ('wonum','assetnum','siteid','orgid')}
 if proof.get('schema_version')!=1 or proof.get('identity')!=expected or version(proof.get('source_changed_at'))!=version(member.get('changedate')):
  raise ValueError('WO detail identity/version mismatch')
 result=evidence(member,origin='LEGACY_COLUMN')
 for key in FIELDS:
  previous=proof.get('fields',{}).get(key)
  if isinstance(previous,dict) and (previous.get('state')!='SOURCE_NOT_YET_VERIFIED' or result['fields'][key]['value'] is None):
   checked=field(key,previous.get('value'),previous.get('state')!='SOURCE_NOT_YET_VERIFIED',previous.get('origin'))
   # Do not promote redacted invalid input to a confirmed null.
   if previous.get('state') in ('SOURCE_VALUE_INVALID','SOURCE_TIMESTAMP_INVALID'):
    checked['state']=previous['state']
   if 'original_value' in previous: checked['original_value']=previous['original_value']
   checked['source_changed_at']=previous.get('source_changed_at')
   result['fields'][key]=checked
 result['collected_at']=proof.get('collected_at')
 return result


def merge_details(previous,incoming,existing,new_row):
 """Omitted/invalid source scalars cannot erase retained technical evidence."""
 import copy
 result=copy.deepcopy(incoming)
 if previous and previous.get('identity')!=incoming.get('identity'): raise ValueError('WO detail identity changed')
 old_fields=previous.get('fields',{}) if isinstance(previous,dict) else {}
 columns={k:k for k in FIELDS if hasattr(existing,k)}
 columns['source_task_reference']='parent_wo'
 old_version=version(existing.source_changed_at)
 new_version=version(new_row.get('source_changed_at'))
 for key,item in result['fields'].items():
  old=old_fields.get(key,{})
  attr=columns.get(key)
  if item['state'] in ('SOURCE_NOT_YET_VERIFIED','SOURCE_VALUE_INVALID','SOURCE_TIMESTAMP_INVALID'):
   if old.get('value') is not None:
    result['fields'][key]=copy.deepcopy(old)
   elif attr and getattr(existing,attr) is not None:
    value=getattr(existing,attr);value=value.isoformat() if isinstance(value,datetime) else value
    result['fields'][key]=field(key,value,True,'LEGACY_COLUMN')
    result['fields'][key]['source_changed_at']=old_version.isoformat() if old_version else None
   if attr and getattr(existing,attr) is not None:new_row[attr]=getattr(existing,attr)
  elif (old.get('value') is not None or old.get('state')=='SOURCE_CONFIRMED_EMPTY' and old.get('origin')=='MAXIMO_RESPONSE') and item.get('value')!=old.get('value'):
   previous_version=version(old.get('source_changed_at'))
   incoming_version=version(item.get('source_changed_at'))
   if previous_version is None or incoming_version is None or incoming_version<=previous_version:
    raise ValueError('conflicting WO detail without newer field evidence')
 return result
