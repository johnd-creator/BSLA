"""Disabled, exact-ID synthetic replay. No scheduler, DSN fallback or startup DDL.

One queue row per B2 family; append-only stage history. A targeted manifest can
never prove population coverage. Domain fencing excludes participating writers;
unfenced legacy writers remain an explicit rollout prohibition.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict, dataclass
from datetime import timedelta
import hashlib
import time
import uuid

from sqlalchemy import String, func, insert, inspect, select, text, tuple_, update
from sqlalchemy.orm import Session
from src.repositories import deferred_models as dm, projection_models as pm, replay_models as rm, models
from src.repositories.deferred_store import (DeferredProjectionStore, LedgerLimit, POLICY_EPOCH,
                                            classify, describe, family_identity)
from src.repositories.projection_store import (CaptureError, FencedOut, BudgetExceeded, EPOCH, SCOPE,
    Ticket, captured_payload, encode, fingerprint, source_query)
from src.services.asset_registry_reconciliation import normalize_identifier

REPLAY_EPOCH = 'replay-v1-exact-id'
SCOPE_KEY = 'BSR:IP:WO_BSR'
INVOCATION_DEADLINE = ContextVar('synthetic_replay_deadline', default=None)

@dataclass(frozen=True)
class ReplayPolicy:
    max_attempts: int = 3
    max_probes: int = 16
    max_events: int = 128
    base_backoff: int = 30
    max_backoff: int = 3600
    work: int = 1
    seconds: int = 20

    def __post_init__(self):
        values = asdict(self)
        if any(type(v) is not int for v in values.values()) or not (
            1 <= self.max_attempts <= 20 and 1 <= self.max_probes <= 64 and
            16 <= self.max_events <= 256 and 1 <= self.base_backoff <= self.max_backoff <= 86400
            and 1 <= self.work <= 5 and 1 <= self.seconds <= 30):
            raise ValueError('invalid finite replay policy')

    def delay(self, count):
        if type(count) is not int or not 1 <= count <= 64:
            raise ValueError('invalid backoff count')
        return min(self.max_backoff, self.base_backoff * 2**(count-1))


def targeted_scope(family):
    return dict(SCOPE, capture_mode='RECOVERY_BY_ID', family_id=family['id'],
                source_id=family['source_id'], policy_epoch=POLICY_EPOCH, replay_epoch=REPLAY_EPOCH)


class ReplayStore(DeferredProjectionStore):
    def __init__(self, db, *, replay_enabled=False, replay_policy=None, **kwargs):
        if replay_enabled is not True:
            raise CaptureError('synthetic replay capability disabled')
        self.replay_policy = replay_policy or ReplayPolicy()
        super().__init__(db, **kwargs)
        if not self.controlled_transitions:
            raise CaptureError('audited transition capability required')
        if self.replay_policy.max_attempts > self.ledger_limits.max_attempts:
            raise LedgerLimit('replay budget exceeds B2 attempt cap')
        self.policy_digest = hashlib.sha256(encode([asdict(self.replay_policy),
                                                    asdict(self.ledger_limits)])).hexdigest()
        self._replay_schema()

    @contextmanager
    def invocation(self):
        # Context-local: concurrent callers cannot extend each other's budget.
        deadline=time.monotonic()+self.replay_policy.seconds
        outer=INVOCATION_DEADLINE.get()
        token=INVOCATION_DEADLINE.set(min(outer,deadline) if outer is not None else deadline)
        try:
            yield INVOCATION_DEADLINE.get()
        finally:
            INVOCATION_DEADLINE.reset(token)

    @staticmethod
    def _remaining():
        deadline=INVOCATION_DEADLINE.get()
        if deadline is None: return None
        left=deadline-time.monotonic()
        if left<=0: raise BudgetExceeded('replay invocation time budget; stage retained')
        return left

    def _limits(self,s,seconds=None):
        left=self._remaining()
        seconds=self.budget.seconds if seconds is None else seconds
        super()._limits(s,min(seconds,left) if left is not None else seconds)

    def _not_expired(self,s,ticket):
        self._remaining()  # Refuse a late commit as well as new phase admission.
        super()._not_expired(s,ticket)

    def _replay_schema(self):
        # Exact signatures generated from reviewed 006, never repaired at startup.
        with self.db.session() as s:
            self._limits(s)
            inspector = inspect(s.connection())
            for table in rm.metadata.tables.values():
                actual = {c['name']:c for c in inspector.get_columns(table.name)}
                if set(actual) != set(table.c.keys()):
                    raise CaptureError('replay schema columns drift')
                for col in table.c:
                    if (str(actual[col.name]['type'].compile(dialect=self.db.engine.dialect)) !=
                        str(col.type.compile(dialect=self.db.engine.dialect)) or
                        actual[col.name]['nullable'] != col.nullable):
                        raise CaptureError('replay schema type drift')
            for name, signature in GUARDS.items():
                body=s.scalar(text('''SELECT prosrc FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
                    WHERE n.nspname=current_schema() AND proname=:name'''),{'name':name})
                if body is None or hashlib.sha256(body.encode()).hexdigest()!=signature:
                    raise CaptureError('replay guard body drift')
            triggers=set(tuple(r) for r in s.execute(text('''SELECT c.relname,t.tgname,t.tgtype,t.tgenabled,
                t.tgdeferrable,t.tginitdeferred,p.proname FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid
                JOIN pg_proc p ON p.oid=t.tgfoid WHERE c.relnamespace=current_schema()::regnamespace
                AND c.relname LIKE 'mart_replay_%' AND NOT t.tgisinternal''')))
            if triggers != TRIGGERS or self._replay_catalog(s) != CATALOG_SIGNATURE:
                raise CaptureError('replay index/constraint/trigger drift')

    @staticmethod
    def _replay_catalog(s):
        schema=s.scalar(text('SELECT current_schema()'))
        cons=s.execute(text("""SELECT r.relname,c.conname,c.contype,pg_get_constraintdef(c.oid)
            FROM pg_constraint c JOIN pg_class r ON r.oid=c.conrelid
            WHERE r.relnamespace=current_schema()::regnamespace AND r.relname LIKE 'mart_replay_%'
            AND c.contype<>'n' ORDER BY r.relname,c.conname""")).all()
        idx=s.execute(text("""SELECT tablename,indexname,indexdef FROM pg_indexes
            WHERE schemaname=current_schema() AND tablename LIKE 'mart_replay_%'
            ORDER BY tablename,indexname""")).all()
        def normalized(row):
            return [v.replace('"'+schema+'".','CAPTURE_SCHEMA.').replace(schema+'.','CAPTURE_SCHEMA.')
                    if isinstance(v,str) else v for v in row]
        return hashlib.sha256(encode([[normalized(r) for r in cons],[normalized(r) for r in idx]])).hexdigest()

    def _scope_compatible(self, scope):
        if scope == SCOPE:
            return True  # Full B1 capture remains available, never auto-queued.
        return (isinstance(scope,dict) and set(scope)==set(SCOPE)|{
            'capture_mode','family_id','source_id','policy_epoch','replay_epoch'} and
            all(scope[k]==v for k,v in SCOPE.items()) and scope['capture_mode']=='RECOVERY_BY_ID' and
            scope['policy_epoch']==POLICY_EPOCH and scope['replay_epoch']==REPLAY_EPOCH and
            isinstance(scope['family_id'],str) and len(scope['family_id'])==64 and
            isinstance(scope['source_id'],str) and 1<=len(scope['source_id'])<=60)

    def _family(self,s,family_id):
        f=s.execute(select(dm.family).where(dm.family.c.id==family_id)).mappings().one()
        if (f['id']!=family_identity(f['domain'],f['source_id']) or f['source_system']!='MAXIMO'
                or f['source_object']!={'asset_master':'MXASSET','maintenance_event':'MXWODETAIL'}[f['domain']]
                or f['policy_epoch']!=POLICY_EPOCH or f['mapper_epoch']!=EPOCH or f['scope_key']!=SCOPE_KEY):
            raise CaptureError('incompatible family policy/scope/mapper')
        return f

    def _queue(self,s,ticket,family_id=None):
        self._lock(s,ticket); self._policy(s)
        q=s.execute(select(rm.queue).where(rm.queue.c.family_id==family_id) if family_id else
                    select(rm.queue).where(rm.queue.c.run_id==ticket.run_id)).mappings().one()
        if (q['owner']!=ticket.owner or q['fence']!=ticket.fence or q['run_id']!=ticket.run_id
                or q['policy_digest']!=self.policy_digest):
            raise FencedOut('replay claim/policy ownership mismatch')
        f=self._family(s,q['family_id'])
        if f['current_id']!=q['obligation_id']:
            raise FencedOut('replay obligation superseded outside claim')
        run=s.execute(select(pm.run).where(pm.run.c.id==ticket.run_id)).mappings().one()
        if run['scope']!=targeted_scope(f) or run['domain']!=ticket.domain or run['epoch']!=EPOCH:
            raise FencedOut('targeted claim manifest mismatch')
        return dict(q), f

    def _change(self,s,ticket,q,phase,reason,**extra):
        revision=q['revision']+1
        if revision>self.replay_policy.max_events:
            raise LedgerLimit('replay audit budget; evidence retained')
        values=dict(q,phase=phase,reason=reason,revision=revision,owner=ticket.owner,fence=ticket.fence)
        values.update(extra)
        s.execute(update(rm.queue).where(rm.queue.c.family_id==q['family_id']).values(**{
            k:v for k,v in values.items() if k!='family_id'}))
        self._journal(s,values)
        return values

    @staticmethod
    def _journal(s,q):
        s.execute(insert(rm.event).values(id=str(uuid.uuid4()),at=func.clock_timestamp(),**{
            k:q[k] for k in ('family_id','obligation_id','revision','phase','reason','probes','attempts',
                            'run_id','owner','fence')}))

    def register(self,ticket,obligation_id):
        """Explicit exact-ID B2 enrollment. No existing-debt scan or auto-import."""
        with self.db.session() as s,s.begin():
            self._limits(s); self._lock(s,ticket); self._policy(s)
            v=s.execute(select(dm.version).where(dm.version.c.id==obligation_id)).mappings().one()
            f=self._family(s,v['family_id'])
            if f['domain']!=ticket.domain or f['current_id']!=obligation_id or v['state'] not in ('OPEN','ELIGIBLE_FOR_RETRY'):
                raise CaptureError('only current nonblocked debt may be enrolled')
            old=s.execute(select(rm.queue).where(rm.queue.c.family_id==f['id'])).mappings().one_or_none()
            if old:
                if old['obligation_id']!=obligation_id or old['policy_digest']!=self.policy_digest:
                    raise CaptureError('existing queue requires explicit policy reconciliation')
                return dict(old)
            q=dict(family_id=f['id'],obligation_id=obligation_id,domain=f['domain'],scope_key=SCOPE_KEY,
                policy_epoch=POLICY_EPOCH,replay_epoch=REPLAY_EPOCH,policy_digest=self.policy_digest,
                phase='PENDING',reason='REGISTERED',due_at=s.scalar(select(func.clock_timestamp())),
                probes=0,attempts=0,revision=1,run_id=None,owner=ticket.owner,fence=ticket.fence)
            s.execute(insert(rm.queue).values(**q)); self._journal(s,q)
            return q

    def _due_query(self,domain,limit,after=None):
        source_query(domain)
        if type(limit) is not int or not 1<=limit<=20:
            raise ValueError('invalid due page limit')
        q=select(rm.queue).join(dm.family,dm.family.c.id==rm.queue.c.family_id).join(
            dm.version,dm.version.c.id==rm.queue.c.obligation_id).where(
            rm.queue.c.domain==domain,rm.queue.c.scope_key==SCOPE_KEY,rm.queue.c.policy_epoch==POLICY_EPOCH,
            rm.queue.c.replay_epoch==REPLAY_EPOCH,rm.queue.c.policy_digest==self.policy_digest,
            text("mart_replay_queue.phase IN ('PENDING','CLAIMED','CAPTURED','WRITING','FAILED','PROJECTED')"),rm.queue.c.due_at<=func.statement_timestamp(),
            dm.family.c.current_id==rm.queue.c.obligation_id,dm.family.c.mapper_epoch==EPOCH,
            dm.version.c.state.in_(('OPEN','ELIGIBLE_FOR_RETRY','RESOLVED')))
        # RESOLVED is eligible only to finish the SAME committed claim after a crash.
        q=q.where((dm.version.c.state!='RESOLVED') | (rm.queue.c.run_id.is_not(None)))
        if after is not None:
            if (not isinstance(after,tuple) or len(after)!=2 or getattr(after[0],'tzinfo',None) is None
                    or not isinstance(after[1],str) or len(after[1])!=64):
                raise ValueError('invalid due continuation')
            q=q.where(tuple_(rm.queue.c.due_at,rm.queue.c.family_id)>after)
        return q.order_by(rm.queue.c.due_at,rm.queue.c.family_id).limit(limit)

    def due(self,domain,*,limit=10,after=None):
        query=self._due_query(domain,limit,after)
        with self.db.session() as s:
            self._limits(s); self._policy(s)
            return [dict(r) for r in s.execute(query).mappings()]

    def claim_due(self,domain):
        """Domain-first lock, due row + new fenced manifest in ONE transaction."""
        query=self._due_query(domain,1)
        with self.db.session() as s,s.begin():
            self._limits(s); self._policy(s)
            d=s.execute(select(pm.lease).where(pm.lease.c.domain==domain).with_for_update()).mappings().one_or_none()
            now=s.scalar(select(func.clock_timestamp()))
            if d is None or d['lease_until']>now: return None
            q=s.execute(query.with_for_update(of=rm.queue)).mappings().one_or_none()
            if q is None: return None
            q=dict(q); f=self._family(s,q['family_id'])
            if q['revision']+8>self.replay_policy.max_events:
                # Fail closed without touching target; no unrecorded budget increase.
                raise LedgerLimit('insufficient replay stage audit capacity')
            run_id=q['run_id'] or str(uuid.uuid4())
            if q['run_id']:
                if d['latest_run']!=run_id:
                    raise FencedOut('unfinished replay was overtaken; manual reconciliation required')
                run=s.execute(select(pm.run).where(pm.run.c.id==run_id)).mappings().one()
                if run['scope']!=targeted_scope(f) or run['epoch']!=EPOCH:
                    raise FencedOut('resume manifest identity mismatch')
            else:
                s.execute(insert(pm.run).values(id=run_id,manifest_id=str(uuid.uuid4()),domain=domain,epoch=EPOCH,
                    scope=targeted_scope(f),sealed=False,item_count=0,byte_count=0,continuation=0,
                    status='CAPTURING',started_at=now))
            ticket=Ticket(run_id,domain,str(uuid.uuid4()),d['fence']+1)
            until=now+timedelta(seconds=self.budget.lease_seconds)
            s.execute(update(pm.lease).where(pm.lease.c.domain==domain).values(owner=ticket.owner,
                fence=ticket.fence,lease_until=until,latest_run=run_id))
            self._change(s,ticket,q,q['phase'] if q['run_id'] else 'CLAIMED',
                         'RESUMED' if q['run_id'] else 'CLAIMED',run_id=run_id,due_at=until)
            self._not_expired(s,ticket)
            return ticket

    def _source(self,s,domain,source_id,*,lock=False):
        model=models.EquipmentOrm if domain=='asset_master' else models.WorkOrderOrm
        query=source_query(domain).where(model.id==source_id).limit(1)
        if lock: query=query.with_for_update(read=True,of=model)
        row=s.execute(query).mappings().one_or_none()
        if row is None: return None
        payload=captured_payload(domain,row)
        if domain=='maintenance_event' and payload.get('local_equipment_present'):
            equipment=normalize_identifier(payload.get('equipment_id'))
            eq=select(models.EquipmentOrm.id).where(models.EquipmentOrm.id==equipment).limit(2)
            if lock: eq=eq.with_for_update(read=True)
            matches=s.scalars(eq).all()
            if len(matches)!=1:
                raise CaptureError('ambiguous exact normalized Equipment dependency')
        return payload

    def _readiness(self,s,f):
        v=s.execute(select(dm.version).where(dm.version.c.id==f['current_id'])).mappings().one()
        deps=s.execute(select(dm.dependency).where(dm.dependency.c.obligation_id==v['id'])
                       .limit(self.ledger_limits.max_dependencies+1)).mappings().all()
        if not deps or len(deps)>self.ledger_limits.max_dependencies:
            return 'BLOCKED','INVALID_MAPPING',None
        old=s.execute(select(pm.item).where(pm.item.c.run_id==v['first_run'],
                     pm.item.c.ordinal==v['first_ordinal'])).mappings().one()
        _,expected=describe(f['domain'],f['source_id'],old['payload'],
                           old['disposition'],old['reason'],old['target_id'])
        if {(d['kind'],d['scoped_key']) for d in deps}!=set(expected):
            return 'BLOCKED','INVALID_MAPPING',None
        payload=self._source(s,f['domain'],f['source_id'])
        if payload is None: return 'UNKNOWN','SOURCE_ABSENT',None
        record,disposition,reason=classify(f['domain'],f['source_id'],payload)
        if record is not None or disposition=='EXPECTED_EXCLUSION': return 'READY',None,payload
        if reason=='MISSING_LOCAL_EQUIPMENT' or reason=='MISSING_REQUIRED_ID': return 'NOT_READY','NOT_READY',payload
        if reason=='UNPROVEN_SCOPE': return 'UNKNOWN','UNKNOWN',payload
        return 'BLOCKED','INVALID_MAPPING',payload

    def readiness(self,ticket):
        with self.db.session() as s:
            self._limits(s); q,f=self._queue(s,ticket)
            state,reason,_=self._readiness(s,f)
            return dict(state=state,reason=reason)

    def capture_claim(self,ticket):
        """One exact source identity in a short consistent snapshot; zero full scan."""
        started=time.monotonic()
        with self.db.engine.connect().execution_options(isolation_level='REPEATABLE READ') as conn:
            with Session(bind=conn) as s,s.begin():
                self._limits(s,self.replay_policy.seconds); q,f=self._queue(s,ticket)
                run=s.execute(select(pm.run).where(pm.run.c.id==ticket.run_id)).mappings().one()
                if q['phase']!='CLAIMED': return dict(state=q['phase'])
                state,reason,payload=self._readiness(s,f)
                if state!='READY':
                    probes=q['probes']+1
                    blocked=state=='BLOCKED' or reason=='SOURCE_ABSENT' or probes>=self.replay_policy.max_probes
                    self._change(s,ticket,q,'BLOCKED' if blocked else 'PENDING',
                        'PROBE_LIMIT' if probes>=self.replay_policy.max_probes else reason,probes=probes,
                        run_id=None if not blocked else ticket.run_id,
                        due_at=func.clock_timestamp()+timedelta(seconds=self.replay_policy.delay(probes)))
                    s.execute(update(pm.run).where(pm.run.c.id==ticket.run_id).values(status='FAILED'))
                    self._not_expired(s,ticket)
                    return dict(state=state,reason=reason)
                size=len(encode([f['source_id'],payload]))
                if size>self.budget.bytes: raise BudgetExceeded('targeted capture byte budget')
                fp=fingerprint(ticket.domain,f['source_id'],payload)
                digest=hashlib.sha256(encode([1,f['source_id'],fp])).hexdigest()
                s.execute(insert(pm.item).values(run_id=ticket.run_id,ordinal=1,source_id=f['source_id'],
                                                fingerprint=fp,payload=payload))
                s.execute(update(pm.run).where(pm.run.c.id==ticket.run_id).values(sealed=True,item_count=1,
                    byte_count=size,manifest_digest=digest,snapshot=s.scalar(select(func.pg_current_snapshot().cast(String))),
                    status='SEALED'))
                self._change(s,ticket,q,'CAPTURED','CAPTURED')
                self._not_expired(s,ticket)
                if time.monotonic()-started>min(self.budget.seconds,self.replay_policy.seconds):
                    raise BudgetExceeded('targeted capture time budget')
                return dict(state='READY',run_id=ticket.run_id)

    def reserve_attempt(self,ticket):
        with self.db.session() as s,s.begin():
            self._limits(s); q,f=self._queue(s,ticket)
            if q['phase']=='WRITING': return True  # Reconcile ambiguous ack, same logical reservation.
            if q['phase'] not in ('CAPTURED','FAILED'): raise CaptureError('invalid attempt phase')
            v=s.execute(select(dm.version).where(dm.version.c.id==f['current_id'])).mappings().one()
            row=s.execute(select(pm.item).where(pm.item.c.run_id==ticket.run_id)).mappings().one()
            fresh=v['fingerprint']!=row['fingerprint']
            needed=(1 if fresh or v['state']=='ELIGIBLE_FOR_RETRY' else 2)+1
            exhausted=(q['attempts']>=self.replay_policy.max_attempts or
                (not fresh and (v['attempts']+1>=self.ledger_limits.max_attempts or
                               v['revision']+needed>self.ledger_limits.max_transitions)) or
                (fresh and (v['revision']+1>self.ledger_limits.max_transitions or
                            v['version']>=self.ledger_limits.max_versions or self.ledger_limits.transition_batch<2)))
            if exhausted:
                self._change(s,ticket,q,'BLOCKED','ATTEMPT_LIMIT' if q['attempts']>=self.replay_policy.max_attempts else 'HISTORY_LIMIT')
                return False
            self._change(s,ticket,q,'WRITING','ATTEMPT',attempts=q['attempts']+1)
            self._not_expired(s,ticket)
            return True

    def _before_item(self,s,ticket,row):
        run=s.execute(select(pm.run.c.scope).where(pm.run.c.id==ticket.run_id)).scalar_one()
        if run==SCOPE: return
        q,f=self._queue(s,ticket)
        if q['phase']!='WRITING': raise CaptureError('actual attempt reservation required')
        payload=self._source(s,ticket.domain,f['source_id'],lock=True)
        if payload is None or fingerprint(ticket.domain,f['source_id'],payload)!=row['fingerprint']:
            raise FencedOut('source/dependency changed after sealed capture; reviewed reconciliation required')

    def _on_receipt(self,s,ticket,row,disposition,reason,target_id,target_digest):
        scope=s.scalar(select(pm.run.c.scope).where(pm.run.c.id==ticket.run_id))
        if scope==SCOPE:
            return super()._on_receipt(s,ticket,row,disposition,reason,target_id,target_digest)
        q,f=self._queue(s,ticket)
        super()._on_receipt(s,ticket,row,disposition,reason,target_id,target_digest)
        current=s.scalar(select(dm.family.c.current_id).where(dm.family.c.id==f['id']))
        self._change(s,ticket,q,'PROJECTED','PROJECTED',obligation_id=current)

    def _proof(self,s,ticket,family,version,reference,**kwargs):
        scope=s.scalar(select(pm.run.c.scope).where(pm.run.c.id==ticket.run_id))
        if scope!=SCOPE:
            q,f=self._queue(s,ticket)
            if q['phase']!='PROJECTED' or family['id']!=f['id']:
                raise CaptureError('committed recovery phase required')
        return super()._proof(s,ticket,family,version,reference,**kwargs)

    def _coverage_incomplete(self,s,ticket):
        scope=s.scalar(select(pm.run.c.scope).where(pm.run.c.id==ticket.run_id))
        return True if scope!=SCOPE else super()._coverage_incomplete(s,ticket)

    def phase(self,ticket):
        with self.db.session() as s:
            self._limits(s); q,_=self._queue(s,ticket)
            return q

    def write_failed(self,ticket):
        with self.db.session() as s,s.begin():
            self._limits(s); q,_=self._queue(s,ticket)
            if q['phase']!='WRITING': raise CaptureError('failure is not an uncommitted write')
            blocked=q['attempts']>=self.replay_policy.max_attempts
            self._change(s,ticket,q,'BLOCKED' if blocked else 'FAILED',
                'ATTEMPT_LIMIT' if blocked else 'WRITE_FAILED',due_at=func.clock_timestamp()+
                    timedelta(seconds=self.replay_policy.delay(q['attempts'])))

    def resolve_claim(self,ticket,*,after_transition=None):
        q=self.phase(ticket)
        if q['phase']!='PROJECTED': raise CaptureError('committed receipt required')
        with self.db.session() as s:
            v=dict(s.execute(select(dm.version).where(dm.version.c.id==q['obligation_id'])).mappings().one())
        for action in ('ELIGIBLE','RESOLVED'):
            if (action=='ELIGIBLE' and v['state']=='OPEN') or (action=='RESOLVED' and v['state']!='RESOLVED'):
                key=str(uuid.uuid5(uuid.UUID(ticket.run_id),action))
                v=self.transition(ticket,v['id'],v['revision'],action,(ticket.run_id,1),key)
                if after_transition: after_transition(action)
        with self.db.session() as s,s.begin():
            self._limits(s); q,f=self._queue(s,ticket)
            v=s.execute(select(dm.version).where(dm.version.c.id==f['current_id'])).mappings().one()
            self._proof(s,ticket,f,v,(ticket.run_id,1),resolved=True)
            if v['state']!='RESOLVED': raise CaptureError('resolution not committed')
            self._change(s,ticket,q,'DONE','RESOLVED')
            self._not_expired(s,ticket)
        return dict(state='DONE',run_id=ticket.run_id)

# Generated from additive 006. Filled by schema qualification, not startup repair.
GUARDS = {'mart_replay_queue_guard': '8e88a8e21e5e277da6ec695337eecdab90f2ebd3fcee6d0a119690d8a8a1a7a7', 'mart_replay_audit_guard': 'a08bc45caf450d7d91b4cc7b5e441a10c6f5324f886ba1dc7eee355cd0eb1ded'}
TRIGGERS = {
 ('mart_replay_queue','replay_queue_guard',31,'O',False,False,'mart_replay_queue_guard'),
 ('mart_replay_queue','replay_queue_no_truncate',34,'O',False,False,'mart_replay_queue_guard'),
 ('mart_replay_queue','replay_audit_guard',21,'O',True,True,'mart_replay_audit_guard'),
 ('mart_replay_event','replay_event_immutable',27,'O',False,False,'mart_deferred_append_only'),
 ('mart_replay_event','replay_event_no_truncate',34,'O',False,False,'mart_deferred_append_only'),
}
CATALOG_SIGNATURE = 'f3471fb5a23314bf9e004fa1f006cefa304d335a80e73df4efc32b998c108bfc'
