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
 from src.services.wo_evidence_sql import WoProofSql,EVIDENCE_ROOTS
 proof=WoProofSql(database,scope)
 if proof.postgres:
  # Wide source JSON is commonly TOASTed after detail recovery. Extract the
  # ten bounded proof roots once per scoped row before repeated predicates;
  # the complete source document never enters the aggregate CTE.
  columns=('work_order_id','canonical_id','status','source_changed_at','actual_start','actual_finish')
  projected=select(*(scope.c[name] for name in columns),
   *(proof.json(*path).label('proof_'+str(i)) for i,path in enumerate(EVIDENCE_ROOTS))).select_from(scope).cte('scoped_wo_proofs').prefix_with('MATERIALIZED')
  scope=projected;key=func.coalesce(scope.c.work_order_id,scope.c.canonical_id)
  proof=WoProofSql(database,scope,{path:scope.c['proof_'+str(i)] for i,path in enumerate(EVIDENCE_ROOTS)})
 reported,valid_report=proof.reported()
 valid_start=proof.valid_actual('actstart',scope.c.actual_start)
 valid_finish=proof.valid_actual('actfinish',scope.c.actual_finish)
 # Evaluate each evidence proof once per registered row, rather than repeating
 # timestamp parsing in every weekly/window FILTER. This remains SELECT-only.
 evaluated=select(key.label('wo_key'),scope.c.status.label('status'),
  case((valid_report,reported),else_=None).label('reported'),
  case((valid_start,scope.c.actual_start),else_=None).label('actual_started'),
  case((valid_finish,scope.c.actual_finish),else_=None).label('actual_finished'),
  scope.c.source_changed_at.label('record_modified')).select_from(scope).cte('verified_wo_basis').prefix_with('MATERIALIZED')
 scope=evaluated;key=scope.c.wo_key
 bases={name:(scope.c[name],scope.c[name].is_not(None),name=='reported') for name in ('reported','actual_started','actual_finished','record_modified')}
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
