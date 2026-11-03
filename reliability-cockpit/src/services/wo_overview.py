"""SQL-only unique-WO aggregates. Modification never substitutes execution."""
from datetime import datetime,timedelta,timezone
from sqlalchemy import select,func,and_,case
from src.repositories.mart_models import MaintenanceEventMart as M, ReliabilityAssetRegistryMart as R


def wo_overview(database, *, window_days=30, as_of=None):
 if window_days not in (7,30,90): raise ValueError('bounded window required')
 now=as_of or datetime.now(timezone.utc)
 if now.tzinfo is None: raise ValueError('aware as_of required')
 start=now-timedelta(days=window_days)
 scope=select(M).join(R,R.asset_ref==M.equipment_id).where(M.site_code=='BSR',M.organization_code=='IP',R.site_code=='BSR',R.organization_code=='IP').subquery()
 key=func.coalesce(scope.c.work_order_id,scope.c.canonical_id)
 count=lambda condition:func.count(func.distinct(key)).filter(condition)
 source=scope.c.sources['maximo']; detail=source['wo_detail']
 epoch=detail['fields']['reported_at']['epoch_seconds']
 numeric=(func.jsonb_typeof(epoch)=='number') if database.engine.dialect.name=='postgresql' else func.json_type(scope.c.sources,'$.maximo.wo_detail.fields.reported_at.epoch_seconds').in_(['integer','real'])
 reported=case((numeric,epoch.as_float()),else_=None)
 proof=source['actual_dates']
 identity=and_(proof['schema_version'].as_integer()==1,proof['identity']['wonum'].as_string()==source['wonum'].as_string(),proof['identity']['assetnum'].as_string()==source['assetnum'].as_string(),proof['identity']['siteid'].as_string()=='BSR',proof['identity']['orgid'].as_string()=='IP')
 valid_start=and_(scope.c.actual_start.is_not(None),identity,proof['fields']['actstart']['state'].as_string()=='VALID')
 valid_finish=and_(scope.c.actual_finish.is_not(None),identity,proof['fields']['actfinish']['state'].as_string()=='VALID')
 valid_report=and_(reported.is_not(None),detail['schema_version'].as_integer()==1,detail['identity']['wonum'].as_string()==source['wonum'].as_string(),detail['identity']['assetnum'].as_string()==source['assetnum'].as_string(),detail['identity']['siteid'].as_string()=='BSR',detail['identity']['orgid'].as_string()=='IP',detail['fields']['reported_at']['state'].as_string().in_(['SOURCE_VALUE','RETAINED_LEGACY_VALUE']))
 bases={'reported':(reported,valid_report,True),'actual_started':(scope.c.actual_start,valid_start,False),'actual_finished':(scope.c.actual_finish,valid_finish,False),'record_modified':(scope.c.source_changed_at,scope.c.source_changed_at.is_not(None),False)}
 def between(basis,a,b):
  col,valid,epoch=bases[basis]
  return and_(valid,col>=a.timestamp() if epoch else col>=a,col<b.timestamp() if epoch else col<b)
 week=now.astimezone(timezone(timedelta(hours=7))).replace(hour=0,minute=0,second=0,microsecond=0)
 week-=timedelta(days=week.weekday())
 weeks=[week-timedelta(weeks=n) for n in range(11,-1,-1)]
 expressions=[func.count(func.distinct(key)).label('total')]
 for basis,(_,valid,_) in bases.items():
  expressions.extend([count(between(basis,start,now+timedelta(microseconds=1))).label(basis),count(valid).label('coverage_'+basis)])
  expressions.extend(count(and_(between(basis,w,w+timedelta(weeks=1)),between(basis,w,now+timedelta(microseconds=1)))).label(basis+'_'+str(i)) for i,w in enumerate(weeks))
 with database.read_session() as session:
  values=session.execute(select(*expressions).select_from(scope)).one()._mapping
  status=func.coalesce(scope.c.status,'UNKNOWN')
  statuses=session.execute(select(status.label('value'),func.count(func.distinct(key)).label('count')).select_from(scope).group_by(status).order_by(status)).all()
 return {'population':{'site_code':'BSR','organization_code':'IP','registry_scope':'REGISTERED_BSR_IP','counting_key':'DISTINCT_WORK_ORDER_REF_OR_UNRESOLVED_CANONICAL_ID','wo_group':'SEMANTICS_UNVERIFIED','task_policy':'ALL_RETAINED_NO_INFERRED_EXCLUSION','work_type':'ALL_RETAINED'},
 'window_days':window_days,'counts':{k:int(values[k] or 0) for k in bases},
 'date_coverage':{'total_unique_wo':int(values['total'] or 0),**{k:int(values['coverage_'+k] or 0) for k in bases}},
 'weekly':[{'period_start':w.isoformat(),'period_end':(w+timedelta(weeks=1)).isoformat(),**{k:int(values[k+'_'+str(i)] or 0) for k in bases}} for i,w in enumerate(weeks)],
 'status_snapshot':[{'value':r.value,'count':int(r.count)} for r in statuses],
 'backlog':{'state':'DEFINITION_REQUIRES_APPROVAL','count':None},
 'freshness':{'state':'NOT_EXPOSED','source_collection_at':None,'explanation':'Query time and source changedate do not establish collection freshness.'}}
