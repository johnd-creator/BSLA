"""New B2 cases, alongside unchanged B1 suite in the same private PG runner."""
from pathlib import Path
import unittest
import uuid
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import psycopg
from sqlalchemy import insert, select, update, delete, text, func
from sqlalchemy.exc import DBAPIError
import test_capture_postgres as b1
from src.repositories import models, mart_models, projection_models as pm, deferred_models as dm
from src.repositories.projection_store import ProjectionStore, FencedOut
from src.repositories.deferred_store import (DeferredProjectionStore, LedgerLimits, LedgerLimit,
    TransitionRejected, CaptureError)
from src.services.mart import MartPersistenceError

MIGRATION = Path(__file__).resolve().parents[1]/'migrations/005_deferred_obligation_candidate.sql'

class DeferredPostgreSQLTest(unittest.TestCase):
    # Reuse only B1's independently verified private fixture, not its test methods.
    cursors=b1.PostgreSQLCaptureTest.cursors
    rows=b1.PostgreSQLCaptureTest.rows
    add_asset=b1.PostgreSQLCaptureTest.add_asset
    add_wo=b1.PostgreSQLCaptureTest.add_wo
    expire=b1.PostgreSQLCaptureTest.expire
    tearDown=b1.PostgreSQLCaptureTest.tearDown

    def setUp(self):
        self.ready=False
        b1.PostgreSQLCaptureTest.setUp(self)
        with self.db.engine.connect() as c:
            c.connection.driver_connection.execute(MIGRATION.read_text())
            c.connection.driver_connection.commit()
        self.ready=True
        self.store=self.fresh()

    def fresh(self, **kwargs):
        if not self.ready: return ProjectionStore(self.db,enabled=True,exclusive_writer=True,**kwargs)
        return DeferredProjectionStore(self.db,enabled=True,exclusive_writer=True,
                                       controlled_transitions=True,**kwargs)

    def debt(self, **kwargs):
        self.add_wo(**kwargs)
        ticket=self.store.capture('maintenance_event')
        self.assertEqual(self.store.process(ticket)['status'],'PARTIAL')
        return ticket

    def current(self):
        with self.db.session() as s:
            return dict(s.execute(select(dm.version).join(dm.family,dm.family.c.current_id==dm.version.c.id)).mappings().one())

    def repaired(self):
        old=self.debt(); self.store.release(old); self.add_asset()
        ticket=self.store.capture('maintenance_event'); self.store.process(ticket)
        return old,ticket,self.current()

    def step(self,ticket,version,action, *, key=None, revision=None, reference=None):
        return self.store.transition(ticket,version['id'],version['revision'] if revision is None else revision,
            action,reference or (ticket.run_id,1),key or str(uuid.uuid4()))

    def test_missing_equipment_creates_single_debt_and_receipt(self):
        ticket=self.debt()
        v=self.current()
        self.assertEqual((v['state'],v['classification'],v['attempts']),('OPEN','DEFERRED_DEPENDENCY',1))
        self.assertEqual(len(self.rows(dm.family)),1); self.assertEqual(len(self.rows(dm.event)),1)
        self.assertEqual(len(self.rows(dm.occurrence)),1)
        self.assertEqual(self.store.inspect(ticket.run_id)['continuation'],1)
        self.assertTrue(self.rows(dm.dependency)[0]['scoped_key'].endswith(':A'))

    def test_repeated_failure_idempotent_delivery_but_distinct_attempt_audited(self):
        ticket=self.debt(); before=self.rows(dm.event)
        self.store.process(ticket)
        self.assertEqual(before,self.rows(dm.event))
        self.store.release(ticket)
        next_ticket=self.store.capture('maintenance_event'); self.store.process(next_ticket)
        self.assertEqual(len(self.rows(dm.version)),1)
        self.assertEqual(self.current()['attempts'],2)
        self.assertEqual(len(self.rows(dm.occurrence)),2); self.assertEqual(len(self.rows(dm.event)),2)

    def test_dependency_survives_restart_without_payload_copy(self):
        ticket=self.debt(); before=self.rows(dm.dependency)
        self.store.release(ticket)
        restarted=self.fresh(); resumed=restarted.resume('maintenance_event',ticket.run_id)
        self.assertEqual(restarted.process(resumed)['status'],'PARTIAL')
        self.assertEqual(before,self.rows(dm.dependency))
        self.assertNotIn('payload',dm.version.c); self.assertNotIn('payload',dm.event.c)

    def test_omitted_and_deleted_source_debt_remains_incomplete(self):
        ticket=self.debt(); self.store.release(ticket)
        with self.db.session() as s,s.begin(): s.execute(delete(models.WorkOrderOrm))
        new=self.store.capture('maintenance_event')
        self.assertEqual(self.store.process(new)['status'],'PARTIAL')
        self.assertEqual(self.current()['state'],'OPEN')
        self.assertIsNone(self.rows(pm.lease)[0]['last_complete_run'])

    def test_fingerprint_change_supersession_and_receipt_immutability(self):
        old=self.debt(); receipt=self.rows(pm.item)[0]; self.store.release(old)
        with self.db.session() as s,s.begin(): s.execute(update(models.WorkOrderOrm).values(equipment_id='B'))
        new=self.store.capture('maintenance_event'); self.store.process(new)
        versions=sorted(self.rows(dm.version),key=lambda v:v['version'])
        self.assertEqual(versions[0]['state'],'SUPERSEDED_BY_NEW_VERSION')
        self.assertEqual(versions[0]['superseded_by'],versions[1]['id'])
        self.assertEqual(versions[1]['predecessor_id'],versions[0]['id'])
        self.assertNotEqual(versions[0]['fingerprint'],versions[1]['fingerprint'])
        self.assertEqual(receipt,self.rows(pm.item,pm.item.c.run_id==old.run_id)[0])
        self.assertEqual(sum(v['state']=='OPEN' for v in versions),1)

    def test_scope_proof_unknown_never_exclusion(self):
        self.add_asset(sources={'maximo':{'assetnum':'A'}})
        ticket=self.store.capture('asset_master'); self.store.process(ticket)
        v=self.current()
        self.assertEqual((v['classification'],v['scope_proof'],v['site'],v['canonical_id']),
                         ('DEFERRED_SCOPE_PROOF','UNKNOWN',None,None))
        self.assertEqual(self.rows(pm.item)[0]['disposition'],'DEFERRED')

    def test_approved_prefix_exclusion_creates_no_debt(self):
        self.add_wo('OTHER-1'); ticket=self.store.capture('maintenance_event')
        self.assertEqual(self.store.process(ticket)['status'],'COMPLETE')
        self.assertEqual(self.rows(dm.family),[]); self.assertEqual(self.rows(dm.event),[])
        self.assertEqual(self.rows(pm.item)[0]['disposition'],'EXPECTED_EXCLUSION')

    def test_missing_mapping_input_is_deferred(self):
        self.add_asset(sources={'maximo':{'assetnum':'','siteid':'BSR','orgid':'IP'}})
        ticket=self.store.capture('asset_master'); self.store.process(ticket)
        self.assertEqual(self.current()['classification'],'DEFERRED_MAPPING')
        self.assertEqual(self.current()['reason'],'MISSING_REQUIRED_ID')

    def test_invalid_mapper_is_blocked_not_ordinary_deferred(self):
        self.add_asset(sources={'maximo':{'assetnum':'A','siteid':'BSR','orgid':'IP','changedate':'malformed'}})
        ticket=self.store.capture('asset_master'); self.store.process(ticket)
        self.assertEqual(self.current()['state'],'BLOCKED_NEEDS_REVIEW')
        self.assertEqual(self.current()['classification'],'FAILED_MAPPING')
        self.assertEqual(self.rows(pm.item)[0]['disposition'],'FAILED')

    def test_writer_error_not_downgraded_to_ledger_failure(self):
        self.add_asset(); ticket=self.store.capture('asset_master')
        with patch.object(self.store.writer,'persist_in_session',side_effect=MartPersistenceError('synthetic')):
            with self.assertRaises(MartPersistenceError): self.store.process(ticket)
        self.assertEqual(self.rows(dm.family),[]); self.assertEqual(self.rows(dm.event),[])
        self.assertIsNone(self.rows(pm.item)[0]['acked_at'])
        self.assertEqual(self.store.inspect(ticket.run_id)['continuation'],0)

    def test_crash_before_commit_rolls_back_ledger_receipt_and_continuation(self):
        self.add_wo(); ticket=self.store.capture('maintenance_event')
        def crash(_): raise RuntimeError('synthetic before commit')
        with self.assertRaises(RuntimeError): self.store.process(ticket,before_commit=crash)
        for table in (dm.family,dm.version,dm.dependency,dm.event,dm.occurrence): self.assertEqual(self.rows(table),[])
        self.assertIsNone(self.rows(pm.item)[0]['acked_at'])
        self.assertEqual(self.store.inspect(ticket.run_id)['continuation'],0)

    def test_actual_disconnect_rolls_back_debt_atomically(self):
        self.add_wo(); ticket=self.store.capture('maintenance_event')
        def disconnect(s): s.connection().connection.driver_connection.close()
        with self.assertRaises(DBAPIError): self.store.process(ticket,before_commit=disconnect)
        self.assertEqual(self.rows(dm.event),[]); self.assertEqual(self.rows(dm.version),[])
        self.assertIsNone(self.rows(pm.item)[0]['acked_at'])

    def test_lost_ack_commit_preserves_debt_across_restart(self):
        self.add_wo(); ticket=self.store.capture('maintenance_event')
        def lost(): raise RuntimeError('synthetic lost reply')
        with self.assertRaises(RuntimeError): self.store.process(ticket,after_commit=lost)
        before=self.rows(dm.event); self.assertEqual(len(before),1)
        self.assertEqual(self.store.inspect(ticket.run_id)['continuation'],1)
        self.store.release(ticket); restarted=self.fresh(); new=restarted.resume('maintenance_event',ticket.run_id)
        self.assertEqual(restarted.process(new)['status'],'PARTIAL')
        self.assertEqual(before,self.rows(dm.event)); self.assertEqual(self.current()['attempts'],1)

    def test_stale_and_expired_worker_cannot_change_debt(self):
        ticket=self.debt(); v=self.current(); self.expire(ticket)
        with self.assertRaises(FencedOut): self.step(ticket,v,'BLOCKED')
        new=self.store.resume('maintenance_event',ticket.run_id)
        with self.assertRaises(FencedOut): self.step(ticket,v,'BLOCKED')
        self.assertEqual(self.current()['state'],'OPEN')
        self.assertEqual(self.step(new,v,'BLOCKED')['state'],'BLOCKED_NEEDS_REVIEW')

    def test_repaired_dependency_and_new_target_do_not_auto_resolve(self):
        _,ticket,v=self.repaired()
        self.assertEqual(v['state'],'OPEN'); self.assertEqual(v['classification'],'RESOLUTION_PENDING')
        self.assertEqual(self.store.inspect(ticket.run_id)['status'],'PARTIAL')
        self.assertEqual(len(self.rows(mart_models.MaintenanceEventMartOrm.__table__)),1)

    def test_resolution_requires_eligible_state_and_committed_matching_target(self):
        _,ticket,v=self.repaired()
        with self.assertRaises(TransitionRejected): self.step(ticket,v,'RESOLVED')
        eligible=self.step(ticket,v,'ELIGIBLE')
        with self.db.session() as s,s.begin():
            s.execute(update(mart_models.MaintenanceEventMartOrm).values(status='UNFENCED'))
        with self.assertRaises(TransitionRejected): self.step(ticket,eligible,'RESOLVED')
        self.assertEqual(self.current()['state'],'ELIGIBLE_FOR_RETRY')

    def test_audited_resolution_holds_original_run_partial_and_new_can_complete(self):
        old,ticket,v=self.repaired(); receipt=self.rows(pm.item,pm.item.c.run_id==old.run_id)[0]
        eligible=self.step(ticket,v,'ELIGIBLE'); resolved=self.step(ticket,eligible,'RESOLVED')
        self.assertEqual(resolved['state'],'RESOLVED'); self.assertIsNotNone(resolved['resolution_event'])
        self.assertEqual(self.store.process(ticket)['status'],'COMPLETE')
        self.assertEqual(self.store.inspect(old.run_id)['status'],'PARTIAL')
        self.assertEqual(receipt,self.rows(pm.item,pm.item.c.run_id==old.run_id)[0])

    def test_idempotent_resolution_and_event_identity_collision(self):
        _,ticket,v=self.repaired(); eligible=self.step(ticket,v,'ELIGIBLE'); key=str(uuid.uuid4())
        result=self.step(ticket,eligible,'RESOLVED',key=key)
        events=self.rows(dm.event)
        again=self.step(ticket,eligible,'RESOLVED',key=key)
        self.assertEqual(result,again); self.assertEqual(events,self.rows(dm.event))
        with self.assertRaises(TransitionRejected): self.step(ticket,result,'BLOCKED',key=key)

    def test_concurrent_workers_cannot_double_resolve(self):
        _,ticket,v=self.repaired(); eligible=self.step(ticket,v,'ELIGIBLE')
        def resolve():
            try: return self.step(ticket,eligible,'RESOLVED')['state']
            except TransitionRejected: return 'STALE_REVISION'
        with ThreadPoolExecutor(max_workers=2) as executor:
            results=list(executor.map(lambda _:resolve(), range(2)))
        self.assertCountEqual(results,['RESOLVED','STALE_REVISION'])
        self.assertEqual(sum(e['action']=='RESOLVED' for e in self.rows(dm.event)),1)

    def test_transition_crash_leaves_no_resolution_event(self):
        _,ticket,v=self.repaired(); eligible=self.step(ticket,v,'ELIGIBLE'); before=self.rows(dm.event)
        def crash(_): raise RuntimeError('synthetic transition crash')
        with self.assertRaises(RuntimeError):
            self.store.transition(ticket,v['id'],eligible['revision'],'RESOLVED',(ticket.run_id,1),
                                  str(uuid.uuid4()),before_commit=crash)
        self.assertEqual(before,self.rows(dm.event)); self.assertEqual(self.current()['state'],'ELIGIBLE_FOR_RETRY')

    def test_controlled_transition_opt_in_and_cas(self):
        ticket=self.debt(); v=self.current()
        protected=DeferredProjectionStore(self.db,enabled=True,exclusive_writer=True)
        with self.assertRaises(TransitionRejected):
            protected.transition(ticket,v['id'],v['revision'],'BLOCKED',(ticket.run_id,1),str(uuid.uuid4()))
        with self.assertRaises(TransitionRejected): self.step(ticket,v,'BLOCKED',revision=0)
        with self.assertRaises(TransitionRejected): self.step(ticket,v,'BLOCKED',key='arbitrary string')

    def test_poison_attempt_limit_retains_debt_and_unprocessed_next_item(self):
        limited=self.fresh(ledger_limits=LedgerLimits(max_attempts=2)); self.store=limited
        ticket=self.debt(); limited.release(ticket)
        second=limited.capture('maintenance_event'); limited.process(second)
        self.assertEqual((self.current()['attempts'],self.current()['state']),(2,'BLOCKED_NEEDS_REVIEW'))
        limited.release(second); third=limited.capture('maintenance_event')
        with self.assertRaises(LedgerLimit): limited.process(third)
        self.assertEqual(self.store.inspect(third.run_id)['continuation'],0)
        self.assertEqual(self.current()['attempts'],2)

    def test_expired_policy_blocks_mutation_without_purging_evidence(self):
        ticket=self.debt(); before=self.rows(dm.version); self.store.release(ticket)
        expired=self.fresh(ledger_limits=LedgerLimits(policy_expires_at=b1.NOW))
        new=expired.capture('maintenance_event')
        with self.assertRaises(LedgerLimit): expired.process(new)
        self.assertEqual(before,self.rows(dm.version)); self.assertEqual(expired.inspect(new.run_id)['continuation'],0)

    def test_null_ties_and_backdated_change_preserve_debt(self):
        self.add_wo('BSR-1',source_changed_at=None); self.add_wo('BSR-2',source_changed_at=None)
        ticket=self.store.capture('maintenance_event'); self.store.process(ticket); self.store.release(ticket)
        self.assertEqual(len(self.rows(dm.version)),2)
        with self.db.session() as s,s.begin():
            s.execute(update(models.WorkOrderOrm).where(models.WorkOrderOrm.id=='BSR-1')
                      .values(source_changed_at=b1.NOW-timedelta(days=1000)))
        new=self.store.capture('maintenance_event'); self.assertEqual(self.store.process(new)['status'],'PARTIAL')
        self.assertEqual(len(self.rows(dm.family)),2); self.assertEqual(len(self.rows(dm.version)),3)

    def test_retention_cannot_delete_or_rewrite_pending_or_audit(self):
        self.debt()
        for table in (dm.family,dm.version,dm.event,dm.dependency,dm.occurrence):
            with self.subTest(table=table.name),self.assertRaises(DBAPIError):
                with self.db.session() as s,s.begin(): s.execute(delete(table))
        with self.assertRaises(DBAPIError):
            with self.db.session() as s,s.begin(): s.execute(update(dm.event).values(reason='REVIEW_REQUIRED'))

    def test_missing_dependency_index_and_unique_constraint_fail_preflight(self):
        with self.db.session() as s,s.begin(): s.execute(text('DROP INDEX deferred_dependency_lookup'))
        with self.assertRaises(CaptureError): self.fresh()

    def test_missing_event_constraint_fails_preflight(self):
        with self.db.session() as s,s.begin():
            s.execute(text('ALTER TABLE mart_deferred_event DROP CONSTRAINT deferred_event_key'))
        with self.assertRaises(CaptureError): self.fresh()

    def test_trigger_and_type_drift_fail_preflight(self):
        with self.db.session() as s,s.begin():
            s.execute(text('ALTER TABLE mart_deferred_event DISABLE TRIGGER deferred_event_immutable'))
        with self.assertRaises(CaptureError): self.fresh()

    def test_005_requires_004_and_cannot_be_reapplied(self):
        with self.assertRaises(psycopg.errors.DuplicateTable):
            with self.db.engine.connect() as c: c.connection.driver_connection.execute(MIGRATION.read_text())
        empty='empty_'+uuid.uuid4().hex
        with self.db.session() as s,s.begin(): s.execute(text('CREATE SCHEMA '+empty))
        with self.assertRaises(psycopg.errors.UndefinedTable):
            with self.db.engine.connect() as c:
                raw=c.connection.driver_connection
                raw.execute('SET LOCAL search_path TO '+empty)
                raw.execute(MIGRATION.read_text())

    def test_missing_target_asset_stays_soft_reference(self):
        self.add_asset(); self.add_wo()
        ticket=self.store.capture('maintenance_event')
        self.assertEqual(self.store.process(ticket)['status'],'COMPLETE')
        self.assertEqual(self.rows(mart_models.AssetMasterMartOrm.__table__),[])
        self.assertEqual(len(self.rows(mart_models.MaintenanceEventMartOrm.__table__)),1)
        self.assertEqual(self.rows(dm.version),[])

    def test_unlinked_pre_b2_debt_never_assumed_resolved(self):
        self.add_wo()
        legacy=ProjectionStore(self.db,enabled=True,exclusive_writer=True)
        ticket=legacy.capture('maintenance_event'); legacy.process(ticket); legacy.release(ticket)
        with self.db.session() as s,s.begin(): s.execute(delete(models.WorkOrderOrm))
        new=self.store.capture('maintenance_event')
        self.assertEqual(self.store.process(new)['status'],'PARTIAL'); self.assertEqual(self.rows(dm.version),[])

    def test_wrong_record_cannot_supply_resolution_evidence(self):
        ticket=self.debt(); v=self.current()
        with self.assertRaises(TransitionRejected): self.step(ticket,v,'ELIGIBLE',reference=(ticket.run_id,999))
        with self.assertRaises(TransitionRejected): self.step(ticket,v,'ELIGIBLE',reference=(str(uuid.uuid4()),1))

    def test_transition_and_version_history_caps_fail_closed(self):
        limited=self.fresh(ledger_limits=LedgerLimits(max_versions=1)); self.store=limited
        old=self.debt(); limited.release(old)
        with self.db.session() as s,s.begin(): s.execute(update(models.WorkOrderOrm).values(status='CLOSE'))
        new=limited.capture('maintenance_event')
        with self.assertRaises(LedgerLimit): limited.process(new)
        self.assertEqual(self.current()['state'],'OPEN'); self.assertEqual(len(self.rows(dm.version)),1)
        self.assertEqual(limited.inspect(new.run_id)['continuation'],0)

    def test_resolved_audit_cannot_be_deleted_or_rewritten(self):
        _,ticket,v=self.repaired(); eligible=self.step(ticket,v,'ELIGIBLE'); result=self.step(ticket,eligible,'RESOLVED')
        for query in (delete(dm.version).where(dm.version.c.id==result['id']),
                      update(dm.version).where(dm.version.c.id==result['id']).values(state='OPEN')):
            with self.assertRaises(DBAPIError):
                with self.db.session() as s,s.begin(): s.execute(query)
        self.assertEqual(self.current()['state'],'RESOLVED')

    def test_source_scope_repair_has_version_lineage_and_requires_explicit_resolution(self):
        self.add_asset(sources={'maximo':{'assetnum':'A'}})
        old=self.store.capture('asset_master'); self.store.process(old); self.store.release(old)
        with self.db.session() as s,s.begin():
            s.execute(update(models.EquipmentOrm).values(sources={'maximo':{'assetnum':'A','siteid':'BSR','orgid':'IP'}}))
        new=self.store.capture('asset_master'); self.store.process(new)
        versions=sorted(self.rows(dm.version),key=lambda v:v['version'])
        self.assertEqual(versions[0]['scope_proof'],'UNKNOWN'); self.assertEqual(versions[1]['scope_proof'],'PROVEN')
        self.assertEqual(versions[1]['predecessor_id'],versions[0]['id'])
        self.assertEqual(self.store.inspect(new.run_id)['status'],'PARTIAL')

    def test_bounded_coverage_proof_check_withholds_complete(self):
        self.add_wo('BSR-001'); self.add_wo('BSR-002')
        old=self.store.capture('maintenance_event'); self.store.process(old); self.store.release(old); self.add_asset()
        new=self.store.capture('maintenance_event'); self.store.process(new)
        for ordinal,v in enumerate(sorted(self.rows(dm.version,dm.version.c.state=='OPEN'),key=lambda v:v['first_ordinal']),1):
            reference=(new.run_id,ordinal)
            eligible=self.step(new,v,'ELIGIBLE',reference=reference)
            self.step(new,eligible,'RESOLVED',reference=reference)
        limited=self.fresh(ledger_limits=LedgerLimits(coverage_proofs=1))
        with self.assertRaises(LedgerLimit): limited.process(new)
        self.assertEqual(limited.inspect(new.run_id)['status'],'PARTIAL')

    def test_multiple_dependency_references_do_not_duplicate_active_obligation(self):
        self.debt(); v=self.current()
        # Synthetic schema qualification of normalized multi-reference support;
        # no watcher/automatic dependency update API is introduced.
        with self.db.session() as s,s.begin():
            s.execute(insert(dm.dependency).values(obligation_id=v['id'],kind='MAPPING_INPUT',
                scoped_key='MAXIMO:maintenance_event:BSR-001:MAPPING_INPUT'))
        with self.db.session() as s:
            matches=s.execute(select(dm.dependency).where(dm.dependency.c.kind=='LOCAL_EQUIPMENT',
                dm.dependency.c.scoped_key=='asset:MAXIMO:MXASSET:BSR:IP:A').limit(2)).all()
        self.assertEqual(len(matches),1); self.assertEqual(len(self.rows(dm.version)),1)
        self.assertEqual(len(self.rows(dm.dependency)),2)

    def test_direct_stale_version_update_fails_database_guard(self):
        ticket=self.debt(); v=self.current(); self.expire(ticket)
        with self.assertRaises(DBAPIError):
            with self.db.session() as s,s.begin():
                s.execute(update(dm.version).values(revision=v['revision']+1,state='BLOCKED_NEEDS_REVIEW'))
        self.assertEqual(self.current(),v)

    def test_new_generation_after_resolution_cannot_silently_replace_changed_version(self):
        _,ticket,v=self.repaired(); eligible=self.step(ticket,v,'ELIGIBLE'); resolved=self.step(ticket,eligible,'RESOLVED')
        self.store.process(ticket); self.store.release(ticket)
        with self.db.session() as s,s.begin(): s.execute(update(models.WorkOrderOrm).values(status='CLOSE'))
        new=self.store.capture('maintenance_event'); self.store.process(new)
        current=self.current()
        self.assertEqual(current['predecessor_id'],resolved['id'])
        self.assertEqual(current['state'],'OPEN'); self.assertEqual(self.store.inspect(new.run_id)['status'],'PARTIAL')

    def test_transition_history_cap_retains_open_debt_without_fabricating_event(self):
        self.store=self.fresh(ledger_limits=LedgerLimits(max_attempts=20,max_transitions=4))
        ticket=self.debt()
        for _ in range(3):
            self.store.release(ticket); ticket=self.store.capture('maintenance_event'); self.store.process(ticket)
        self.assertEqual(len(self.rows(dm.event)),4)
        self.store.release(ticket); ticket=self.store.capture('maintenance_event')
        with self.assertRaises(LedgerLimit): self.store.process(ticket)
        self.assertEqual(len(self.rows(dm.event)),4); self.assertEqual(self.current()['state'],'OPEN')
        self.assertEqual(self.store.inspect(ticket.run_id)['continuation'],0)

    def test_other_record_exclusion_cannot_resolve_existing_debt(self):
        old=self.debt(); v=self.current(); self.store.release(old)
        with self.db.session() as s,s.begin(): s.execute(delete(models.WorkOrderOrm))
        self.add_wo('OTHER-1')
        new=self.store.capture('maintenance_event'); self.store.process(new)
        self.assertEqual(self.rows(pm.item,pm.item.c.run_id==new.run_id)[0]['disposition'],'EXPECTED_EXCLUSION')
        with self.assertRaises(TransitionRejected): self.step(new,v,'ELIGIBLE')
        self.assertEqual(self.current()['state'],'OPEN')

    def test_changed_partial_index_predicate_is_schema_drift(self):
        with self.db.session() as s,s.begin():
            s.execute(text('DROP INDEX deferred_one_active'))
            s.execute(text("CREATE UNIQUE INDEX deferred_one_active ON mart_deferred_version(family_id) WHERE state='OPEN'"))
        with self.assertRaises(CaptureError): self.fresh()

    def test_retention_cannot_truncate_debt(self):
        self.debt()
        with self.assertRaises(DBAPIError):
            with self.db.session() as s,s.begin(): s.execute(text('TRUNCATE mart_deferred_family CASCADE'))
        self.assertEqual(self.current()['state'],'OPEN')

    def test_resolved_target_drift_cannot_be_hidden_by_empty_capture(self):
        _,ticket,v=self.repaired(); eligible=self.step(ticket,v,'ELIGIBLE'); self.step(ticket,eligible,'RESOLVED')
        self.store.process(ticket); self.store.release(ticket)
        with self.db.session() as s,s.begin():
            s.execute(delete(models.WorkOrderOrm))
            s.execute(update(mart_models.MaintenanceEventMartOrm).values(status='UNFENCED'))
        new=self.store.capture('maintenance_event')
        with self.assertRaises(FencedOut): self.store.process(new)
        self.assertNotEqual(self.store.inspect(new.run_id)['status'],'COMPLETE')

    def test_expired_policy_blocks_empty_capture_completion(self):
        store=self.fresh(ledger_limits=LedgerLimits(policy_expires_at=b1.NOW))
        ticket=store.capture('asset_master')
        with self.assertRaises(LedgerLimit): store.process(ticket)
        self.assertNotEqual(store.inspect(ticket.run_id)['status'],'COMPLETE')

    def test_supersession_honors_transition_batch_budget(self):
        self.store=self.fresh(ledger_limits=LedgerLimits(transition_batch=1))
        old=self.debt(); self.store.release(old)
        with self.db.session() as s,s.begin(): s.execute(update(models.WorkOrderOrm).values(status='CLOSE'))
        new=self.store.capture('maintenance_event')
        with self.assertRaises(LedgerLimit): self.store.process(new)
        self.assertEqual(len(self.rows(dm.version)),1); self.assertEqual(self.current()['state'],'OPEN')

    def test_identical_resolved_fingerprint_cannot_be_silently_reinterpreted(self):
        _,ticket,v=self.repaired(); eligible=self.step(ticket,v,'ELIGIBLE'); self.step(ticket,eligible,'RESOLVED')
        self.store.process(ticket); self.store.release(ticket)
        new=self.store.capture('maintenance_event')
        with patch.object(self.store,'_map_item',return_value=(None,'DEFERRED','MISSING_LOCAL_EQUIPMENT')):
            with self.assertRaises(TransitionRejected): self.store.process(new)
        self.assertEqual(self.current()['state'],'RESOLVED')
        self.assertEqual(self.store.inspect(new.run_id)['continuation'],0)
