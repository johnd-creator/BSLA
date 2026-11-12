"""Disabled B2 debt foundation. No replay scanner, CLI, watcher or startup DDL.

Controlled transitions require a separate explicit opt-in and current B1 ticket.
This is a repository capability for synthetic qualification, not a public API or
an operational authorization service. Legacy writers remain restricted.
"""
from dataclasses import dataclass
from datetime import datetime
import hashlib
import uuid

from sqlalchemy import exists, func, insert, inspect, select, text, update, or_
from src.canonical_identity import canonical_id, scoped_reference
from src.repositories import deferred_models as dm, projection_models as pm
from src.repositories.projection_store import (CaptureError, FencedOut, EPOCH, SCOPE,
    TERMINAL, ProjectionStore, encode, map_input)
from src.services.asset_registry_reconciliation import normalize_identifier

POLICY_EPOCH = 'deferred-v1-BSR-IP-WO-BSR'
ACTIVE = ('OPEN','ELIGIBLE_FOR_RETRY','BLOCKED_NEEDS_REVIEW')

class LedgerLimit(CaptureError):
    pass

class TransitionRejected(CaptureError):
    pass

@dataclass(frozen=True)
class LedgerLimits:
    obligations_per_transaction: int = 1
    transition_batch: int = 2
    max_attempts: int = 5
    max_transitions: int = 16
    max_dependencies: int = 4
    max_versions: int = 16
    coverage_proofs: int = 1000
    policy_expires_at: datetime | None = None

    def __post_init__(self):
        # One source identity; at most supersession + observation, or one controlled transition.
        counts = (self.obligations_per_transaction,self.transition_batch,self.max_attempts,
                  self.max_transitions,self.max_dependencies,self.max_versions,self.coverage_proofs)
        if any(type(value) is not int for value in counts):
            raise ValueError('ledger resource limits must be integers')
        if not (self.obligations_per_transaction == 1 and 1 <= self.transition_batch <= 2
                and 1 <= self.max_attempts <= 20 and 4 <= self.max_transitions <= 64
                and 1 <= self.max_dependencies <= 8 and 1 <= self.coverage_proofs <= 10000
                and 1 <= self.max_versions <= 128):
            raise ValueError('invalid ledger limits')
        if self.policy_expires_at is not None and self.policy_expires_at.tzinfo is None:
            raise ValueError('retention policy time must be aware')


def family_identity(domain, source_id):
    obj = {'asset_master':'MXASSET','maintenance_event':'MXWODETAIL'}.get(domain)
    if obj is None or not isinstance(source_id,str) or not 1 <= len(source_id) <= 60:
        raise CaptureError('invalid obligation identity')
    return hashlib.sha256(encode(['obligation-v1',domain,'MAXIMO',obj,source_id,
                                 'BSR:IP:WO_BSR',POLICY_EPOCH,EPOCH])).hexdigest()


def classify(domain, source_id, payload):
    """Safe missing ID can be corrected; other mapper errors require review.

    No writer/SQL exception is caught here or downgraded into ordinary deferral.
    """
    try:
        return map_input(domain,source_id,payload)
    except ValueError:
        if domain == 'asset_master' and not payload.get('assetnum'):
            return None,'DEFERRED','MISSING_REQUIRED_ID'
        return None,'FAILED','INVALID_MAPPING'


def describe(domain, source_id, payload, disposition, reason, target_id=None):
    if domain == 'asset_master':
        proven = payload.get('siteid') == 'BSR' and payload.get('orgid') == 'IP'
        asset = normalize_identifier(payload.get('assetnum'))
        target_id = target_id or (canonical_id('asset','MXASSET',payload['assetnum'],'BSR','IP')
                                  if proven and asset else None)
    else:
        proven = source_id.startswith('BSR')  # Existing scoped Collector/prefix contract.
        target_id = target_id or (canonical_id('maintenance_event','MXWODETAIL',source_id,'BSR','IP')
                                  if proven else None)
    mapping = {
        'MISSING_LOCAL_EQUIPMENT':('DEFERRED_DEPENDENCY','LOCAL_EQUIPMENT'),
        'UNPROVEN_SCOPE':('DEFERRED_SCOPE_PROOF','SCOPE_PROOF'),
        'MISSING_REQUIRED_ID':('DEFERRED_MAPPING','MAPPING_INPUT'),
        'INVALID_MAPPING':('FAILED_MAPPING','MAPPING_INPUT'),
        None:('RESOLUTION_PENDING','RECEIPT_RECONCILIATION'),
        'APPROVED_WO_PREFIX':('RESOLUTION_PENDING','RECEIPT_RECONCILIATION'),
    }
    if reason not in mapping:
        raise TransitionRejected('unreviewed disposition reason')
    classification, kind = mapping[reason]
    if kind == 'LOCAL_EQUIPMENT':
        equipment = normalize_identifier(payload.get('equipment_id'))
        key = scoped_reference('asset','MXASSET',equipment,'BSR','IP') if equipment else None
        key = key or f'MXWODETAIL:{source_id}:missing-equipment-id'
    else:
        key = f'MAXIMO:{domain}:{source_id}:{kind}'
    if len(key) > 240:
        raise LedgerLimit('dependency key budget')
    return dict(scope_proof='PROVEN' if proven else 'UNKNOWN',site='BSR' if proven else None,
        organization='IP' if proven else None,canonical_id=target_id,classification=classification,
        reason=reason if reason not in (None,'APPROVED_WO_PREFIX') else 'RECEIPT_RECONCILIATION'), [(kind,key)]


class DeferredProjectionStore(ProjectionStore):
    def __init__(self, db, *, controlled_transitions=False, ledger_limits=None, **kwargs):
        super().__init__(db,**kwargs)  # Disabled by default; B1 schema is required first.
        self.ledger_limits = ledger_limits or LedgerLimits()
        self.controlled_transitions = controlled_transitions
        self._ledger_schema()

    def _ledger_schema(self):
        # Versioned 005 capability, including indexes/constraints, not table-existence alone.
        with self.db.session() as s:
            self._limits(s)
            inspector = inspect(s.connection())
            for table in dm.metadata.tables.values():
                columns = {c['name']:c for c in inspector.get_columns(table.name)}
                if set(columns) != set(table.c.keys()):
                    raise CaptureError('deferred schema columns missing or drifted')
                for col in table.c:
                    if (str(columns[col.name]['type'].compile(dialect=self.db.engine.dialect)) !=
                        str(col.type.compile(dialect=self.db.engine.dialect)) or
                        columns[col.name]['nullable'] != col.nullable):
                        raise CaptureError('deferred schema type drift')
                if inspector.get_pk_constraint(table.name)['constrained_columns'] != [c.name for c in table.primary_key]:
                    raise CaptureError('deferred primary key drift')
            actual = set(s.scalars(text("""SELECT conname FROM pg_constraint
                WHERE connamespace=current_schema()::regnamespace AND conname LIKE 'deferred_%'""")))
            required = {'deferred_source','deferred_identity','deferred_version_identity','deferred_input',
                'deferred_scope','deferred_state','deferred_class','deferred_reason','deferred_counts',
                'deferred_closed_proof','deferred_current','deferred_dependency_kind','deferred_event_key',
                'deferred_event_revision','deferred_event_input','deferred_event_action','deferred_event_reason',
                'deferred_last_event','deferred_resolution_event','deferred_occurrence_input','deferred_audit_guard'}
            if not required <= actual:
                raise CaptureError('deferred constraints missing')
            index_specs = {'mart_deferred_version':{'deferred_one_active':['family_id'],
                            'deferred_family_state':['family_id','state']},
                'mart_deferred_dependency':{'deferred_dependency_lookup':['kind','scoped_key','obligation_id']},
                'mart_deferred_occurrence':{'deferred_occurrence_version':['obligation_id']}}
            for table, specs in index_specs.items():
                indexes = {i['name']:i for i in inspector.get_indexes(table)}
                for name, columns in specs.items():
                    if name not in indexes or indexes[name]['column_names'] != columns:
                        raise CaptureError('deferred dependency/index capability missing')
                    if name == 'deferred_one_active' and (not indexes[name]['unique'] or
                            'postgresql_where' not in indexes[name].get('dialect_options',{})):
                        raise CaptureError('deferred active uniqueness drift')
            # Exact reviewed function bodies and attachment/flags, generated from 005.
            for name, signature in GUARDS.items():
                body = s.scalar(text('''SELECT prosrc FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
                    WHERE n.nspname=current_schema() AND proname=:name'''), {'name':name})
                if body is None or hashlib.sha256(body.encode()).hexdigest() != signature:
                    raise CaptureError('deferred guard body drift')
            triggers = s.execute(text('''SELECT c.relname,t.tgname,t.tgtype,t.tgenabled,
                t.tgdeferrable,t.tginitdeferred,p.proname FROM pg_trigger t
                JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_proc p ON p.oid=t.tgfoid
                WHERE c.relnamespace=current_schema()::regnamespace AND NOT t.tgisinternal''')).all()
            if not REQUIRED_TRIGGERS <= set(tuple(t) for t in triggers):
                raise CaptureError('deferred trigger capability drift')
            signature = self._catalog_signature(s)
            if signature != CATALOG_SIGNATURE:
                raise CaptureError('deferred constraint/index definition drift')

    @staticmethod
    def _catalog_signature(s):
        schema = s.scalar(text('SELECT current_schema()'))
        constraints = s.execute(text("""SELECT r.relname,c.conname,c.contype,pg_get_constraintdef(c.oid)
            FROM pg_constraint c JOIN pg_class r ON r.oid=c.conrelid
            WHERE r.relnamespace=current_schema()::regnamespace
            AND r.relname LIKE 'mart_deferred_%' AND c.contype<>'n'
            ORDER BY r.relname,c.conname""")).all()
        indexes = s.execute(text("""SELECT tablename,indexname,indexdef FROM pg_indexes
            WHERE schemaname=current_schema() AND tablename LIKE 'mart_deferred_%'
            ORDER BY tablename,indexname""")).all()
        def normalize(row):
            return [v.replace('"'+schema+'".','CAPTURE_SCHEMA.').replace(schema+'.','CAPTURE_SCHEMA.')
                    if isinstance(v,str) else v for v in row]
        return hashlib.sha256(encode([[normalize(r) for r in constraints],
                                      [normalize(r) for r in indexes]])).hexdigest()

    def _policy(self,s):
        until = self.ledger_limits.policy_expires_at
        if until is not None and until <= s.scalar(select(func.clock_timestamp())):
            raise LedgerLimit('candidate retention policy expired; evidence retained')

    def _map_item(self, domain, source_id, payload):
        return classify(domain,source_id,payload)

    def _event(self,s,ticket,version,action,reason,row,to_state, *, key=None, digest=None):
        self._policy(s)
        revision = version['revision'] + 1
        if revision > self.ledger_limits.max_transitions:
            raise LedgerLimit('transition history budget; debt retained')
        eid = str(uuid.uuid4())
        key = key or hashlib.sha256(encode([version['id'],action,ticket.run_id,row['ordinal']])).hexdigest()
        s.execute(insert(dm.event).values(id=eid,event_key=key,obligation_id=version['id'],
            revision=revision,from_state=version['state'] if version['revision'] else None,
            to_state=to_state,action=action,reason=reason,evidence_run=ticket.run_id,
            evidence_ordinal=row['ordinal'],target_digest=digest,at=func.clock_timestamp(),
            fence=ticket.fence,owner=ticket.owner))
        return dict(revision=revision,last_event=eid,state=to_state,fence=ticket.fence,owner=ticket.owner)

    def _on_receipt(self,s,ticket,row,disposition,reason,target_id,target_digest):
        self._policy(s)
        identity = family_identity(ticket.domain,row['source_id'])
        family = s.execute(select(dm.family).where(dm.family.c.id==identity)).mappings().one_or_none()
        unresolved = disposition not in TERMINAL
        if family is None and not unresolved:
            return  # Proven exclusion/success never creates invented debt.
        if family is None:
            s.execute(insert(dm.family).values(id=identity,domain=ticket.domain,source_system='MAXIMO',
                source_object='MXASSET' if ticket.domain=='asset_master' else 'MXWODETAIL',
                source_id=row['source_id'],scope_key='BSR:IP:WO_BSR',policy_epoch=POLICY_EPOCH,mapper_epoch=EPOCH))
            old = None
        else:
            old = s.execute(select(dm.version).where(dm.version.c.id==family['current_id'])).mappings().one()
        fresh_version = old is None or old['fingerprint'] != row['fingerprint']
        # Deterministic mapping cannot both resolve and fail an identical version.
        # Preserve the evidence and require epoch/policy review, never invent a change.
        if old and old['state']=='RESOLVED' and unresolved and not fresh_version:
            raise TransitionRejected('resolved fingerprint produced incompatible disposition')
        if old and old['state']=='RESOLVED' and not unresolved and not fresh_version:
            return
        if fresh_version:
            transition_count = 2 if old and old['state'] in ACTIVE else 1
            if transition_count > self.ledger_limits.transition_batch:
                raise LedgerLimit('transition batch budget; debt retained')
            if old and old['version'] >= self.ledger_limits.max_versions:
                raise LedgerLimit('version history budget; debt retained')
            vid = str(uuid.uuid4())
            if old and old['state'] not in ('RESOLVED','SUPERSEDED_BY_NEW_VERSION'):
                values=self._event(s,ticket,old,'SUPERSEDED','SOURCE_VERSION_CHANGED',row,
                                   'SUPERSEDED_BY_NEW_VERSION')
                s.execute(update(dm.version).where(dm.version.c.id==old['id']).values(**values,superseded_by=vid))
            metadata,deps=describe(ticket.domain,row['source_id'],row['payload'],disposition,reason,target_id)
            if len(deps)>self.ledger_limits.max_dependencies:
                raise LedgerLimit('dependency reference budget')
            manifest=s.scalar(select(pm.run.c.manifest_id).where(pm.run.c.id==ticket.run_id))
            v=dict(id=vid,family_id=identity,version=old['version']+1 if old else 1,
                fingerprint=row['fingerprint'],first_run=ticket.run_id,first_manifest=manifest,
                first_ordinal=row['ordinal'],predecessor_id=old['id'] if old else None,attempts=1,revision=0,state='OPEN',**metadata)
            state='BLOCKED_NEEDS_REVIEW' if disposition=='FAILED' else 'OPEN'
            if unresolved and v['attempts']>=self.ledger_limits.max_attempts:
                state='BLOCKED_NEEDS_REVIEW'
            values=self._event(s,ticket,v,'OBSERVED','SOURCE_VERSION_CHANGED' if old else 'CAPTURE_DISPOSITION',row,state)
            s.execute(insert(dm.version).values(**{k:val for k,val in v.items() if k not in values},
                **values,first_at=func.clock_timestamp(),last_attempt=func.clock_timestamp()))
            for kind,key in deps:
                s.execute(insert(dm.dependency).values(obligation_id=vid,kind=kind,scoped_key=key))
            s.execute(update(dm.family).where(dm.family.c.id==identity).values(current_id=vid))
        else:
            vid=old['id']
            if old['attempts']>=self.ledger_limits.max_attempts:
                raise LedgerLimit('attempt history budget; debt retained')
            attempts=old['attempts']+1
            blocked=(old['state']=='BLOCKED_NEEDS_REVIEW' or
                     attempts>=self.ledger_limits.max_attempts or disposition=='FAILED')
            state='BLOCKED_NEEDS_REVIEW' if blocked else ('OPEN' if unresolved else old['state'])
            values=self._event(s,ticket,old,'ATTEMPT','ATTEMPT_LIMIT' if blocked else 'CAPTURE_DISPOSITION',row,state)
            s.execute(update(dm.version).where(dm.version.c.id==vid).values(**values,
                attempts=attempts,last_attempt=func.clock_timestamp()))
        s.execute(insert(dm.occurrence).values(run_id=ticket.run_id,ordinal=row['ordinal'],obligation_id=vid))

    def _proof(self,s,ticket,family,version,reference, *, resolved=False, require_ready=True):
        run_id,ordinal = reference
        if run_id != ticket.run_id:
            raise TransitionRejected('evidence is not from the current fenced run')
        row=s.execute(select(pm.item).where(pm.item.c.run_id==run_id,pm.item.c.ordinal==ordinal)).mappings().one_or_none()
        capture = s.execute(select(pm.run).where(pm.run.c.id==run_id)).mappings().one()
        if not capture['sealed'] or capture['domain']!=ticket.domain or capture['epoch']!=EPOCH or not self._scope_compatible(capture['scope']):
            raise TransitionRejected('incompatible evidence manifest')
        if (row is None or row['source_id']!=family['source_id'] or row['fingerprint']!=version['fingerprint']):
            raise TransitionRejected('receipt identity/version mismatch')
        if not require_ready:
            return row
        record,disposition,reason=classify(ticket.domain,row['source_id'],row['payload'])
        if record is None and disposition!='EXPECTED_EXCLUSION':
            raise TransitionRejected('dependency or mapping not ready')
        if not resolved:
            return row
        if row['acked_at'] is None or row['disposition'] not in TERMINAL:
            raise TransitionRejected('valid committed receipt required')
        if row['disposition']=='EXPECTED_EXCLUSION':
            if disposition!='EXPECTED_EXCLUSION' or reason!='APPROVED_WO_PREFIX':
                raise TransitionRejected('unproven exclusion')
        elif (record is None or row['target_id']!=record['canonical_id'] or
                row['target_digest']!=self._target_digest(s,ticket.domain,row['target_id'])):
            raise TransitionRejected('target receipt drift')
        return row

    def transition(self,ticket,obligation_id,expected_revision,action,reference,event_key, *, before_commit=None):
        """One synthetic controlled transition, exact revision + receipt evidence.

        Dependency readiness alone is never resolution. No replay is performed.
        """
        if not self.controlled_transitions:
            raise TransitionRejected('controlled transition capability is disabled')
        try:
            uuid.UUID(event_key)
        except (ValueError,TypeError,AttributeError):
            raise TransitionRejected('bounded event UUID required') from None
        if action not in ('ELIGIBLE','BLOCKED','RESOLVED'):
            raise TransitionRejected('unsupported transition')
        with self.db.session() as s,s.begin():
            self._limits(s); self._lock(s,ticket); self._policy(s)
            v=s.execute(select(dm.version).where(dm.version.c.id==obligation_id).with_for_update()).mappings().one()
            f=s.execute(select(dm.family).where(dm.family.c.id==v['family_id'])).mappings().one()
            if f['domain']!=ticket.domain or f['current_id']!=obligation_id:
                raise FencedOut('not current obligation ownership')
            prior=s.execute(select(dm.event).where(dm.event.c.event_key==event_key)).mappings().one_or_none()
            if prior:
                if (prior['obligation_id']!=obligation_id or prior['action']!=action or
                    (prior['evidence_run'],prior['evidence_ordinal'])!=reference):
                    raise TransitionRejected('event identity collision')
                if action=='RESOLVED':
                    self._proof(s,ticket,f,v,reference,resolved=True)
                return dict(v)
            if v['revision']!=expected_revision:
                raise TransitionRejected('stale obligation revision')
            if action=='RESOLVED' and v['state']=='RESOLVED':
                self._proof(s,ticket,f,v,reference,resolved=True)
                return dict(v)
            allowed={'ELIGIBLE':('OPEN',),'BLOCKED':('OPEN','ELIGIBLE_FOR_RETRY'),
                     'RESOLVED':('ELIGIBLE_FOR_RETRY',)}
            if v['state'] not in allowed[action]:
                raise TransitionRejected('invalid obligation transition')
            row=self._proof(s,ticket,f,v,reference,resolved=action=='RESOLVED',require_ready=action!='BLOCKED')
            state={'ELIGIBLE':'ELIGIBLE_FOR_RETRY','BLOCKED':'BLOCKED_NEEDS_REVIEW','RESOLVED':'RESOLVED'}[action]
            reason={'ELIGIBLE':'DEPENDENCY_READY','BLOCKED':'REVIEW_REQUIRED','RESOLVED':'VALID_RECEIPT'}[action]
            values=self._event(s,ticket,v,action,reason,row,state,key=event_key,digest=row['target_digest'])
            if action=='RESOLVED': values['resolution_event']=values['last_event']
            s.execute(update(dm.version).where(dm.version.c.id==v['id']).values(**values))
            if before_commit: before_commit(s)
            self._not_expired(s,ticket)
            return dict(s.execute(select(dm.version).where(dm.version.c.id==v['id'])).mappings().one())

    def _coverage_incomplete(self,s,ticket):
        self._policy(s)
        # Original DEFERRED receipts stay immutable and their runs stay PARTIAL.
        own=s.scalar(select(exists(select(pm.item.c.ordinal).where(pm.item.c.run_id==ticket.run_id,
                    or_(pm.item.c.disposition.is_(None),pm.item.c.disposition.not_in(TERMINAL))))))
        if own: return True
        active=s.scalar(select(exists(select(dm.version.c.id).join(dm.family,
            dm.family.c.id==dm.version.c.family_id).where(dm.family.c.domain==ticket.domain,
                                                        dm.version.c.state.in_(ACTIVE)))))
        if active: return True
        # Any B1 debt without a B2 link is UNKNOWN; never auto-import/forgive it.
        incomplete=s.scalar(select(exists(select(pm.item.c.ordinal).join(pm.run,
            pm.run.c.id==pm.item.c.run_id).outerjoin(dm.occurrence,
            (dm.occurrence.c.run_id==pm.item.c.run_id)&(dm.occurrence.c.ordinal==pm.item.c.ordinal))
            .where(pm.run.c.domain==ticket.domain,pm.run.c.sealed,
                or_(pm.item.c.disposition.is_(None),
                    pm.item.c.disposition.not_in(TERMINAL)&dm.occurrence.c.obligation_id.is_(None))))))
        if incomplete: return True
        # Bounded proof revalidation; fail closed rather than scanning unlimited debt.
        proofs=s.execute(select(dm.version,dm.family.c.domain).join(dm.family,
            dm.family.c.id==dm.version.c.family_id).where(dm.family.c.domain==ticket.domain,
                dm.family.c.current_id==dm.version.c.id,dm.version.c.state=='RESOLVED')
            .limit(self.ledger_limits.coverage_proofs+1)).mappings().all()
        if len(proofs)>self.ledger_limits.coverage_proofs:
            raise LedgerLimit('coverage proof budget; complete withheld')
        for v in proofs:
            event=s.execute(select(dm.event).where(dm.event.c.id==v['resolution_event'])).mappings().one()
            row=s.execute(select(pm.item).where(pm.item.c.run_id==event['evidence_run'],
                pm.item.c.ordinal==event['evidence_ordinal'])).mappings().one()
            if row['target_id'] is not None and row['target_digest']!=self._target_digest(s,ticket.domain,row['target_id']):
                raise FencedOut('resolved obligation target drift')
        return False

# Filled from the reviewed follow-on migration. Schema drift is not repaired at startup.
GUARDS = {'mart_deferred_append_only': 'ad802d3eda901ff026ad2e4df69f3d97c642c3393543abeab7ee9e383b64452e',
 'mart_deferred_audit_guard': '7b07469d2f3bf9e1220c70af6e5d7b540932b63528e13096ff21add9651a15de',
 'mart_deferred_family_guard': 'b4579c893f12d3e22ba442d8ba08397bb094cbe5bf2fd93d203d426bef5e30cf',
 'mart_deferred_version_guard': '33966907711a2cd880fd8a6dc61e1bc8955daf07281c1e74049b5550a2a1939d'}
REQUIRED_TRIGGERS = {('mart_deferred_dependency',
  'deferred_dependency_immutable',
  27,
  'O',
  False,
  False,
  'mart_deferred_append_only'),
 ('mart_deferred_event',
  'deferred_event_immutable',
  27,
  'O',
  False,
  False,
  'mart_deferred_append_only'),
 ('mart_deferred_family',
  'deferred_family_guard',
  27,
  'O',
  False,
  False,
  'mart_deferred_family_guard'),
 ('mart_deferred_occurrence',
  'deferred_occurrence_immutable',
  27,
  'O',
  False,
  False,
  'mart_deferred_append_only'),
 ('mart_deferred_version',
  'deferred_audit_guard',
  21,
  'O',
  True,
  True,
  'mart_deferred_audit_guard'),
 ('mart_deferred_version',
  'deferred_version_guard',
  31,
  'O',
  False,
  False,
  'mart_deferred_version_guard')}

CATALOG_SIGNATURE = 'faca19addbe32d3e024ca83c8421c3f5cb6f60e0e7a738f67760d38daf7af92a'

REQUIRED_TRIGGERS |= {
    ('mart_deferred_family','deferred_no_truncate',34,'O',False,False,'mart_deferred_append_only'),
    ('mart_deferred_version','deferred_no_truncate',34,'O',False,False,'mart_deferred_append_only'),
    ('mart_deferred_event','deferred_no_truncate',34,'O',False,False,'mart_deferred_append_only'),
    ('mart_deferred_dependency','deferred_no_truncate',34,'O',False,False,'mart_deferred_append_only'),
    ('mart_deferred_occurrence','deferred_no_truncate',34,'O',False,False,'mart_deferred_append_only'),
}
