"""Mapper + sync-engine tests (fakes — no network, no DB)."""

from __future__ import annotations

import unittest
import json
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Mapping

from src.adapters.maximo.mappers import equipment_from_payload, work_order_from_payload
from src.api.app import sync_config_for
from src.adapters.maximo.oslc_client import OslcError, OslcPaginationLimitError, oslc_boolean, oslc_number, oslc_timestamp
from src.repositories.store import _row
from src.services.sync import ObjectSyncConfig, SyncService

SAMPLE_ASSET = {
    "assetnum": "BSR-101",
    "description": "Boiler Feed Pump A",
    "location": "BSR-PLANT",
    "siteid": "BSR",
    "orgid": "IP",
    "status": "OPERATING",
    "assettype": "PUMP",
    "isrunning": "true",  # Maximo stringifies booleans
    "priority": "2",
    "changedate": "2026-08-17T09:00:00Z",
    "totdowntime": "12.5",
    "eq11": "CS01",
}

SAMPLE_WO = {
    "wonum": "WO-2001",
    "reportdate": "2025-01-01T00:00:00+07:00",
    "assetnum": "BSR-101",
    "status": "CLOSE",
    "worktype": "PM",
    "changedate": "2026-08-18T01:30:00Z",
    "actlabhrs": "3.5",
    "istask": "false",
    "seksi": "Operasi",
    "bu": "Generation",
    "jumlahhidup": "1",
    "luasareatanam": "12.5",
}

SAMPLE_BSR_WO = {
    **SAMPLE_WO,
    "wonum": "BSR25/17466",
}


class CoercionTest(unittest.TestCase):
    def test_boolean_strings(self):
        self.assertIs(oslc_boolean("true"), True)
        self.assertIs(oslc_boolean("1"), True)
        self.assertIs(oslc_boolean("false"), False)
        self.assertIsNone(oslc_boolean(""))
        self.assertIs(oslc_boolean(True), True)

    def test_number_strings(self):
        self.assertEqual(oslc_number("12.5"), 12.5)
        self.assertIsNone(oslc_number("n/a"))

    def test_timestamp_variants(self):
        self.assertEqual(
            oslc_timestamp("2026-08-17T09:00:00Z"),
            datetime(2026, 8, 17, 9, 0, tzinfo=timezone.utc),
        )
        self.assertIsNone(oslc_timestamp(""))


class MapperTest(unittest.TestCase):
    def test_equipment_requires_primary_key(self):
        with self.assertRaises(ValueError):
            equipment_from_payload({"description": "missing asset number"})

    def test_equipment_contract_shape(self):
        e = equipment_from_payload(SAMPLE_ASSET)
        self.assertEqual(e.id, "BSR-101")
        self.assertEqual(e.status, "OPERATING")
        self.assertIs(e.is_running, True)  # coerced from "true"
        self.assertEqual(e.downtime_total_hours, 12.5)
        # vendor quarantine
        self.assertEqual(e.maximo_source.siteid, "BSR")
        self.assertEqual(e.maximo_source.assetnum, "BSR-101")
        self.assertTrue(type(e).__dataclass_params__.frozen)
        row = _row(e)
        self.assertTrue(json.dumps(row))
        self.assertNotIn("maximo_source", row)
        self.assertEqual(row["sources"]["maximo"]["assetnum"], "BSR-101")

    def test_verified_mxapiasset_extra_fields_stay_quarantined(self):
        e = equipment_from_payload({
            **SAMPLE_ASSET,
            "assettype_description": "Production Assets",
            "plant_description": "PLTU BSR",
            "ytdcost": "12.5",
            "disabled": "false",
            "href": "https://should-not-be-stored",
            "changeby": "PERSON-1",
        })
        self.assertEqual(e.maximo_source.extra["assettype_description"], "Production Assets")
        self.assertEqual(e.maximo_source.extra["ytdcost"], 12.5)
        self.assertIs(e.maximo_source.extra["disabled"], False)
        self.assertNotIn("href", e.maximo_source.extra)
        self.assertNotIn("changeby", e.maximo_source.extra)

    def test_work_order_contract_shape(self):
        w = work_order_from_payload(SAMPLE_WO)
        self.assertEqual(w.id, "WO-2001")
        self.assertEqual(w.work_type, "PM")
        self.assertEqual(w.actual_labor_hours, 3.5)
        self.assertEqual(w.sources["maximo"]["wonum"], "WO-2001")
        self.assertEqual(w.sources["maximo"]["extra"]["seksi"], "Operasi")
        self.assertEqual(w.sources["maximo"]["extra"]["jumlahhidup"], 1.0)


class FakeStore:
    def __init__(self):
        self.entities: list[tuple[str, object]] = []
        self.cursors: dict[str, datetime | None] = {}
        self.runs: list = []
        self.unchanged: set[tuple[str, str, str, datetime]] = set()
        self.status_history: list[object] = []

    def get_cursor(self, scope):
        return self.cursors.get(scope)

    def set_cursor(self, scope, watermark, rows_seen):
        self.cursors[scope] = watermark

    def upsert_for(self, entity_name, entity):
        self.entities.append((entity_name, entity))

    def upsert_many_for(self, entity_name, entities):
        self.entities.extend((entity_name, entity) for entity in entities)

    def is_unchanged(self, entity_name, entity_id, compare_column, source_value):
        return (entity_name, entity_id, compare_column, source_value) in self.unchanged

    def record_equipment_status(self, entity):
        self.status_history.append(entity)

    def record_run(self, stats):
        self.runs.append(stats)


class FakeClient:
    """Records iterate() calls; returns canned pages."""

    def __init__(self, pages):
        self.pages = pages
        self.calls: list[dict] = []

    def iterate(self, object_structure, *, where=None, required_scope=None, select=None, order_by=None, page_size=None, max_pages=1000, identity_field=None):
        self.calls.append({"os": object_structure, "where": where, "required_scope": required_scope, "select": select, "order_by": order_by, "page_size": page_size})
        yield from self.pages


class SyncEngineTest(unittest.TestCase):
    CFG = ObjectSyncConfig(
        object_structure="mxasset",
        entity_name="equipment",
        mapper=equipment_from_payload,
        watermark_field="changedate",
        order_by="-changedate",
    )

    def test_full_sync_first_run(self):
        store, client = FakeStore(), FakeClient([SAMPLE_ASSET])
        stats = SyncService(client, store).sync(self.CFG)
        self.assertEqual(stats.mode, "full")
        self.assertEqual(stats.upserted, 1)
        self.assertEqual(len(store.entities), 1)
        self.assertEqual(client.calls[0]["where"], 'siteid="BSR"')  # site scope default
        self.assertEqual(client.calls[0]["required_scope"], 'siteid="BSR"')
        self.assertEqual(stats.watermark, datetime(2026, 8, 17, 9, 0, tzinfo=timezone.utc))

    def test_incremental_uses_watermark(self):
        store = FakeStore()
        store.cursors["mxasset"] = datetime(2026, 8, 17, 9, 0, tzinfo=timezone.utc)
        client = FakeClient([])
        stats = SyncService(client, store).sync(self.CFG)
        self.assertEqual(stats.mode, "incremental")
        self.assertIn("changedate >= ", client.calls[0]["where"])

    def test_bad_row_skipped_not_fatal(self):
        bad: Mapping[str, Any] = {"description": "no assetnum at all"}  # mapper ok but id=""
        store, client = FakeStore(), FakeClient([bad, SAMPLE_ASSET])
        # make the mapper raise for the first row
        original = self.CFG.mapper

        def flaky(member):
            if member is bad:
                raise ValueError("flaky")
            return original(member)

        cfg = ObjectSyncConfig(
            object_structure="mxasset", entity_name="equipment",
            mapper=flaky, watermark_field="changedate",
        )
        stats = SyncService(client, store).sync(cfg)
        self.assertEqual(stats.rows_seen, 2)
        self.assertEqual(stats.upserted, 1)
        self.assertEqual(stats.skipped, 1)
        self.assertEqual(stats.errors, 1)

    def test_no_watermark_object_always_full(self):
        cfg = ObjectSyncConfig(
            object_structure="mxapilabor", entity_name="labor",
            mapper=lambda m: None, watermark_field=None,
        )
        store = FakeStore()
        store.cursors["mxapilabor"] = datetime(2026, 1, 1, tzinfo=timezone.utc)
        client = FakeClient([])
        stats = SyncService(client, store).sync(cfg)
        self.assertEqual(stats.mode, "full")  # labor has no watermark by design
        self.assertNotIn("changedate", client.calls[0]["where"])

    def test_unchanged_row_is_skipped(self):
        store = FakeStore()
        changed = datetime(2026, 8, 17, 9, 0, tzinfo=timezone.utc)
        store.unchanged.add(("equipment", "BSR-101", "source_changed_at", changed))
        client = FakeClient([SAMPLE_ASSET])
        stats = SyncService(client, store).sync(self.CFG)
        self.assertEqual(stats.upserted, 0)
        self.assertEqual(stats.skipped, 1)
        self.assertEqual(store.entities, [])

    def test_custom_scope_is_forwarded(self):
        store, client = FakeStore(), FakeClient([])
        cfg = ObjectSyncConfig(
            object_structure="mxapilabor", entity_name="labor",
            mapper=lambda m: None, watermark_field=None,
            scope_clause='worksite="BSR"', compare_column=None,
        )
        SyncService(client, store).sync(cfg)
        self.assertEqual(client.calls[0]["where"], 'worksite="BSR"')
        self.assertEqual(client.calls[0]["required_scope"], 'worksite="BSR"')

    def test_work_order_prefix_is_validated_without_legacy_query_predicate(self):
        cfg = ObjectSyncConfig(
            object_structure="mxwodetail", entity_name="work_order",
            mapper=lambda member: member,
            prefix_field="wonum", allowed_prefixes=("BSR",), prefix_query=False,
        )
        store = FakeStore()
        client = FakeClient([SAMPLE_BSR_WO, SAMPLE_WO])
        stats = SyncService(client, store).sync(cfg)
        self.assertEqual(client.calls[0]["where"], 'siteid="BSR"')
        self.assertNotIn("like", client.calls[0]["where"])
        self.assertEqual(stats.rows_seen, 2)
        self.assertEqual(stats.upserted, 1)
        self.assertEqual(stats.skipped, 1)

    def test_select_is_forwarded_to_oslc_client(self):
        select = ("wonum", "changedate")
        cfg = ObjectSyncConfig(
            object_structure="mxwodetail", entity_name="work_order",
            mapper=lambda member: member, watermark_field=None, order_by=None, select=select,
        )
        store, client = FakeStore(), FakeClient([])
        SyncService(client, store).sync(cfg)
        self.assertEqual(client.calls[0]["select"], list(select) + ["reportdate"])

    def test_batch_upsert_deduplicates_duplicate_entity_ids(self):
        cfg = ObjectSyncConfig(
            object_structure="mxperson", entity_name="person",
            mapper=lambda member: SimpleNamespace(id=member["id"]),
            watermark_field=None, order_by=None, batch_size=100,
        )
        store, client = FakeStore(), FakeClient([
            {"id": "P-1"}, {"id": "P-1"}, {"id": "P-2"},
        ])
        stats = SyncService(client, store).sync(cfg)
        self.assertEqual(stats.upserted, 2)
        self.assertEqual(stats.skipped, 1)

    def test_runtime_work_order_and_person_queries_are_bounded(self):
        asset = sync_config_for("mxapiasset")
        work_order = sync_config_for("mxwodetail")
        person = sync_config_for("mxperson")
        self.assertEqual(work_order.order_by, "-changedate")
        self.assertTrue(work_order.recent_work_orders)
        self.assertTrue(work_order.cursor_requires_zero_errors)
        self.assertEqual(work_order.max_pages, 20)
        self.assertEqual(work_order.scope_clause, 'siteid="BSR"')
        self.assertEqual(work_order.allowed_prefixes, ("BSR",))
        self.assertIn("wonum", work_order.select)
        self.assertIn("orgid", work_order.select)
        self.assertEqual(work_order.batch_size, 100)
        self.assertEqual(work_order.page_size, 25)
        self.assertTrue(work_order.prefix_query)
        self.assertFalse(work_order.watermark_query)
        self.assertEqual(person.scope_clause, 'locationorg="IP"')
        self.assertIn("personid", person.select)
        self.assertIn("assetnum", asset.select)
        self.assertIn("failurecode", asset.select)
        self.assertIsNone(asset.page_size)  # runtime default is 100; repair pins it explicitly
        self.assertEqual(asset.max_pages, 1000)

    def test_equipment_unit_is_applied_and_non_cs01_is_rejected(self):
        cfg = ObjectSyncConfig(
            object_structure="mxapiasset", entity_name="equipment",
            mapper=lambda member: member,
            required_values=(("eq11", "CS01"),),
        )
        store = FakeStore()
        client = FakeClient([
            {**SAMPLE_ASSET, "eq11": "CS01"},
            {**SAMPLE_ASSET, "assetnum": "CS02-ASSET", "eq11": "CS02"},
        ])
        stats = SyncService(client, store).sync(cfg)
        self.assertIn('siteid="BSR" and eq11="CS01"', client.calls[0]["where"])
        self.assertEqual(stats.rows_seen, 2)
        self.assertEqual(stats.upserted, 1)
        self.assertEqual(stats.skipped, 1)

    def test_run_logged(self):
        store, client = FakeStore(), FakeClient([SAMPLE_ASSET])
        SyncService(client, store).sync(self.CFG)
        self.assertEqual(len(store.runs), 1)
        self.assertIsNotNone(store.runs[0].finished_at)

    def test_pagination_cap_keeps_progress_but_does_not_advance_cursor(self):
        cfg = ObjectSyncConfig(
            object_structure="mxwodetail",
            entity_name="work_order",
            mapper=work_order_from_payload,
            prefix_field="wonum",
            allowed_prefixes=("BSR",),
        )

        class CappedClient(FakeClient):
            def iterate(self, *args, **kwargs):
                yield SAMPLE_BSR_WO
                raise OslcPaginationLimitError(
                    "mxwodetail", pages=1000, max_pages=1000,
                    next_page_fingerprint="safe-fingerprint",
                )

        store, client = FakeStore(), CappedClient([])
        stats = SyncService(client, store).sync(cfg)
        self.assertFalse(stats.complete)
        self.assertEqual(stats.mode, "partial")
        self.assertEqual(stats.pagination_error, "OslcPaginationLimitError")
        self.assertEqual(stats.upserted, 1)
        self.assertNotIn("mxwodetail", store.cursors)

    def test_cursor_independent_backfill_does_not_create_cursor(self):
        cfg = ObjectSyncConfig(
            object_structure="mxwodetail",
            entity_name="work_order",
            mapper=work_order_from_payload,
            watermark_field=None,
            prefix_field="wonum",
            allowed_prefixes=("BSR",),
            prefix_query=True,
            max_pages=2,
        )
        store, client = FakeStore(), FakeClient([SAMPLE_BSR_WO])
        stats = SyncService(client, store).sync(cfg)
        self.assertTrue(stats.complete)
        self.assertEqual(stats.upserted, 1)
        self.assertNotIn("mxwodetail", store.cursors)

    def test_transport_failure_is_partial_and_does_not_advance_cursor(self):
        class FailingClient(FakeClient):
            def iterate(self, *args, **kwargs):
                yield SAMPLE_ASSET
                raise OslcError("synthetic transport interruption")

        cfg = ObjectSyncConfig(
            object_structure="mxapiasset",
            entity_name="equipment",
            mapper=equipment_from_payload,
            cursor_requires_zero_errors=True,
        )
        store = FakeStore()
        stats = SyncService(FailingClient([]), store).sync(cfg)
        self.assertFalse(stats.complete)
        self.assertEqual(stats.mode, "partial")
        self.assertEqual(stats.pagination_error, "OslcError")
        self.assertEqual(stats.upserted, 1)
        self.assertNotIn("mxapiasset", store.cursors)
        self.assertEqual(store.runs[0].mode, "partial")

    def test_baseline_mapping_error_is_partial_and_does_not_advance_cursor(self):
        cfg = ObjectSyncConfig(
            object_structure="mxapiasset",
            entity_name="equipment",
            mapper=equipment_from_payload,
            cursor_requires_zero_errors=True,
        )
        store = FakeStore()
        stats = SyncService(FakeClient([{"eq11": "CS01", "changedate": SAMPLE_ASSET["changedate"]}]), store).sync(cfg)
        self.assertFalse(stats.complete)
        self.assertEqual(stats.mode, "partial")
        self.assertEqual(stats.pagination_error, "MAPPING_ERRORS")
        self.assertEqual(stats.errors, 1)
        self.assertNotIn("mxapiasset", store.cursors)


if __name__ == "__main__":
    unittest.main()
