"""Synthetic bounded asset recovery tests; no production source."""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from unittest import TestCase
from unittest.mock import patch
from sqlalchemy import select
from src.config import DbConfig
from src.repositories.database import Database
from src.repositories.store import CollectorStore
from src.repositories import models as orm
from src.repositories.asset_references import AssetReferenceStore, RUN_OBJECT
from src.services.asset_references import collect_asset_references
from src.adapters.maximo.oslc_client import OslcPaginationLimitError

NOW = datetime(2026, 11, 6, tzinfo=timezone.utc)

def asset(identity="A1", **kw):
    return {"assetnum":identity,"siteid":"BSR","orgid":"IP","eq11":"CS01", "status":"OPERATING",
            "description":"synthetic", "changedate":"2020-01-01T00:00:00Z", **kw}

class Client:
    def __init__(self, rows=None, error=None):
        self.rows = [asset()] if rows is None else rows
        self.error=error; self.calls=[]
        self.request_telemetry={"business_requests":0,"detail_requests":0}
    @contextmanager
    def bounded_requests(self, limit):
        self.limit=limit
        yield
    def iterate(self, name, **kwargs):
        assert self.request_telemetry["business_requests"] < self.limit
        self.request_telemetry["business_requests"] += 1
        self.calls.append((name,kwargs))
        if self.error: raise self.error
        yield from self.rows

class Store:
    def __init__(self, lock=True): self.lock=lock;self.saved=[];self.runs=[];self.statuses=[]
    @contextmanager
    def work_order_recovery_lock(self): yield self.lock
    def upsert_equipment(self,e): self.saved.append(e);return "inserted"
    def record_equipment_status(self,e):self.statuses.append(e)
    def record_run(self,r):self.runs.append(r)

class Checks:
    def __init__(self, ids=("A1",), due=True):self.ids=ids;self.isdue=due;self.marked=[]
    def due(self,now):return self.isdue
    def candidates(self,now,limit):return self.ids[:limit]
    def mark(self,*args):self.marked.append(args)

class ReferenceCollectorTests(TestCase):
    def run_check(self, client=None, store=None, checks=None, **kw):
        client=client or Client(); store=store or Store();checks=checks or Checks()
        return collect_asset_references(client,store,checks=checks,**kw),client,store,checks
    def test_exact_asset_persists_without_wo_or_cursor_write(self):
        r,c,s,k=self.run_check()
        self.assertEqual(r["inserted"],1);self.assertEqual(s.saved[0].id,"A1")
        self.assertEqual(s.saved[0].source_changed_at.year,2020)
        self.assertEqual(k.marked[0][1],"FOUND_EXACT")
        self.assertEqual(s.runs[0].object_structure,RUN_OBJECT)
        self.assertIsNone(s.runs[0].watermark)
        opts=c.calls[0][1]
        self.assertIn('siteid="BSR" and eq11="CS01" and assetnum="A1"',opts["where"])
        self.assertFalse(opts["allow_resource_links"]); self.assertTrue(opts["strict_members"])
        self.assertEqual((opts["max_pages"],opts["page_size"]),(1,2))
    def test_missing_is_not_deleted_or_aliased(self):
        r,c,s,k=self.run_check(Client([]))
        self.assertEqual(r["not_found_in_scope"],1);self.assertFalse(s.saved)
        self.assertEqual(k.marked[0][1],"NOT_FOUND_IN_SCOPE")
    def test_wrong_site_org_unit_or_identity_fail_closed(self):
        for kw,reason in [({"siteid":"OTHER"},"SCOPE_MISMATCH"),({"orgid":"OTHER"},"SCOPE_MISMATCH"),
                          ({"eq11":"CS02"},"SCOPE_MISMATCH"),({"orgid":None},"SCOPE_MISMATCH"),
                          ({"assetnum":"A2"},"IDENTITY_MISMATCH")]:
            with self.subTest(kw=kw):
                r,c,s,k=self.run_check(Client([asset(**kw)]))
                self.assertFalse(s.saved);self.assertEqual(r["stop_reason"],reason)
    def test_duplicate_or_pagination_is_ambiguous(self):
        for client in (Client([asset(),asset()]),Client(error=OslcPaginationLimitError("mxapiasset",pages=1,max_pages=1,next_page_fingerprint="x"))):
            r,c,s,k=self.run_check(client)
            self.assertFalse(s.saved);self.assertEqual(r["stop_reason"],"AMBIGUOUS")
    def test_invalid_identifier_sends_nothing(self):
        for identity in ('A%','A" or siteid="X','A\\','A'*61):
            r,c,s,k=self.run_check(checks=Checks([identity]))
            self.assertFalse(c.calls);self.assertEqual(r["stop_reason"],"UNSUPPORTED_ID")
    def test_failure_stops_without_retry(self):
        r,c,s,k=self.run_check(Client(error=RuntimeError("secret must not escape")),checks=Checks(["A1","A2"]))
        self.assertEqual(len(c.calls),1);self.assertEqual(r["errors"],1)
        self.assertNotIn("secret",str(r));self.assertEqual(s.runs[0].mode,"targeted_partial")
    def test_request_ceiling(self):
        r,c,s,k=self.run_check(Client([]),checks=Checks(["A1","A2","A3"]),limit=2)
        self.assertEqual(r["requests"],2);self.assertEqual(len(c.calls),2)
    def test_time_budget(self):
        times=iter([0,46])
        r,c,s,k=self.run_check(monotonic=lambda:next(times))
        self.assertFalse(c.calls);self.assertEqual(r["stop_reason"],"TIME_BUDGET")
    def test_source_busy_has_no_lookup_or_schedule_write(self):
        r,c,s,k=self.run_check(store=Store(False))
        self.assertEqual(r["stop_reason"],"SOURCE_BUSY");self.assertFalse(c.calls);self.assertFalse(s.runs)
    def test_scheduled_cooldown_and_explicit_override(self):
        r,c,s,k=self.run_check(checks=Checks(due=False),scheduled=True)
        self.assertEqual(r["stop_reason"],"NOT_DUE");self.assertFalse(c.calls)
        r,c,s,k=self.run_check(checks=Checks(due=False),scheduled=False)
        self.assertEqual(r["inserted"],1)
    def test_bounds_cannot_be_disabled(self):
        for kw in ({"limit":0},{"limit":51},{"max_seconds":0},{"max_seconds":181}):
            with self.assertRaises(ValueError):self.run_check(**kw)
    def test_mapping_error_does_not_persist(self):
        with patch("src.services.asset_references.equipment_from_payload",side_effect=ValueError()):
            r,c,s,k=self.run_check()
        self.assertFalse(s.saved);self.assertEqual(r["stop_reason"],"MAPPING_ERROR")

class ReferenceRepositoryTests(TestCase):
    def setUp(self):
        self.db=Database(DbConfig("sqlite+pysqlite:///:memory:"));self.db.create_all()
        self.checks=AssetReferenceStore(self.db)
        with self.db.session() as s:
            for i,a,scope in [("W1","A1",{"siteid":"BSR","orgid":"IP"}),
                              ("W2","A1",{"siteid":"BSR","orgid":"IP"}),
                              ("W3","A2",{"siteid":"BSR","orgid":"IP"}),
                              ("W4","A3",{"siteid":"OTHER","orgid":"IP"}),
                              ("W5",None,{"siteid":"BSR","orgid":"IP"}),
                              ("W6","A4",{}), ("W7","A5",{"siteid":"BSR","orgid":"IP"})]:
                s.add(orm.WorkOrderOrm(id=i,equipment_id=a,sources={"maximo":scope}))
            s.add(orm.EquipmentOrm(id="A5",unit="CS01"));s.commit()
    def tearDown(self): self.db.engine.dispose()
    def test_candidates_only_proven_scope_missing_exact_ids(self):
        self.assertEqual(self.checks.candidates(NOW,10),["A1","A2"])
    def test_negative_cooldown_expires_and_does_not_starve_next(self):
        self.checks.mark("A1","NOT_FOUND_IN_SCOPE",NOW)
        self.assertEqual(self.checks.candidates(NOW,1),["A2"])
        self.assertEqual(self.checks.candidates(NOW+timedelta(days=7),1),["A1"])
    def test_schedule_uses_own_run_not_wo_cursor(self):
        self.assertTrue(self.checks.due(NOW))
        with self.db.session() as s:
            s.add(orm.CollectRunOrm(object_structure=RUN_OBJECT,mode="targeted",started_at=NOW,finished_at=NOW));s.commit()
        self.assertFalse(self.checks.due(NOW+timedelta(minutes=59)))
        self.assertTrue(self.checks.due(NOW+timedelta(hours=1)))
    def test_audit_attempts_idempotent_identity_and_counts(self):
        self.checks.mark("A1","NOT_FOUND_IN_SCOPE",NOW)
        self.checks.mark("A1","FOUND_EXACT",NOW)
        with self.db.session() as s:self.assertEqual(s.get(orm.AssetReferenceCheckOrm,"A1").attempts,2)
        r=self.checks.coverage()
        self.assertEqual(r["work_orders_without_asset_id"],1)
        self.assertEqual(r["work_orders_with_missing_equipment"],5)
        self.assertEqual(r["distinct_missing_asset_ids"],4)
        self.assertEqual(r["source_verified_bsr_missing_wo"],3)
        self.assertEqual(r["source_verified_bsr_missing_asset_ids"],2)
        self.assertEqual(r["lookup_outcomes"],{"FOUND_EXACT":1})
    def test_old_asset_insert_has_local_evidence_without_changedate_rewrite(self):
        from src.adapters.maximo.mappers import equipment_from_payload
        store=CollectorStore(self.db)
        store.upsert_equipment(equipment_from_payload(asset()))
        with self.db.session() as s:
            e=s.get(orm.EquipmentOrm,"A1")
            self.assertEqual(e.source_changed_at.year,2020)
            self.assertIn("collector_updated_at",e.sources["maximo"])
        self.assertEqual(self.checks.candidates(NOW,10),["A2"])

class RecoveredAssetProjectionTest(TestCase):
    def test_old_reference_is_reconsidered_by_incremental_projection(self):
        from src.adapters.maximo.mappers import equipment_from_payload
        from src.services.local_mart_projector import CollectorMartProjector
        from src.repositories import mart_models
        db=Database(DbConfig("sqlite+pysqlite:///:memory:"));db.create_all()
        try:
            with db.session() as session:
                # Establish a newer watermark, so old records would be missed.
                session.add(orm.EquipmentOrm(id="NEW",unit="CS01",source_changed_at=NOW,
                    sources={"maximo":asset("NEW",changedate=NOW.isoformat())}))
                session.add(orm.WorkOrderOrm(id="BSR-NEW",equipment_id="NEW",status="CLOSE",source_changed_at=NOW,
                    sources={"maximo":{"siteid":"BSR","orgid":"IP"}}))
                session.add(orm.WorkOrderOrm(id="BSR-OLD",equipment_id="A1",status="CLOSE",source_changed_at=NOW-timedelta(days=1000),
                    sources={"maximo":{"siteid":"BSR","orgid":"IP"}}))
                session.commit()
            projector=CollectorMartProjector(db,db)
            first=projector.project_all()
            self.assertEqual(first["maintenance_event"]["skipped_missing_equipment"],1)
            CollectorStore(db).upsert_equipment(equipment_from_payload(asset()))
            report=projector.project_all(incremental=True)
            self.assertTrue(report["asset_master"]["completed"])
            with db.session() as session:
                self.assertEqual(session.query(mart_models.AssetMasterMartOrm).count(),2)
                self.assertEqual(session.query(mart_models.MaintenanceEventMartOrm).count(),2)
                self.assertEqual(session.get(orm.WorkOrderOrm,"BSR-OLD").equipment_id,"A1")
                self.assertEqual(session.query(mart_models.ReliabilityAssetRegistryMartOrm).count(),0)
        finally:db.engine.dispose()

class ExactAssetTransportTest(TestCase):
    def test_resource_link_refused_before_any_detail_read(self):
        from tests.test_guard import PaginationCompletionTest
        from src.adapters.maximo.oslc_client import OslcError
        fixture=PaginationCompletionTest()
        client=fixture._client([fixture.Response({"_member":[{"rdf:resource":"https://example.invalid/asset/1"}]})])
        client._detail_request_count=0
        with self.assertRaises(OslcError):
            list(client.iterate("mxapiasset",allow_resource_links=False,strict_members=True))
        self.assertEqual(client._detail_request_count,0)

class ManualOnlyIntegrationTest(TestCase):
    def test_wo_sync_never_invokes_asset_recovery(self):
        from types import SimpleNamespace
        from src.cli import cmd_sync
        service=SimpleNamespace(sync=lambda config:SimpleNamespace(mode="incremental",object_structure="mxwodetail",
            rows_seen=0,upserted=0,skipped=0,errors=0,watermark=None,complete=True))
        with patch("src.cli.get_database",return_value=object()), patch("src.cli.CollectorStore",return_value=object()), \
             patch("src.cli._sync_service",return_value=(service,object())), \
             patch("src.api.app.sync_config_for",return_value=SimpleNamespace(object_structure="mxwodetail")), \
             patch("src.services.asset_references.collect_asset_references") as collect:
            self.assertEqual(cmd_sync(SimpleNamespace(objects=["mxwodetail"])),0)
            collect.assert_not_called()
