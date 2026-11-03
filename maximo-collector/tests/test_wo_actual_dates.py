"""Synthetic, network-free date lineage, recovery and conflict rehearsals."""
import copy
from contextlib import contextmanager
from datetime import datetime, timezone
import sqlite3
import unittest
from unittest.mock import Mock

from src.adapters.maximo.actual_dates import clock, evidence, retained_values
from src.adapters.maximo.canonical_mappers import maintenance_event_from_payload
from src.adapters.maximo.mappers import work_order_from_payload
from src.api.app import WORK_ORDER_SELECT
from src.canonical_identity import canonical_id
from src.config import DbConfig
from src.repositories.database import Database
from src.repositories import models, mart_models
from src.repositories.store import CollectorStore
from src.services.canonical import CanonicalCollection
from src.services.local_mart_projector import _work_order_payload
from src.services.mart import MartWriter, CanonicalRecordRejected
from src.services.wo_actual_date_recovery import plan_cohort, fetch_cohort, apply_cohort, rollback_cohort, seal, SELECT

T = "2026-09-02T10:00:00+07:00"
RAW = dict(wonum="BSR-SYNTHETIC-1", assetnum="ASSET-SYNTHETIC", siteid="BSR", orgid="IP",
           changedate=T, status="CLOSE", worktype="CD", actstart="2026-09-01T22:00:00.123400+07:00",
           actfinish="2026-09-02T01:00:00+07:00", downtime=0, actlabhrs=0)


def seed(db, raw=RAW):
    local = work_order_from_payload({k:v for k,v in raw.items() if k not in ("actstart", "actfinish")})
    CollectorStore(db).upsert_work_order(local)
    mapped = maintenance_event_from_payload({k:v for k,v in raw.items() if k not in ("actstart", "actfinish")})
    MartWriter(db).persist_collection(CanonicalCollection("maintenance_event", records=[mapped]))
    asset = canonical_id("asset", "MXASSET", raw["assetnum"], "BSR", "IP")
    with db.session() as s:
        if s.get(mart_models.ReliabilityAssetRegistryMartOrm, asset) is None:
            s.add(mart_models.ReliabilityAssetRegistryMartOrm(asset_ref=asset, source_asset_number=raw["assetnum"],
                  site_code="BSR", organization_code="IP", registry_source="SYNTHETIC", snapshot_sha256="a"*64,
                  snapshot_row_count=1, snapshot_imported_at=datetime.now(timezone.utc)))
        s.commit()


class ActualDatesTest(unittest.TestCase):
    def setUp(self):
        self.db=Database(DbConfig("sqlite+pysqlite:///:memory:")); self.db.create_all()
        self.addCleanup(self.db.engine.dispose)

    def write(self, raw):
        return MartWriter(self.db).persist_collection(CanonicalCollection("maintenance_event", records=[maintenance_event_from_payload(raw)]))

    def test_selection_and_end_to_end_retention(self):
        self.assertTrue({"actstart", "actfinish"} <= set(WORK_ORDER_SELECT))
        CollectorStore(self.db).upsert_work_order(work_order_from_payload(RAW))
        with self.db.session() as s:
            row=s.get(models.WorkOrderOrm, RAW["wonum"])
            payload=_work_order_payload(row)
            self.assertEqual(payload["actstart"], RAW["actstart"])
            self.write(payload)
            stored=s.get(mart_models.MaintenanceEventMartOrm, maintenance_event_from_payload(RAW)["id"])
            self.assertEqual(stored.actual_start.utcoffset().total_seconds(), 7*3600)
            self.assertEqual(stored.sources["maximo"]["actstart"],RAW["actstart"])
            self.assertEqual(stored.downtime_hours,0); self.assertEqual(stored.labor_hours,0)
            self.assertIsNone(stored.duration_hours); self.assertIsNone(stored.event_type)
            self.assertEqual(stored.status,"CLOSE")

    def test_all_clock_states_and_no_substitutions(self):
        for value,state in [(None,"MISSING"),("","MISSING"),("broken","INVALID"),("2026-09-01","INVALID"),
                            ("2026-09-01T10:00:00","NAIVE"),(RAW["actstart"],"VALID")]:
            self.assertEqual(clock(value)["state"],state)
            record=maintenance_event_from_payload(dict(RAW,actstart=value,actfinish=None))
            self.assertEqual(record["actual_start"] is not None,state=="VALID")
            self.assertIsNone(record["actual_finish"])
        self.assertEqual(clock(None,present=False)["state"],"UNAVAILABLE")
        for zone in ("Z","+00:00","-03:30","+07:00"):
            self.assertEqual(clock("2026-09-01T10:00:00"+zone)["state"],"VALID")

    def test_scope_identity_version_revalidation(self):
        proof=evidence(RAW)
        self.assertEqual(retained_values(proof, RAW["wonum"], RAW["assetnum"], T)["actstart"],RAW["actstart"])
        for key,value in (("siteid","OTHER"),("orgid","OTHER"),("wonum","BSR-OTHER"),("assetnum","OTHER")):
            changed=copy.deepcopy(proof);changed["identity"][key]=value
            self.assertEqual(retained_values(changed,RAW["wonum"],RAW["assetnum"],T),{})
        self.assertEqual(retained_values(proof,RAW["wonum"],RAW["assetnum"],"2026-08-01T00:00:00Z"),{})
        changed=copy.deepcopy(proof);changed["fields"]["actstart"]["normalized"]="forged"
        self.assertNotIn("actstart",retained_values(changed,RAW["wonum"],RAW["assetnum"],T))

    def test_legacy_preserves_dates_missing_and_rejects_stale_and_equal_conflicts(self):
        store=CollectorStore(self.db);store.upsert_work_order(work_order_from_payload(RAW))
        self.assertFalse(store.is_unchanged("work_order",RAW["wonum"],"source_changed_at",datetime.fromisoformat(T)))
        newer=dict(RAW,changedate="2026-09-03T00:00:00Z",actstart=None,actfinish=None,status="CAN")
        store.upsert_work_order(work_order_from_payload(newer))
        store.upsert_work_order(work_order_from_payload(dict(RAW,status="STALE")))
        with self.db.session() as s:
            row=s.get(models.WorkOrderOrm,RAW["wonum"])
            self.assertEqual(row.status,"CAN");self.assertEqual(_work_order_payload(row)["actstart"],RAW["actstart"])
        store.upsert_work_order(work_order_from_payload(RAW))

    def test_equal_legacy_date_conflict_is_atomic(self):
        store=CollectorStore(self.db);store.upsert_work_order(work_order_from_payload(RAW))
        with self.assertRaises(ValueError):
            store.upsert_work_order(work_order_from_payload(dict(RAW,actstart="2026-08-01T00:00:00Z",status="CONFLICT")))
        with self.db.session() as s:self.assertEqual(s.get(models.WorkOrderOrm,RAW["wonum"]).status,"CLOSE")

    def test_mart_stale_missing_and_same_version_conflict(self):
        self.write(RAW)
        self.assertEqual(self.write(RAW).records_unchanged,1)
        self.write(dict(RAW,changedate="2026-09-03T00:00:00Z",actstart=None,actfinish=None,status="CAN"))
        self.assertEqual(self.write(dict(RAW,status="STALE")).records_unchanged,1)
        self.assertEqual(self.write(dict(RAW,changedate=None,status="UNKNOWN")).records_unchanged,1)
        # The retained clock is still a v1 observation. A v2 explicit valid
        # correction is newer field evidence even when the row was already v2.
        self.write(dict(RAW,changedate="2026-09-03T00:00:00Z",actstart="2026-08-01T00:00:00Z",status="CAN"))
        with self.assertRaises(CanonicalRecordRejected):
            self.write(dict(RAW,changedate="2026-09-03T00:00:00Z",actstart="2026-08-02T00:00:00Z"))
        with self.db.session() as s:
            row=s.get(mart_models.MaintenanceEventMartOrm,maintenance_event_from_payload(RAW)["id"])
            self.assertEqual(row.status,"CAN");self.assertIsNotNone(row.actual_start);self.assertIsNotNone(row.actual_finish)

    def test_recovery_idempotent_rollback_and_unrelated_preserved(self):
        seed(self.db);plan=plan_cohort(self.db,[RAW["wonum"]]);digest=seal(plan)
        receipt=apply_cohort(self.db,plan,{RAW["wonum"]:RAW},expected_database="disposable-sqlite",approved_plan_sha256=digest)
        replay=apply_cohort(self.db,plan,{RAW["wonum"]:RAW},expected_database="disposable-sqlite",approved_plan_sha256=digest)
        self.assertEqual(receipt["records"][0]["after_sha256"],replay["records"][0]["after_sha256"])
        with self.db.session() as s:
            row=s.get(mart_models.MaintenanceEventMartOrm,plan["cohort"][0]["canonical_id"])
            self.assertEqual(row.status,"CLOSE");self.assertEqual(row.downtime_hours,0);self.assertIsNone(row.event_type)
            self.assertIsNotNone(row.actual_start);self.assertIsNotNone(row.actual_finish)
            self.assertEqual(s.query(models.WorkOrderOrm).one().sources["maximo"]["actual_dates"]["fields"]["actstart"]["state"],"VALID")
            self.assertEqual(s.query(models.SyncCursorOrm).count(),0)
            self.assertEqual(s.query(mart_models.MartProjectionStateOrm).count(),0)
        rollback_cohort(self.db,receipt,expected_database="disposable-sqlite")
        with self.db.session() as s:self.assertIsNone(s.get(mart_models.MaintenanceEventMartOrm,plan["cohort"][0]["canonical_id"]).actual_start)

    def test_recovery_rejects_source_local_version_scope_and_manifest_conflicts(self):
        seed(self.db);plan=plan_cohort(self.db,[RAW["wonum"]])
        for raw in [dict(RAW,siteid="OTHER"),dict(RAW,assetnum="OTHER"),dict(RAW,changedate="2026-09-04T00:00:00Z")]:
            with self.assertRaises(ValueError):apply_cohort(self.db,plan,{RAW["wonum"]:raw},expected_database="disposable-sqlite",approved_plan_sha256=seal(plan))
        with self.assertRaises(ValueError):apply_cohort(self.db,plan,{RAW["wonum"]:RAW},expected_database="disposable-sqlite",approved_plan_sha256="wrong")
        self.write(dict(RAW,changedate="2026-09-04T00:00:00Z"))
        with self.assertRaises(ValueError):apply_cohort(self.db,plan,{RAW["wonum"]:RAW},expected_database="disposable-sqlite",approved_plan_sha256=seal(plan))

    def test_rollback_refuses_newer_normal_worker_record(self):
        seed(self.db);plan=plan_cohort(self.db,[RAW["wonum"]])
        receipt=apply_cohort(self.db,plan,{RAW["wonum"]:RAW},expected_database="disposable-sqlite",approved_plan_sha256=seal(plan))
        self.write(dict(RAW,changedate="2026-09-04T00:00:00Z"))
        with self.assertRaises(ValueError):rollback_cohort(self.db,receipt,expected_database="disposable-sqlite")

    def test_bounded_resumable_fetch_no_completed_refetch(self):
        seed(self.db);plan=plan_cohort(self.db,[RAW["wonum"]]);client=Mock()
        @contextmanager
        def budget(n):
            self.assertEqual(n,20);yield
        client.bounded_requests.side_effect=budget;client.iterate.return_value=[RAW]
        saved=[];self.assertEqual(fetch_cohort(client,plan,checkpoint=saved.append),{RAW["wonum"]:{k:v for k,v in RAW.items() if k in SELECT}})
        client.iterate.assert_called_once();client.iterate.reset_mock()
        fetch_cohort(client,plan,completed=saved[0]);client.iterate.assert_not_called()
        with self.assertRaises(ValueError):plan_cohort(self.db,[RAW["wonum"]]*11)

    def test_entire_batch_rollback_on_second_identity_failure(self):
        second=dict(RAW,wonum="BSR-SYNTHETIC-2");seed(self.db);seed(self.db,second)
        plan=plan_cohort(self.db,[RAW["wonum"],second["wonum"]])
        with self.assertRaises(ValueError):apply_cohort(self.db,plan,{RAW["wonum"]:RAW,second["wonum"]:dict(second,siteid="OTHER")},expected_database="disposable-sqlite",approved_plan_sha256=seal(plan))
        with self.db.session() as s:
            self.assertEqual(s.query(mart_models.MaintenanceEventMartOrm).filter(mart_models.MaintenanceEventMartOrm.actual_start.is_not(None)).count(),0)

    def test_independent_memory_restore_recovery_replay_and_rollback(self):
        seed(self.db)
        backup=sqlite3.connect(":memory:")
        isolated=Database(DbConfig("sqlite+pysqlite:///:memory:"))
        a=self.db.engine.raw_connection();b=isolated.engine.raw_connection()
        try:
            a.driver_connection.backup(backup)
            backup.backup(b.driver_connection)
            plan=plan_cohort(isolated,[RAW["wonum"]])
            receipt=apply_cohort(isolated,plan,{RAW["wonum"]:RAW},expected_database="disposable-sqlite",approved_plan_sha256=seal(plan))
            rollback_cohort(isolated,receipt,expected_database="disposable-sqlite")
            with isolated.session() as session:self.assertIsNone(session.query(mart_models.MaintenanceEventMartOrm).one().actual_start)
            with self.db.session() as session:self.assertIsNone(session.query(mart_models.MaintenanceEventMartOrm).one().actual_start)
        finally:a.close();b.close();backup.close();isolated.engine.dispose()


class StatusCompletenessTest(unittest.TestCase):
    def classify(self, raw, *, actual=True, source=True):
        from src.services.wo_actual_date_completeness import classify_dates
        record=maintenance_event_from_payload(raw)
        if not actual:record.update(actual_start=None,actual_finish=None,sources={"maximo":{"assetnum":raw["assetnum"]}})
        return classify_dates(record,source=raw if source else None)

    def test_status_never_fabricates_or_suppresses_dates(self):
        for status in ("WAPPR","WMATL","COMP","CLOSE","CUSTOM","wappr"):
            result=self.classify(dict(RAW,status=status))
            self.assertEqual(result["status"],status);self.assertEqual(result["state"],"ACTUAL_DATES_AVAILABLE")
            empty=self.classify(dict(RAW,status=status,actstart=None,actfinish=None))
            self.assertEqual(empty["state"],"SOURCE_CONFIRMED_EMPTY")
            self.assertEqual(empty["advanced_status_missing_dates"],status in ("COMP","CLOSE"))
            if status in ("WAPPR","WMATL"):self.assertIn("may not yet",empty["status_note"])

    def test_evidence_derived_seven_states(self):
        self.assertEqual(self.classify(RAW)["state"],"ACTUAL_DATES_AVAILABLE")
        self.assertEqual(self.classify(dict(RAW,actfinish=None))["state"],"START_ONLY")
        self.assertEqual(self.classify(dict(RAW,actstart=None))["state"],"FINISH_ONLY")
        self.assertEqual(self.classify(dict(RAW,actstart=None,actfinish=None))["state"],"SOURCE_CONFIRMED_EMPTY")
        self.assertEqual(self.classify(RAW,actual=False,source=False)["state"],"SOURCE_NOT_YET_VERIFIED")
        self.assertEqual(self.classify(RAW,actual=False)["state"],"COLLECTOR_PROJECTION_GAP")
        self.assertEqual(self.classify(dict(RAW,actstart="2026-09-01T00:00:00"))["state"],"SOURCE_TIMESTAMP_INVALID")

    def test_projection_gap_and_missing_field_are_not_confirmed_null(self):
        from src.services.wo_actual_date_completeness import classify_dates
        raw={k:v for k,v in RAW.items() if k not in ("actstart","actfinish")}
        result=self.classify(raw)
        self.assertEqual(result["state"],"SOURCE_NOT_YET_VERIFIED")
        self.assertEqual(len(result["unverified_missing_fields"]),2)
        record=maintenance_event_from_payload(RAW);record.update(actual_start=None,actual_finish=None)
        self.assertEqual(classify_dates(record)["state"],"COLLECTOR_PROJECTION_GAP")
        wrong=dict(RAW,siteid="OTHER")
        result=classify_dates(dict(record,sources={}),source=wrong)
        self.assertTrue(result["source_identity_or_version_mismatch"])
        self.assertEqual(result["state"],"SOURCE_NOT_YET_VERIFIED")

    def test_status_matrix_retains_early_statuses_and_missing_reasons(self):
        from src.services.wo_actual_date_completeness import status_date_matrix
        results=[self.classify(dict(RAW,status=s,actstart=None,actfinish=None)) for s in ("WAPPR","WMATL","COMP","CLOSE")]
        matrix=status_date_matrix(results)
        self.assertEqual(sum(r["total"] for r in matrix),4)
        self.assertEqual({r["status"] for r in matrix},{"WAPPR","WMATL","COMP","CLOSE"})
        self.assertTrue(all(r["source_confirmed_null"]==1 and r["both_missing"]==1 for r in matrix))


class RecoveryCheckpointTest(unittest.TestCase):
    def test_durable_checkpoint_failure_rolls_back_whole_transaction(self):
        db=Database(DbConfig("sqlite+pysqlite:///:memory:"));db.create_all()
        try:
            seed(db);plan=plan_cohort(db,[RAW["wonum"]])
            def failed(receipt):raise OSError("synthetic full private disk")
            with self.assertRaises(OSError):apply_cohort(db,plan,{RAW["wonum"]:RAW},expected_database="disposable-sqlite",approved_plan_sha256=seal(plan),checkpoint=failed)
            with db.session() as session:
                self.assertIsNone(session.query(mart_models.MaintenanceEventMartOrm).one().actual_start)
                self.assertEqual(session.query(models.WorkOrderOrm).one().sources["maximo"]["actual_dates"]["fields"]["actstart"]["state"],"UNAVAILABLE")
        finally:db.engine.dispose()


class IndependentReviewRegressions(unittest.TestCase):
    def test_unobserved_legacy_dates_remain_unverified_after_projection(self):
        from src.services.wo_actual_date_completeness import classify_dates
        row=models.WorkOrderOrm(id=RAW["wonum"],equipment_id=RAW["assetnum"],source_changed_at=datetime.fromisoformat(T))
        record=maintenance_event_from_payload(_work_order_payload(row))
        self.assertEqual(record["sources"]["maximo"]["actual_dates"]["fields"]["actstart"]["state"],"UNAVAILABLE")
        self.assertEqual(classify_dates(record)["state"],"SOURCE_NOT_YET_VERIFIED")

    def test_redacted_invalid_original_never_becomes_confirmed_null(self):
        from src.services.wo_actual_date_completeness import classify_dates
        for value in ("x"*129,{"unexpected":"non-scalar"},["bad"],123,True):
            raw=dict(RAW,actstart=value,actfinish=None)
            direct=maintenance_event_from_payload(raw)
            self.assertEqual(classify_dates(direct)["state"],"SOURCE_TIMESTAMP_INVALID")
            mapped=work_order_from_payload(raw)
            row=models.WorkOrderOrm(**{f.name:getattr(mapped,f.name) for f in __import__('dataclasses').fields(mapped)})
            projected=maintenance_event_from_payload(_work_order_payload(row))
            self.assertEqual(projected["sources"]["maximo"]["actual_dates"]["fields"]["actstart"]["state"],"INVALID")
            self.assertEqual(classify_dates(projected)["state"],"SOURCE_TIMESTAMP_INVALID")

    def test_newer_field_correction_agrees_in_collector_and_mart(self):
        db=Database(DbConfig("sqlite+pysqlite:///:memory:"));db.create_all()
        try:
            store,writer=CollectorStore(db),MartWriter(db)
            observations=[RAW,dict(RAW,changedate="2026-09-03T00:00:00Z",actstart=None),
                          dict(RAW,changedate="2026-09-03T00:00:00Z",actstart="2026-08-01T00:00:00Z")]
            for raw in observations:
                store.upsert_work_order(work_order_from_payload(raw))
                with db.session() as session:record=maintenance_event_from_payload(_work_order_payload(session.get(models.WorkOrderOrm,RAW["wonum"])))
                writer.persist_collection(CanonicalCollection("maintenance_event",records=[record]))
            with db.session() as session:
                mart=session.query(mart_models.MaintenanceEventMartOrm).one()
                self.assertEqual(mart.actual_start,datetime.fromisoformat(observations[-1]["actstart"]))
                self.assertEqual(datetime.fromisoformat(mart.sources["maximo"]["actual_dates"]["fields"]["actstart"]["source_changed_at"]),datetime.fromisoformat(observations[-1]["changedate"].replace("Z","+00:00")))
        finally:db.engine.dispose()


class WorkOrderClientRegression(unittest.TestCase):
    class Response:
        content=b"{}"
        headers={"Content-Type":"application/json"}
        text=""
        url="http://maximo.example/maximo/oslc/os/mxwodetail"
        def __init__(self,payload,status=200):self.payload=payload;self.status_code=status
        def json(self):return self.payload
        def raise_for_status(self):
            if self.status_code>=400:raise RuntimeError("synthetic HTTP error")

    def client(self,responses,budget=20):
        from types import SimpleNamespace
        from src.adapters.maximo.oslc_client import OslcClient
        from src.config import MaximoConfig
        session=Mock();session.request.side_effect=responses
        auth=SimpleNamespace(session=session,last_request_at=0.0,ensure_logged_in=Mock(),handle_expiry=Mock())
        return OslcClient(MaximoConfig(base_url="http://maximo.example/maximo",rate_limit_seconds=0),auth,request_budget=budget),auth

    def test_wo_collection_expiry_retries_once_without_weakening_page_or_request_caps(self):
        client,auth=self.client([self.Response({},401),self.Response({"_member":[RAW]})])
        rows=list(client.iterate("mxwodetail",select=list(SELECT),page_size=2,max_pages=1))
        self.assertEqual(rows,[RAW]);auth.handle_expiry.assert_called_once()
        self.assertEqual(client.request_telemetry["business_requests"],2);self.assertEqual(client.last_iteration_pages,1)
        from src.adapters.maximo.oslc_client import OslcRequestBudgetExceeded,OslcAuthExpiredError
        client,auth=self.client([self.Response({},401),self.Response({},401)])
        with self.assertRaises(OslcAuthExpiredError):list(client.iterate("mxwodetail",page_size=2,max_pages=1))
        self.assertEqual(client.request_telemetry["business_requests"],2);auth.handle_expiry.assert_called_once()
        client,_=self.client([self.Response({},401)],budget=1)
        with self.assertRaises(OslcRequestBudgetExceeded):list(client.iterate("mxwodetail",page_size=2,max_pages=1))
        self.assertEqual(client.request_telemetry["business_requests"],1)

    def test_wo_detail_link_carries_exact_field_selection(self):
        from urllib.parse import parse_qs,urlsplit
        link="http://maximo.example/maximo/oslc/os/mxwodetail/SYNTHETIC?oslc.select=*"
        client,_=self.client([self.Response({"_member":[{"rdf:resource":link}]}),self.Response(RAW)])
        self.assertEqual(list(client.iterate("mxwodetail",select=list(SELECT),page_size=2,max_pages=1)),[RAW])
        detail_url=client._session.request.call_args_list[1].args[1]
        self.assertEqual(parse_qs(urlsplit(detail_url).query)["oslc.select"],[",".join(SELECT)])
        self.assertEqual(client.request_telemetry["business_requests"],2)


class UnknownClockVersionRegression(unittest.TestCase):
    def test_conflicting_non_null_clock_requires_provably_newer_field_version(self):
        db=Database(DbConfig("sqlite+pysqlite:///:memory:"));db.create_all()
        try:
            writer=MartWriter(db)
            initial=maintenance_event_from_payload(dict(RAW,changedate=None))
            writer.persist_collection(CanonicalCollection("maintenance_event",records=[initial]))
            for change in (None,"2026-09-04T00:00:00Z"):
                conflicting=maintenance_event_from_payload(dict(RAW,changedate=change,actstart="2026-08-01T00:00:00Z"))
                with self.assertRaises(CanonicalRecordRejected):writer.persist_collection(CanonicalCollection("maintenance_event",records=[conflicting]))
            with db.session() as session:self.assertEqual(session.query(mart_models.MaintenanceEventMartOrm).one().actual_start,datetime.fromisoformat(RAW["actstart"]))
        finally:db.engine.dispose()


class SourceNullVsEmptyRegression(unittest.TestCase):
    def test_explicit_blank_is_confirmed_empty_but_not_source_null(self):
        from src.services.wo_actual_date_completeness import classify_dates,status_date_matrix
        raw=dict(RAW,actstart="",actfinish="")
        result=classify_dates(maintenance_event_from_payload(raw),source=raw)
        self.assertEqual(result["state"],"SOURCE_CONFIRMED_EMPTY")
        self.assertEqual(result["source_confirmed_null_fields"],[])
        self.assertEqual(set(result["source_confirmed_empty_fields"]),{"actstart","actfinish"})
        matrix=status_date_matrix([result])
        self.assertEqual(matrix[0]["source_confirmed_null"],0)
        self.assertEqual(matrix[0]["source_confirmed_empty"],1)
