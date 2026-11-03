"""Allowlisted Mart-only WO detail. Never joins Collector or calls a source."""
from datetime import datetime, timezone
import math

FIELDS={'description':4000,'status_description':300,'work_class':80,'priority':80,'priority_description':300,
 'location_id':160,'source_parent':160,'source_task_reference':160,'wo_group':160,
 'is_task':0,'has_children':0,'reported_at':128,'status_changed_at':128,'scheduled_start':128,
 'scheduled_finish':128,'target_completion':128,'estimated_duration_hours':0}
STATES={'SOURCE_VALUE','RETAINED_LEGACY_VALUE','SOURCE_CONFIRMED_EMPTY','SOURCE_NOT_YET_VERIFIED',
        'SOURCE_VALUE_INVALID','SOURCE_TIMESTAMP_INVALID'}

def instant(value):
 try:
  result=datetime.fromisoformat(str(value).replace('Z','+00:00'))
  return result.astimezone(timezone.utc) if result.tzinfo and not str(value).endswith('-00:00') else None
 except (ValueError,TypeError): return None


def row_version(value):
 # ORM source metadata is UTC-normalized on write; SQLite loses its tz flag.
 if isinstance(value,datetime) and value.tzinfo is None: value=value.replace(tzinfo=timezone.utc)
 return instant(value)


def detail_view(row):
 root=row.sources if isinstance(row.sources,dict) else {}
 source=root.get('maximo',{})
 if not isinstance(source,dict): source={}
 proof=source.get('wo_detail',{})
 fields={}
 collected=None
 identity={'wonum':source.get('wonum'),'assetnum':source.get('assetnum'),'siteid':row.site_code,'orgid':row.organization_code}
 if (isinstance(proof,dict) and proof.get('schema_version')==1 and proof.get('identity')==identity
     and instant(proof.get('source_changed_at')) is not None
     and instant(proof.get('source_changed_at'))==row_version(row.source_changed_at)):
  collected=instant(proof.get("collected_at"))
  proof_fields=proof.get('fields',{})
  if not isinstance(proof_fields,dict): proof_fields={}
  for key,cap in FIELDS.items():
   item=proof_fields.get(key)
   if not isinstance(item,dict) or item.get('state') not in STATES or item.get('origin') not in ('MAXIMO_RESPONSE','LEGACY_COLUMN'): continue
   if item['state']=='SOURCE_CONFIRMED_EMPTY' and (item.get('origin')!='MAXIMO_RESPONSE' or item.get('value') not in (None,'')): continue
   value=item.get('value'); valid=value is None or isinstance(value,str) and len(value)<=cap
   if key=='priority' and isinstance(value,(float,int)) and not isinstance(value,bool): valid=math.isfinite(value)
   if key in ('is_task','has_children'): valid=value is None or isinstance(value,bool)
   if key=='estimated_duration_hours': valid=value is None or isinstance(value,(float,int)) and not isinstance(value,bool) and math.isfinite(value) and value>=0
   if valid:
    observed=instant(item.get('source_changed_at'));current=row_version(row.source_changed_at)
    fields[key]={'value':value,'state':item['state'],'origin':item['origin'],'source_changed_at':observed.isoformat() if observed and current and observed<=current else None}
 # Presence/state never derives from a WO status.
 clocks=source.get('actual_dates',{})
 clock_fields=clocks.get('fields',{}) if isinstance(clocks,dict) and clocks.get('schema_version')==1 and clocks.get('identity')==identity and identity['wonum'] and identity['assetnum'] else {}
 if not isinstance(clock_fields,dict): clock_fields={}
 verified={}
 for key,item in clock_fields.items():
  if not isinstance(item,dict): continue
  observed=instant(item.get('source_changed_at'));current=row_version(row.source_changed_at)
  if observed is None or current is None or observed>current: continue
  state=item.get('state');original=item.get('original');normalized=item.get('normalized')
  if state=='VALID' and instant(original) is not None and instant(original)==instant(normalized): verified[key]=item
  elif state=='MISSING' and original in (None,'') and normalized is None: verified[key]=item
  elif state in ('INVALID','NAIVE') and normalized is None: verified[key]=item
 clock_fields=verified
 states=[clock_fields.get(k,{}).get('state') for k in ('actstart','actfinish')]
 start,finish=row.actual_start is not None,row.actual_finish is not None
 if any(s in ('INVALID','NAIVE') for s in states): state='SOURCE_TIMESTAMP_INVALID'
 elif any(clock_fields.get(k,{}).get('state')=='VALID' and not present for k,present in (('actstart',start),('actfinish',finish))): state='COLLECTOR_PROJECTION_GAP'
 elif start and finish: state='ACTUAL_DATES_AVAILABLE'
 elif start: state='START_ONLY'
 elif finish: state='FINISH_ONLY'
 elif all(s=='MISSING' for s in states) and all(instant(clock_fields[k].get('source_changed_at'))==row_version(row.source_changed_at) and row_version(row.source_changed_at) is not None for k in ('actstart','actfinish')): state='SOURCE_CONFIRMED_EMPTY'
 else: state='SOURCE_NOT_YET_VERIFIED'
 return fields,state,collected
