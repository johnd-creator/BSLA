"""Executed MVCC/atomic/fencing proofs in runner-owned synthetic PG only."""
import hashlib
import psycopg
from pathlib import Path
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from sqlalchemy import create_engine, event, insert, select, text, update, delete, func
from sqlalchemy.exc import DBAPIError
import fixture_context
from src.config import DbConfig
from src.repositories.database import Database
from src.repositories import models, mart_models, projection_models as pm
from src.repositories.projection_store import (ProjectionStore, Budget, BudgetExceeded,
    CaptureError, FencedOut, fingerprint)
from src.services.mart import MartWriter
from src.services.canonical import CanonicalCollection
from src.adapters.maximo.canonical_mappers import asset_master_from_payload

NOW = datetime(2026, 10, 1, tzinfo=timezone.utc)
MIGRATION = Path(__file__).resolve().parents[1]/'migrations/004_projection_capture_candidate.sql'


class PostgreSQLCaptureTest(unittest.TestCase):
    def setUp(self):
        if fixture_context.url is None:
            raise AssertionError('private disposable-cluster runner required; no environment fallback')
        self.schema = 'b1_fixture_' + uuid.uuid4().hex
        engine = create_engine(fixture_context.url)
        with engine.begin() as c:
            self.assertEqual(c.scalar(text('SELECT current_database()')),'nadi_aud02b_disposable')
            self.assertEqual(c.scalar(text('SELECT current_user')),'nadi_b1_fixture')
            self.assertEqual(c.scalar(text('SELECT system_identifier::text FROM pg_control_system()')),
                             fixture_context.identity['system_id'])
            c.execute(text('CREATE SCHEMA '+self.schema))
        engine.dispose()
        self.db = Database(DbConfig(fixture_context.url))
        @event.listens_for(self.db.engine, 'connect')
        def scope(conn, _):
            conn.execute('SET search_path TO '+self.schema)
            conn.commit()
        self.db.create_all()  # Existing schemas only, fixture database only.
        with self.db.engine.connect() as c:
            raw = c.connection.driver_connection
            raw.execute(MIGRATION.read_text())
            raw.commit()
        self.store = self.fresh()
        with self.db.session() as s, s.begin():
            s.add(models.SyncCursorOrm(scope='mxapiasset',watermark=NOW,rows_seen=7,updated_at=NOW))
        self.cursor_before = self.cursors()

    def tearDown(self):
        self.assertEqual(self.cursors(), self.cursor_before)
        self.db.engine.dispose()  # Retain all evidence in OWN cluster until runner cleanup.

    def fresh(self, **kwargs):
        return ProjectionStore(self.db,enabled=True,exclusive_writer=True,**kwargs)

    def cursors(self):
        with self.db.session() as s:
            return [tuple(r) for r in s.execute(select(models.SyncCursorOrm.__table__))]

    def add_asset(self, key='A', **kwargs):
        defaults = dict(description='SYNTHETIC '+key, unit='CS01',status='OPERATING',
            source_changed_at=NOW,sources={'maximo':{'siteid':'BSR','orgid':'IP','assetnum':key}})
        defaults.update(kwargs)
        with self.db.session() as s, s.begin():
            s.add(models.EquipmentOrm(id=key, **defaults))

    def add_wo(self, key='BSR-001', eq='A', **kwargs):
        data = dict(equipment_id=eq,status='CAN',work_type='PM',source_changed_at=NOW)
        data.update(kwargs)
        with self.db.session() as s, s.begin():
            s.add(models.WorkOrderOrm(id=key,**data))

    def rows(self, table, *where):
        with self.db.session() as s:
            return [dict(r) for r in s.execute(select(table).where(*where)).mappings()]

    def expire(self, ticket):
        # Deterministic fixture-only expiry, not a runtime lease extension.
        with self.db.session() as s, s.begin():
            s.execute(update(pm.lease).where(pm.lease.c.domain==ticket.domain)
                      .values(lease_until=NOW))

    def test_t03_mvcc_insert_between_pages(self):
        for k in ('B','D','F'): self.add_asset(k)
        def mutate(n):
            if n == 1:
                self.add_asset('A',source_changed_at=NOW-timedelta(days=100))
                self.add_asset('E')
        store = self.fresh(budget=Budget(page=1))
        t = store.capture('asset_master',after_page=mutate)
        self.assertEqual([r['source_id'] for r in self.rows(pm.item)],['B','D','F'])
        self.assertEqual(store.process(t)['status'],'COMPLETE')
        store.release(t)
        next_t = store.capture('asset_master')
        self.assertEqual(store.inspect(next_t.run_id)['item_count'],5)

    def test_t04_mutation_and_later_max_not_certified(self):
        self.add_asset('A'); self.add_asset('B')
        def mutate(n):
            if n == 1:
                with self.db.session() as s, s.begin():
                    s.execute(update(models.EquipmentOrm).where(models.EquipmentOrm.id=='B')
                              .values(description='NEW',source_changed_at=NOW+timedelta(days=200)))
        store = self.fresh(budget=Budget(page=1))
        t = store.capture('asset_master',after_page=mutate)
        store.process(t)
        self.assertEqual(self.rows(mart_models.AssetMasterMartOrm.__table__)[1]['description'],'SYNTHETIC B')
        old_fp = self.rows(pm.item,pm.item.c.source_id=='B')[0]['fingerprint']
        store.release(t); new = store.capture('asset_master'); store.process(new)
        self.assertNotEqual(old_fp,self.rows(pm.item,pm.item.c.run_id==new.run_id,
                                            pm.item.c.source_id=='B')[0]['fingerprint'])

    def test_t05_rollback_before_commit_is_atomic(self):
        self.add_asset(); t=self.store.capture('asset_master')
        def crash(_session): raise RuntimeError('synthetic crash boundary')
        with self.assertRaises(RuntimeError): self.store.process(t,before_commit=crash)
        self.assertEqual(self.rows(mart_models.AssetMasterMartOrm.__table__),[])
        self.assertIsNone(self.rows(pm.item)[0]['disposition'])
        self.assertEqual(self.store.inspect(t.run_id)['continuation'],0)
        self.assertEqual(self.rows(pm.target),[])

    def test_t05_ambiguous_commit_resume_does_not_duplicate(self):
        self.add_asset(); t=self.store.capture('asset_master')
        def lost_reply(): raise RuntimeError('synthetic lost acknowledgment')
        with self.assertRaises(RuntimeError): self.store.process(t,after_commit=lost_reply)
        receipt=self.rows(pm.item)[0]
        created=self.rows(mart_models.AssetMasterMartOrm.__table__)[0]['mart_created_at']
        self.assertEqual(self.store.inspect(t.run_id)['continuation'],1)
        self.store.release(t)
        restarted=self.fresh(); resumed=restarted.resume('asset_master',t.run_id)
        self.assertEqual(restarted.process(resumed)['status'],'COMPLETE')
        self.assertEqual(self.rows(pm.item)[0],receipt)
        self.assertEqual(self.rows(mart_models.AssetMasterMartOrm.__table__)[0]['mart_created_at'],created)

    def test_t06_restart_ordinal_continuation(self):
        for k in ('A','B','C'): self.add_asset(k)
        t=self.store.capture('asset_master')
        self.assertEqual(self.store.process(t,max_items=1)['continuation'],1)
        self.store.release(t)
        restarted=self.fresh(); resumed=restarted.resume('asset_master',t.run_id)
        self.assertEqual(restarted.process(resumed)['status'],'COMPLETE')
        self.assertEqual(len(self.rows(mart_models.AssetMasterMartOrm.__table__)),3)
        with self.assertRaises(FencedOut): self.store.process(t)

    def test_t10_null_source_timestamp_preserved(self):
        self.add_asset(source_changed_at=None)
        t=self.store.capture('asset_master'); self.store.process(t)
        self.assertIsNone(self.rows(pm.item)[0]['payload']['changedate'])
        self.assertIsNone(self.rows(mart_models.AssetMasterMartOrm.__table__)[0]['source_updated_at'])

    def test_t11_identical_timestamps_with_small_pages(self):
        for k in reversed(('A','B','C','D','E')): self.add_asset(k)
        store=self.fresh(budget=Budget(page=2)); t=store.capture('asset_master')
        self.assertEqual([r['source_id'] for r in self.rows(pm.item)],['A','B','C','D','E'])
        self.assertEqual(store.process(t)['continuation'],5)

    def test_t14_row_budget_aborts_unsealed_capture(self):
        self.add_asset('A'); self.add_asset('B')
        with self.assertRaises(BudgetExceeded): self.fresh(budget=Budget(rows=1,page=1)).capture('asset_master')
        r=self.rows(pm.run)[0]
        self.assertEqual((r['sealed'],r['status'],r['continuation']),(False,'FAILED',0))
        self.assertEqual(self.rows(pm.item),[])
        self.assertIsNone(self.rows(pm.lease)[0]['last_complete_run'])

    def test_t14_byte_budget_aborts(self):
        self.add_asset()
        with self.assertRaises(BudgetExceeded): self.fresh(budget=Budget(bytes=1)).capture('asset_master')
        self.assertEqual(self.rows(pm.item),[])

    def test_t14_capture_time_budget_aborts(self):
        self.add_asset()
        with patch('src.repositories.projection_store.time.monotonic',side_effect=[0,0,99]):
            with self.assertRaises(BudgetExceeded): self.store.capture('asset_master')
        self.assertEqual(self.rows(pm.item),[])

    def test_t14_process_budget_retains_partial(self):
        for k in ('A','B'): self.add_asset(k)
        t=self.store.capture('asset_master'); state=self.store.process(t,max_items=1)
        self.assertEqual((state['status'],state['continuation']),('PARTIAL',1))
        self.assertIsNone(self.rows(pm.lease)[0]['last_complete_run'])

    def test_t17_backdated_changes_next_manifest(self):
        self.add_asset(); t=self.store.capture('asset_master'); self.store.process(t); self.store.release(t)
        old=self.rows(pm.item)[0]['fingerprint']
        with self.db.session() as s, s.begin():
            s.execute(update(models.EquipmentOrm).values(description='BACKDATED',source_changed_at=NOW-timedelta(days=900)))
        new=self.store.capture('asset_master'); self.store.process(new)
        self.assertNotEqual(self.rows(pm.item,pm.item.c.run_id==new.run_id)[0]['fingerprint'],old)
        self.assertEqual(self.rows(mart_models.AssetMasterMartOrm.__table__)[0]['description'],'BACKDATED')

    def test_t18_stale_writer_cannot_overwrite_new_generation(self):
        self.add_asset(); old=self.store.capture('asset_master'); self.expire(old)
        with self.db.session() as s, s.begin():
            s.execute(update(models.EquipmentOrm).values(description='NEW'))
        current=self.store.capture('asset_master'); self.store.process(current)
        with self.assertRaises(FencedOut): self.store.process(old)
        with self.assertRaises(FencedOut): self.store.resume('asset_master',old.run_id)
        self.assertEqual(self.rows(mart_models.AssetMasterMartOrm.__table__)[0]['description'],'NEW')
        self.assertIsNone(self.rows(pm.item,pm.item.c.run_id==old.run_id)[0]['disposition'])

    def test_t18_live_lease_refuses_second_owner(self):
        self.add_asset(); self.store.capture('asset_master')
        with self.assertRaises(FencedOut): self.fresh().capture('asset_master')

    def test_t18_expiry_before_commit_rolls_back_everything(self):
        self.add_asset(); t=self.store.capture('asset_master')
        def expire_inside(session):
            session.execute(update(pm.lease).values(lease_until=NOW))
        with self.assertRaises(FencedOut): self.store.process(t,before_commit=expire_inside)
        self.assertEqual(self.rows(pm.target),[])
        self.assertEqual(self.rows(mart_models.AssetMasterMartOrm.__table__),[])

    def test_t01_t12_missing_equipment_blocks_complete(self):
        self.add_asset(); self.add_wo('BSR-OLD','MISSING',source_changed_at=NOW-timedelta(days=100))
        self.add_wo('BSR-NEW','A')
        t=self.store.capture('maintenance_event'); state=self.store.process(t)
        self.assertEqual((state['continuation'],state['status']),(2,'PARTIAL'))
        self.assertEqual({r['disposition'] for r in self.rows(pm.item)}, {'PROJECTED','DEFERRED'})
        self.assertIsNone(self.rows(pm.lease)[0]['last_complete_run'])
        self.assertEqual(self.rows(mart_models.MaintenanceEventMartOrm.__table__)[0]['status'],'CAN')

    def test_t12_historical_unresolved_input_not_erased_by_new_run(self):
        self.add_wo(eq='MISSING'); old=self.store.capture('maintenance_event'); self.store.process(old)
        self.store.release(old)
        with self.db.session() as s, s.begin(): s.execute(delete(models.WorkOrderOrm))
        new=self.store.capture('maintenance_event')
        self.assertEqual(self.store.process(new)['status'],'PARTIAL')

    def test_unknown_scope_deferred_not_expected_exclusion(self):
        self.add_asset(sources={'maximo':{'assetnum':'A'}})
        t=self.store.capture('asset_master'); self.assertEqual(self.store.process(t)['status'],'PARTIAL')
        self.assertEqual(self.rows(pm.item)[0]['reason'],'UNPROVEN_SCOPE')

    def test_expected_prefix_exclusion_has_receipt(self):
        self.add_wo('OTHER-1','MISSING'); t=self.store.capture('maintenance_event')
        self.assertEqual(self.store.process(t)['status'],'COMPLETE')
        self.assertEqual(self.rows(pm.item)[0]['disposition'],'EXPECTED_EXCLUSION')

    def test_sealed_membership_input_and_receipts_immutable(self):
        self.add_asset(); t=self.store.capture('asset_master')
        for query in (update(pm.item).values(payload={}),
                      insert(pm.item).values(run_id=t.run_id,ordinal=2,source_id='X',fingerprint='0'*64,payload={}),
                      update(pm.run).values(manifest_digest='0'*64),delete(pm.item)):
            with self.subTest(query=type(query).__name__), self.assertRaises(DBAPIError):
                with self.db.session() as s,s.begin(): s.execute(query)
        self.store.process(t)
        with self.assertRaises(DBAPIError):
            with self.db.session() as s,s.begin(): s.execute(update(pm.item).values(reason='changed'))

    def test_database_refuses_continuation_without_receipts(self):
        self.add_asset(); self.store.capture('asset_master')
        with self.assertRaises(DBAPIError):
            with self.db.session() as s,s.begin(): s.execute(update(pm.run).values(continuation=1))

    def test_prior_complete_not_refreshed_by_incomplete_attempt(self):
        self.add_asset(); t=self.store.capture('asset_master'); self.store.process(t); self.store.release(t)
        before=self.rows(pm.lease)[0]['last_complete_at']
        self.add_asset('BAD',sources={}); new=self.store.capture('asset_master')
        self.assertEqual(self.store.process(new)['status'],'PARTIAL')
        state=self.rows(pm.lease)[0]
        self.assertEqual((state['last_complete_at'],state['last_complete_run']),(before,t.run_id))
        self.assertEqual(state['latest_run'],new.run_id)

    def test_legacy_target_drift_refused_before_next_write(self):
        self.add_asset(); t=self.store.capture('asset_master'); self.store.process(t); self.store.release(t)
        with self.db.session() as s,s.begin(): s.execute(update(mart_models.AssetMasterMartOrm).values(description='UNFENCED'))
        new=self.store.capture('asset_master')
        with self.assertRaises(FencedOut): self.store.process(new)
        self.assertIsNone(self.rows(pm.item,pm.item.c.run_id==new.run_id)[0]['disposition'])

    def test_acknowledged_target_drift_cannot_certify_complete(self):
        self.add_asset(); t=self.store.capture('asset_master'); self.store.process(t,max_items=1)
        with self.db.session() as s,s.begin(): s.execute(update(mart_models.AssetMasterMartOrm).values(description='UNFENCED'))
        with self.assertRaises(FencedOut): self.store.process(t)
        self.assertIsNone(self.rows(pm.lease)[0]['last_complete_run'])

    def test_schema_guard_drift_refuses_candidate(self):
        with self.db.session() as s,s.begin():
            s.execute(text('ALTER TABLE mart_capture_item DISABLE TRIGGER mart_capture_item_guard'))
        with self.assertRaises(CaptureError): self.fresh()

    def test_duplicate_migration_refused_without_rewriting(self):
        with self.assertRaises(psycopg.errors.DuplicateTable):
            with self.db.engine.connect() as c: c.connection.driver_connection.execute(MIGRATION.read_text())
        self.assertEqual(self.rows(pm.run),[])

    def test_private_source_keys_and_person_fields_not_captured(self):
        self.add_asset(sources={'maximo':{'siteid':'BSR','orgid':'IP','assetnum':'A',
            'password':'SYNTHETIC_PRIVATE','raw_payload':{'x':1}}})
        self.add_wo()
        with self.db.session() as s,s.begin(): s.execute(update(models.WorkOrderOrm).values(reported_by='SYNTHETIC_PERSON'))
        self.store.capture('asset_master'); self.store.capture('maintenance_event')
        payload=str(self.rows(pm.item))
        self.assertNotIn('SYNTHETIC_PRIVATE',payload); self.assertNotIn('SYNTHETIC_PERSON',payload)
        self.assertNotIn('raw_payload',payload)

    def test_local_equipment_normalization_matches_existing_mapper(self):
        self.add_asset(); self.add_wo(eq=' a ')
        t=self.store.capture('maintenance_event'); self.assertEqual(self.store.process(t)['status'],'COMPLETE')
        self.assertTrue(self.rows(mart_models.MaintenanceEventMartOrm.__table__)[0]['equipment_id'].endswith(':A'))

    def test_genuine_domain_lock_conflict_cannot_write(self):
        from concurrent.futures import ThreadPoolExecutor
        self.add_asset(); ticket=self.store.capture('asset_master')
        with self.db.session() as s, s.begin():
            s.execute(select(pm.lease).with_for_update()).one()
            with ThreadPoolExecutor(max_workers=1) as pool:
                future=pool.submit(self.fresh().process,ticket)
                with self.assertRaises(DBAPIError): future.result(timeout=5)
        self.assertEqual(self.rows(mart_models.AssetMasterMartOrm.__table__),[])
        self.assertIsNone(self.rows(pm.item)[0]['disposition'])

    def test_oversized_scalar_fails_closed_without_persisting_input(self):
        self.add_asset(description='X'*9000)
        with self.assertRaises(BudgetExceeded): self.store.capture('asset_master')
        self.assertEqual(self.rows(pm.item),[])

    def test_mapper_failure_keeps_unprocessed_and_no_complete(self):
        self.add_asset(sources={'maximo':{'assetnum':'','siteid':'BSR','orgid':'IP'}})
        ticket=self.store.capture('asset_master')
        with self.assertRaises(ValueError): self.store.process(ticket)
        self.assertEqual(self.store.inspect(ticket.run_id)['continuation'],0)
        self.assertIsNone(self.rows(pm.item)[0]['disposition'])
        self.assertIsNone(self.rows(pm.lease)[0]['last_complete_run'])

    def test_schema_type_drift_refuses_candidate(self):
        with self.db.session() as s,s.begin():
            s.execute(text('ALTER TABLE mart_capture_item ALTER COLUMN source_id TYPE VARCHAR(61)'))
        with self.assertRaises(CaptureError): self.fresh()

    def test_empty_snapshot_is_explicitly_complete(self):
        ticket=self.store.capture('asset_master')
        state=self.store.process(ticket)
        self.assertEqual((state['item_count'],state['continuation'],state['status']),(0,0,'COMPLETE'))

    def test_unchanged_new_generation_preserves_target_created_time(self):
        self.add_asset(); ticket=self.store.capture('asset_master'); self.store.process(ticket)
        created=self.rows(mart_models.AssetMasterMartOrm.__table__)[0]['mart_created_at']
        self.store.release(ticket)
        new=self.store.capture('asset_master'); self.store.process(new)
        self.assertEqual(self.rows(pm.item,pm.item.c.run_id==new.run_id)[0]['disposition'],'UNCHANGED')
        self.assertEqual(self.rows(mart_models.AssetMasterMartOrm.__table__)[0]['mart_created_at'],created)

    def test_real_connection_loss_before_commit_rolls_back_target_receipt(self):
        self.add_asset(); ticket=self.store.capture('asset_master')
        def disconnect(session):
            session.connection().connection.driver_connection.close()
        with self.assertRaises(DBAPIError): self.store.process(ticket,before_commit=disconnect)
        self.assertEqual(self.rows(mart_models.AssetMasterMartOrm.__table__),[])
        self.assertEqual(self.rows(pm.target),[])
        self.assertIsNone(self.rows(pm.item)[0]['acked_at'])
        self.assertEqual(self.store.inspect(ticket.run_id)['continuation'],0)

    def test_writer_rejection_does_not_acknowledge(self):
        from src.services.mart import ScopeViolation
        self.add_asset(); ticket=self.store.capture('asset_master')
        invalid=asset_master_from_payload({'assetnum':'A','siteid':'BSR','orgid':'IP'})
        invalid['site_code']='OTHER'
        with patch('src.repositories.projection_store.map_input',return_value=(invalid,None,None)):
            with self.assertRaises(ScopeViolation): self.store.process(ticket)
        self.assertIsNone(self.rows(pm.item)[0]['acked_at'])
        self.assertEqual(self.rows(mart_models.AssetMasterMartOrm.__table__),[])

    def test_seal_digest_reconciles_ordered_inputs(self):
        from src.repositories.projection_store import encode
        self.add_asset('A'); self.add_asset('B')
        ticket=self.store.capture('asset_master')
        digest=hashlib.sha256()
        for item in self.rows(pm.item):
            digest.update(encode([item['ordinal'],item['source_id'],item['fingerprint']]))
        state=self.store.inspect(ticket.run_id)
        self.assertEqual(state['manifest_digest'],digest.hexdigest())
        self.assertTrue(state['sealed']); self.assertIsNotNone(state['snapshot'])

    def test_nested_allowed_field_is_not_persisted_as_raw_payload(self):
        self.add_asset(sources={'maximo':{'siteid':'BSR','orgid':'IP','assetnum':'A',
            'description':{'unexpected_private':'SYNTHETIC'}}})
        with self.assertRaises(CaptureError): self.store.capture('asset_master')
        self.assertEqual(self.rows(pm.item),[])
