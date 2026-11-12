"""Synthetic B3 tests. Only runner-verified private Unix PG is permitted."""
from pathlib import Path
from datetime import timedelta
import unittest
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select, update, delete, text, insert, func
from sqlalchemy.exc import DBAPIError
import psycopg
import test_capture_postgres as b1
import test_deferred_postgres as b2
from src.repositories import replay_models as rm, deferred_models as dm, projection_models as pm, models, mart_models
from src.repositories.projection_store import ProjectionStore, CaptureError, FencedOut, Budget
from src.repositories.deferred_store import DeferredProjectionStore, LedgerLimit, LedgerLimits
from src.repositories.replay_store import ReplayStore, ReplayPolicy, GUARDS, TRIGGERS, CATALOG_SIGNATURE
from src.services.projection_replay import ProjectionReplay

MIGRATION=Path(__file__).resolve().parents[1]/'migrations/006_bounded_replay_candidate.sql'

class ReplayPostgreSQLTest(unittest.TestCase):
    rows=b1.PostgreSQLCaptureTest.rows
    cursors=b1.PostgreSQLCaptureTest.cursors
    add_asset=b1.PostgreSQLCaptureTest.add_asset
    add_wo=b1.PostgreSQLCaptureTest.add_wo
    expire=b1.PostgreSQLCaptureTest.expire
    tearDown=b1.PostgreSQLCaptureTest.tearDown
    current=b2.DeferredPostgreSQLTest.current

    def setUp(self):
        self.b3_ready=False
        self.addCleanup(lambda: self.db.engine.dispose() if hasattr(self,"db") else None)
        b2.DeferredPostgreSQLTest.setUp(self)
        with self.db.engine.connect() as c:
            c.connection.driver_connection.execute(MIGRATION.read_text())
            c.connection.driver_connection.commit()
        self.b3_ready=True
        self.store=self.fresh()

    def fresh(self,**kwargs):
        if not self.b3_ready:
            return b2.DeferredPostgreSQLTest.fresh(self,**kwargs)
        return ReplayStore(self.db,replay_enabled=True,enabled=True,exclusive_writer=True,
                           controlled_transitions=True,**kwargs)

    def debt(self,*,domain='maintenance_event',key='BSR001'):
        if domain=='maintenance_event': self.add_wo(key)
        else: self.add_asset(key,sources={'maximo':{'assetnum':key}})
        ticket=self.store.capture(domain); self.store.process(ticket)
        v=self.current(); self.store.register(ticket,v['id']); self.store.release(ticket)
        return ticket,v

    def service(self): return ProjectionReplay(self.store,enabled=True)

    def make_due(self):
        # Advance only synthetic scheduling via fenced candidate transaction.
        with self.db.session() as s,s.begin():
            d=s.execute(select(pm.lease)).mappings().one()
            s.execute(update(pm.lease).values(lease_until=func.clock_timestamp()+timedelta(seconds=60)))
            q=dict(s.execute(select(rm.queue)).mappings().one())
            from src.repositories.projection_store import Ticket
            self.store._change(s,Ticket(d['latest_run'],d['domain'],d['owner'],d['fence']),q,
                q['phase'],q['reason'],due_at=func.clock_timestamp()-timedelta(seconds=1))
            s.execute(update(pm.lease).values(lease_until=func.clock_timestamp()-timedelta(seconds=1)))

    def test_schema_catalog_pin(self):
        with self.db.session() as s:
            self.assertEqual(self.store._replay_catalog(s),CATALOG_SIGNATURE)

    def test_old_wo_repaired_exact_capture_supersedes_resolves(self):
        old,v=self.debt(); receipt=self.rows(pm.item)[0]
        self.add_asset()
        result=self.service().run('maintenance_event')
        self.assertEqual(result[0]['state'],'DONE')
        versions=sorted(self.rows(dm.version),key=lambda r:r['version'])
        self.assertEqual([v['state'] for v in versions],['SUPERSEDED_BY_NEW_VERSION','RESOLVED'])
        self.assertNotEqual(versions[0]['fingerprint'],versions[1]['fingerprint'])
        self.assertEqual(versions[1]['predecessor_id'],versions[0]['id'])
        self.assertEqual(versions[0]['superseded_by'],versions[1]['id'])
        self.assertEqual(receipt,self.rows(pm.item,pm.item.c.run_id==old.run_id)[0])
        recovery=self.rows(pm.item,pm.item.c.run_id==result[0]['run_id'])[0]
        self.assertEqual(recovery['payload']['source_changed_at'],receipt['payload']['source_changed_at'])
        self.assertEqual(recovery['source_id'],'BSR001')
        run=self.store.inspect(result[0]['run_id'])
        self.assertTrue(run['sealed']); self.assertEqual(run['item_count'],1)
        self.assertEqual(run['scope']['capture_mode'],'RECOVERY_BY_ID')
        self.assertEqual(run['status'],'PARTIAL')
        self.assertIsNone(self.rows(pm.lease)[0]['last_complete_run'])
        self.assertEqual(recovery['target_digest'],self.rows(pm.target)[0]['target_digest'])
        self.assertEqual(self.rows(rm.queue)[0]['phase'],'DONE')
        self.assertEqual(self.service().run('maintenance_event'),[])

    def test_missing_dependency_probes_do_not_consume_actual_budget(self):
        self.debt(); before=self.current()
        self.assertEqual(self.service().run('maintenance_event')[0]['state'],'NOT_READY')
        q=self.rows(rm.queue)[0]
        self.assertEqual((q['probes'],q['attempts'],q['phase']),(1,0,'PENDING'))
        self.assertEqual(self.current(),before)
        self.assertEqual(self.store.due('maintenance_event'),[])
        self.make_due(); self.service().run('maintenance_event')
        self.assertEqual(self.rows(rm.queue)[0]['probes'],2)
        self.assertEqual(self.current()['attempts'],1)

    def test_unknown_scope_not_resolved(self):
        self.debt(domain='asset_master',key='A')
        self.assertEqual(self.service().run('asset_master')[0]['state'],'UNKNOWN')
        self.assertEqual(self.current()['state'],'OPEN')

    def test_deleted_source_remains_unknown_blocked_without_target_delete(self):
        self.debt()
        with self.db.session() as s,s.begin(): s.execute(delete(models.WorkOrderOrm))
        self.assertEqual(self.service().run('maintenance_event')[0]['reason'],'SOURCE_ABSENT')
        self.assertEqual(self.rows(rm.queue)[0]['phase'],'BLOCKED')
        self.assertEqual(self.current()['state'],'OPEN')
        self.assertEqual(self.service().run('maintenance_event'),[])

    def test_null_timestamp_preserved(self):
        self.debt()
        with self.db.session() as s,s.begin():
            s.execute(update(models.WorkOrderOrm).values(source_changed_at=None))
        self.add_asset(); out=self.service().run('maintenance_event')
        self.assertIsNone(self.rows(pm.item,pm.item.c.run_id==out[0]['run_id'])[0]['payload']['source_changed_at'])

    def test_b1_b2_cannot_consume_targeted_manifest(self):
        self.debt(); self.add_asset(); t=self.store.claim_due('maintenance_event'); self.store.capture_claim(t)
        for cls in (ProjectionStore,DeferredProjectionStore):
            store=cls(self.db,enabled=True,exclusive_writer=True)
            with self.assertRaises(CaptureError): store.process(t)

    def test_attempt_reservation_required(self):
        self.debt(); self.add_asset(); t=self.store.claim_due('maintenance_event'); self.store.capture_claim(t)
        with self.assertRaises(CaptureError): self.store.process(t)
        self.assertIsNone(self.rows(pm.item,pm.item.c.run_id==t.run_id)[0]['acked_at'])

    def test_competing_claims_only_one_owner(self):
        self.debt(); self.add_asset()
        with ThreadPoolExecutor(2) as pool:
            claims=list(pool.map(lambda _:self.store.claim_due('maintenance_event'),range(2)))
        self.assertEqual(sum(c is not None for c in claims),1)

    def test_resume_new_fence_same_manifest(self):
        self.debt(); self.add_asset(); t=self.store.claim_due('maintenance_event'); self.store.capture_claim(t)
        self.expire(t); self.make_due()
        new=self.store.claim_due('maintenance_event')
        self.assertEqual(t.run_id,new.run_id); self.assertGreater(new.fence,t.fence)
        with self.assertRaises(FencedOut): self.store.reserve_attempt(t)
        self.assertTrue(self.store.reserve_attempt(new)); self.store.process(new,max_items=1)
        self.assertEqual(self.store.resolve_claim(new)['state'],'DONE')

    def test_source_changed_after_capture_refuses_stale_write(self):
        self.debt(); self.add_asset(); t=self.store.claim_due('maintenance_event'); self.store.capture_claim(t)
        with self.db.session() as s,s.begin(): s.execute(update(models.WorkOrderOrm).values(status='COMP'))
        self.store.reserve_attempt(t)
        with self.assertRaises(FencedOut): self.store.process(t,max_items=1)
        self.assertEqual(self.rows(pm.target),[])

    def test_expired_lease_cannot_commit(self):
        self.debt(); self.add_asset(); t=self.store.claim_due('maintenance_event'); self.store.capture_claim(t)
        self.store.reserve_attempt(t); self.expire(t)
        with self.assertRaises(FencedOut): self.store.process(t,max_items=1)
        self.assertEqual(self.rows(pm.target),[])

    def test_before_commit_disconnect_rolls_back_target_receipt_debt(self):
        self.debt(); self.add_asset()
        def disconnect(s): s.connection().connection.driver_connection.close()
        with self.assertRaises(CaptureError): self.service().run('maintenance_event',before_commit=disconnect)
        self.assertEqual(len(self.rows(dm.version)),1); self.assertEqual(self.rows(pm.target),[])
        q=self.rows(rm.queue)[0]; self.assertEqual(q['phase'],'FAILED')
        self.assertIsNone(self.rows(pm.item,pm.item.c.run_id==q['run_id'])[0]['acked_at'])

    def test_lost_ack_reconciles_without_rewriting(self):
        self.debt(); self.add_asset()
        def lost(): raise RuntimeError('synthetic reply lost')
        with self.assertRaises(RuntimeError): self.service().run('maintenance_event',after_commit=lost)
        before=self.rows(pm.target); q=self.rows(rm.queue)[0]
        self.assertEqual(q['phase'],'PROJECTED')
        self.make_due()
        self.assertEqual(self.service().run('maintenance_event')[0]['state'],'DONE')
        self.assertEqual(before,self.rows(pm.target)); self.assertEqual(self.rows(rm.queue)[0]['attempts'],1)

    def test_crash_after_eligible_transition_resumes(self):
        self.debt(); self.add_asset()
        def crash(action): raise RuntimeError('synthetic stage loss')
        with self.assertRaises(RuntimeError): self.service().run('maintenance_event',after_transition=crash)
        self.assertEqual(self.current()['state'],'ELIGIBLE_FOR_RETRY')
        self.make_due(); self.assertEqual(self.service().run('maintenance_event')[0]['state'],'DONE')
        self.assertEqual(sum(e['action']=='ELIGIBLE' for e in self.rows(dm.event)),1)

    def test_crash_after_resolved_before_done_resumes(self):
        self.debt(); self.add_asset()
        def crash(action):
            if action=='RESOLVED': raise RuntimeError('synthetic done gap')
        with self.assertRaises(RuntimeError): self.service().run('maintenance_event',after_transition=crash)
        self.assertEqual(self.current()['state'],'RESOLVED')
        self.make_due(); self.assertEqual(self.service().run('maintenance_event')[0]['state'],'DONE')
        self.assertEqual(sum(e['action']=='RESOLVED' for e in self.rows(dm.event)),1)

    def test_drifted_target_refuses_resolution(self):
        self.debt(); self.add_asset()
        def lost(): raise RuntimeError('synthetic')
        with self.assertRaises(RuntimeError): self.service().run('maintenance_event',after_commit=lost)
        with self.db.session() as s,s.begin():
            s.execute(update(mart_models.MaintenanceEventMartOrm).values(status='DRIFT'))
        self.make_due()
        with self.assertRaises(CaptureError): self.service().run('maintenance_event')
        self.assertNotEqual(self.current()['state'],'RESOLVED')

    def test_budget_change_rejected_not_auto_increased(self):
        self.debt(); changed=self.fresh(replay_policy=ReplayPolicy(max_attempts=4))
        self.assertEqual(changed.due('maintenance_event'),[])
        ticket=changed.capture('maintenance_event')
        with self.assertRaises(CaptureError): changed.register(ticket,self.current()['id'])

    def test_readiness_probe_limit_blocks_without_b2_poison_attempt(self):
        self.store=self.fresh(replay_policy=ReplayPolicy(max_probes=1))
        self.debt(); self.service().run('maintenance_event')
        self.assertEqual(self.rows(rm.queue)[0]['reason'],'PROBE_LIMIT')
        self.assertEqual(self.current()['attempts'],1)

    def test_actual_write_poison_budget_and_backoff(self):
        self.store=self.fresh(replay_policy=ReplayPolicy(max_attempts=1)); self.debt(); self.add_asset()
        with patch.object(self.store.writer,'persist_in_session',side_effect=RuntimeError('synthetic')):
            with self.assertRaises(CaptureError): self.service().run('maintenance_event')
        q=self.rows(rm.queue)[0]
        self.assertEqual((q['phase'],q['attempts'],q['reason']),('BLOCKED',1,'ATTEMPT_LIMIT'))
        self.assertEqual(self.store.due('maintenance_event'),[])

    def test_due_keyset_fairness_and_exact_query(self):
        self.add_wo('BSR001'); self.add_wo('BSR002')
        t=self.store.capture('maintenance_event'); self.store.process(t)
        for v in self.rows(dm.version): self.store.register(t,v['id'])
        self.store.release(t)
        rows=self.store.due('maintenance_event',limit=1)
        more=self.store.due('maintenance_event',limit=1,after=(rows[0]['due_at'],rows[0]['family_id']))
        self.assertEqual(len(more),1); self.assertNotEqual(more[0]['family_id'],rows[0]['family_id'])
        self.service().run('maintenance_event')
        self.assertEqual(self.store.due('maintenance_event')[0]['family_id'],more[0]['family_id'])

    def test_only_exact_source_id_is_captured(self):
        self.debt(); self.add_asset(); self.add_wo('BSR-UNRELATED')
        queries=[]
        from sqlalchemy import event
        def record(conn,cursor,statement,parameters,context,many):
            if 'FROM work_order' in statement: queries.append((statement,parameters))
        event.listen(self.db.engine,'before_cursor_execute',record)
        try: result=self.service().run('maintenance_event')
        finally: event.remove(self.db.engine,'before_cursor_execute',record)
        self.assertTrue(queries)
        self.assertTrue(all('WHERE work_order.id =' in sql for sql,_ in queries))
        self.assertEqual(self.store.inspect(result[0]['run_id'])['item_count'],1)

    def test_missing_index_refused(self):
        with self.db.session() as s,s.begin(): s.execute(text('DROP INDEX replay_due'))
        with self.assertRaises(CaptureError): self.fresh()

    def test_guard_drift_refused(self):
        with self.db.session() as s,s.begin():
            s.execute(text('ALTER TABLE mart_replay_queue DISABLE TRIGGER replay_queue_guard'))
        with self.assertRaises(CaptureError): self.fresh()

    def test_queue_audit_and_deletion_protected(self):
        self.debt()
        with self.assertRaises(DBAPIError):
            with self.db.session() as s,s.begin(): s.execute(delete(rm.queue))
        with self.assertRaises(DBAPIError):
            with self.db.session() as s,s.begin(): s.execute(text('TRUNCATE mart_replay_event'))

    def test_b2_history_cap_refuses_before_target_write(self):
        self.store=self.fresh(ledger_limits=LedgerLimits(max_versions=1))
        self.debt(); self.add_asset(); self.service().run('maintenance_event')
        self.assertEqual(self.rows(pm.target),[])
        self.assertEqual(self.rows(rm.queue)[0]['reason'],'HISTORY_LIMIT')

    def test_initial_blocked_mapping_never_enrolled_or_retried(self):
        self.add_asset(sources={'maximo':{'assetnum':'A','siteid':'BSR','orgid':'IP','changedate':'bad'}})
        t=self.store.capture('asset_master'); self.store.process(t)
        self.assertEqual(self.current()['state'],'BLOCKED_NEEDS_REVIEW')
        with self.assertRaises(CaptureError): self.store.register(t,self.current()['id'])
        self.assertEqual(self.store.due('asset_master'),[])

    def test_new_invalid_mapping_readiness_blocks_without_target(self):
        self.debt(domain='asset_master',key='A')
        with self.db.session() as s,s.begin():
            s.execute(update(models.EquipmentOrm).values(sources={'maximo':{
                'assetnum':'A','siteid':'BSR','orgid':'IP','changedate':'bad'}}))
        result=self.service().run('asset_master')
        self.assertEqual(result[0]['state'],'BLOCKED')
        self.assertEqual(self.rows(pm.target),[])
        self.assertEqual(self.rows(rm.queue)[0]['attempts'],0)

    def test_scope_repair_exact_id_and_asset_mapping(self):
        self.debt(domain='asset_master',key='A')
        with self.db.session() as s,s.begin():
            s.execute(update(models.EquipmentOrm).values(sources={'maximo':{
                'assetnum':'A','siteid':'BSR','orgid':'IP'}}))
        self.assertEqual(self.service().run('asset_master')[0]['state'],'DONE')
        self.assertEqual(self.current()['scope_proof'],'PROVEN')
        self.assertEqual(self.current()['state'],'RESOLVED')

    def test_backdated_source_timestamp_preserved(self):
        from datetime import datetime, timezone
        date=datetime(2000,1,1,tzinfo=timezone.utc)
        self.add_wo()
        with self.db.session() as s,s.begin(): s.execute(update(models.WorkOrderOrm).values(source_changed_at=date))
        t=self.store.capture('maintenance_event'); self.store.process(t)
        self.store.register(t,self.current()['id']); self.store.release(t)
        self.add_asset(); out=self.service().run('maintenance_event')
        payload=self.rows(pm.item,pm.item.c.run_id==out[0]['run_id'])[0]['payload']
        self.assertEqual(payload['source_changed_at'],date.isoformat())

    def test_claim_crash_before_capture_can_resume(self):
        self.debt(); self.add_asset(); first=self.store.claim_due('maintenance_event')
        self.make_due()
        out=self.service().run('maintenance_event')
        self.assertEqual(out[0]['run_id'],first.run_id)
        self.assertEqual(out[0]['state'],'DONE')
        self.assertEqual(len(self.rows(pm.item,pm.item.c.run_id==first.run_id)),1)

    def test_ambiguous_reserved_attempt_resumes_without_double_charge(self):
        self.debt(); self.add_asset(); t=self.store.claim_due('maintenance_event')
        self.store.capture_claim(t); self.store.reserve_attempt(t)
        self.make_due(); self.service().run('maintenance_event')
        self.assertEqual(self.rows(rm.queue)[0]['attempts'],1)

    def test_failed_write_retries_same_manifest_with_bounded_new_reservation(self):
        self.debt(); self.add_asset()
        with patch.object(self.store.writer,'persist_in_session',side_effect=RuntimeError('fixture')):
            with self.assertRaises(CaptureError): self.service().run('maintenance_event')
        q=self.rows(rm.queue)[0]; self.assertEqual(q['attempts'],1)
        self.assertEqual(self.service().run('maintenance_event'),[])
        self.make_due(); out=self.service().run('maintenance_event')
        self.assertEqual(out[0]['run_id'],q['run_id']); self.assertEqual(self.rows(rm.queue)[0]['attempts'],2)

    def test_newer_generation_protected_from_old_sealed_replay(self):
        self.debt(); self.add_asset(); old=self.store.claim_due('maintenance_event')
        self.store.capture_claim(old); self.store.reserve_attempt(old); self.expire(old)
        with self.db.session() as s,s.begin(): s.execute(update(models.WorkOrderOrm).values(status='COMP'))
        newer=self.store.capture('maintenance_event'); self.store.process(newer)
        target=self.rows(pm.target)
        with self.assertRaises(FencedOut): self.store.process(old,max_items=1)
        with self.assertRaises(FencedOut): self.store.resolve_claim(old)
        self.assertEqual(target,self.rows(pm.target))

    def test_exhausted_replay_journal_prevents_claim(self):
        self.store=self.fresh(replay_policy=ReplayPolicy(max_events=16,max_probes=64))
        self.debt()
        for _ in range(3):
            self.service().run('maintenance_event'); self.make_due()
        with self.assertRaises(LedgerLimit): self.service().run('maintenance_event')
        self.assertEqual(self.current()['state'],'OPEN'); self.assertEqual(self.rows(pm.target),[])

    def test_policy_expired_refuses_due_without_discarding_queue(self):
        from datetime import datetime, timezone
        self.debt(); original=self.rows(rm.queue)
        expired=self.fresh(ledger_limits=LedgerLimits(policy_expires_at=datetime(2000,1,1,tzinfo=timezone.utc)))
        with self.assertRaises(LedgerLimit): expired.due('maintenance_event')
        self.assertEqual(original,self.rows(rm.queue))

    def test_missing_006_rejected_and_duplicate_006_refused(self):
        with self.assertRaises(psycopg.errors.DuplicateTable):
            with self.db.engine.connect() as c:
                c.connection.driver_connection.execute(MIGRATION.read_text())
        with self.db.session() as s,s.begin():
            s.execute(text('ALTER TABLE mart_replay_queue DROP COLUMN reason'))
        with self.assertRaises(CaptureError): self.fresh()

    def test_b2_can_complete_new_full_capture_after_targeted_resolution(self):
        self.debt(); self.add_asset(); self.service().run('maintenance_event')
        new=self.store.capture('maintenance_event')
        self.assertEqual(self.store.process(new)['status'],'COMPLETE')
        self.assertEqual(self.rows(pm.lease)[0]['last_complete_run'],new.run_id)

    def test_missing_canonical_asset_is_soft_reference_during_recovery(self):
        self.debt(); self.add_asset(); self.service().run('maintenance_event')
        self.assertEqual(self.rows(mart_models.AssetMasterMartOrm),[])
        self.assertEqual(len(self.rows(mart_models.MaintenanceEventMartOrm)),1)

    def test_sql_forbids_forged_done_and_attempt_jumps(self):
        self.debt(); t=self.store.claim_due('maintenance_event')
        for values in ({'phase':'DONE'},{'attempts':10}):
            with self.subTest(values=values),self.assertRaises(DBAPIError):
                with self.db.session() as s,s.begin():
                    q=dict(s.execute(select(rm.queue)).mappings().one())
                    self.store._change(s,t,q,values.get('phase',q['phase']),q['reason'],
                                       **{k:v for k,v in values.items() if k!='phase'})

    def test_stage_and_audit_roll_back_together(self):
        self.debt(); t=self.store.claim_due('maintenance_event')
        before=self.rows(rm.event)
        with self.assertRaises(DBAPIError):
            with self.db.session() as s,s.begin():
                s.execute(update(rm.queue).values(revision=rm.queue.c.revision+1))
        self.assertEqual(before,self.rows(rm.event))

    def test_receipt_reconciliation_dependency_kind(self):
        self.debt(); self.add_asset()
        # B2 successful same-domain re-capture creates a fresh receipt-pending version.
        t=self.store.capture('maintenance_event'); self.store.process(t)
        v=self.current(); self.assertEqual(self.rows(dm.dependency,dm.dependency.c.obligation_id==v['id'])[0]['kind'],
                                          'RECEIPT_RECONCILIATION')
        self.store.release(t)
        # Existing B3 enrollment is deliberately not silently repointed by another writer.
        self.assertEqual(self.store.due('maintenance_event'),[])
        with self.assertRaises(CaptureError): self.store.register(self.store.capture('maintenance_event'),v['id'])

    def test_mapping_input_dependency_can_be_repaired(self):
        self.add_asset(sources={'maximo':{'assetnum':'','siteid':'BSR','orgid':'IP'}})
        t=self.store.capture('asset_master'); self.store.process(t)
        self.store.register(t,self.current()['id']); self.store.release(t)
        with self.db.session() as s,s.begin():
            s.execute(update(models.EquipmentOrm).values(sources={'maximo':{'assetnum':'A','siteid':'BSR','orgid':'IP'}}))
        self.assertEqual(self.service().run('asset_master')[0]['state'],'DONE')

    def receipt_pending(self):
        self.add_wo(); t=self.store.capture('maintenance_event'); self.store.process(t); self.store.release(t)
        self.add_asset(); ready=self.store.capture('maintenance_event'); self.store.process(ready)
        self.store.register(ready,self.current()['id']); self.store.release(ready)

    def test_existing_receipt_pending_same_fingerprint_resolves(self):
        self.receipt_pending(); v=self.current()
        self.assertEqual(self.rows(dm.dependency,dm.dependency.c.obligation_id==v['id'])[0]['kind'],'RECEIPT_RECONCILIATION')
        self.assertEqual(self.service().run('maintenance_event')[0]['state'],'DONE')
        self.assertEqual(self.current()['id'],v['id'])
        self.assertEqual(self.current()['attempts'],2)

    def test_b2_poison_boundary_cannot_be_reached_by_successful_replay(self):
        self.store=self.fresh(ledger_limits=LedgerLimits(max_attempts=2),replay_policy=ReplayPolicy(max_attempts=2))
        self.receipt_pending(); v=self.current()
        self.assertEqual(self.service().run('maintenance_event')[0]['state'],'BLOCKED')
        self.assertEqual(self.current(),v)
        self.assertEqual(self.rows(rm.queue)[0]['attempts'],0)

    def test_source_query_locks_only_required_equipment(self):
        self.debt(); self.add_asset(); self.add_asset('UNRELATED')
        queries=[]
        from sqlalchemy import event
        def record(conn,cursor,statement,parameters,context,many):
            if statement.startswith('SELECT equipment.id') and 'FOR SHARE' in statement: queries.append(statement)
        event.listen(self.db.engine,'before_cursor_execute',record)
        try: self.service().run('maintenance_event')
        finally: event.remove(self.db.engine,'before_cursor_execute',record)
        self.assertEqual(len(queries),1)
        self.assertIn('WHERE equipment.id =',queries[0])

    def test_due_selection_index_supports_ordered_bounded_range(self):
        from sqlalchemy.dialects import postgresql
        self.debt()
        query=self.store._due_query('maintenance_event',1)
        sql=str(query.compile(dialect=postgresql.dialect(),compile_kwargs={'literal_binds':True}))
        with self.db.session() as s,s.begin():
            s.execute(text('SET LOCAL enable_seqscan=off'))
            plan='\n'.join(s.scalars(text('EXPLAIN '+sql)))
        self.assertIn('replay_due',plan)
        self.assertIn('due_at <= statement_timestamp()',plan)

    def test_invocation_deadline_after_projection_retains_unresolved_receipt(self):
        from src.repositories.replay_store import INVOCATION_DEADLINE
        from src.repositories.projection_store import BudgetExceeded
        self.debt(); self.add_asset()
        def elapsed(): INVOCATION_DEADLINE.set(0)
        with self.assertRaises(BudgetExceeded): self.service().run('maintenance_event',after_commit=elapsed)
        self.assertEqual(self.rows(rm.queue)[0]['phase'],'PROJECTED')
        self.assertNotEqual(self.current()['state'],'RESOLVED')
        self.make_due()
        self.assertEqual(self.service().run('maintenance_event')[0]['state'],'DONE')
