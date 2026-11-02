"""Hermetic retained-Maximo hierarchy scope, lineage and query-budget tests."""
import unittest
from tempfile import TemporaryDirectory
from datetime import datetime, timezone

from sqlalchemy import event, select, func
from sqlalchemy.orm import Session

from src.config import MartDbConfig
from src.repositories.mart_database import MartDatabase
from src.repositories.mart_models import AssetMasterMart as Asset, ReliabilityAssetRegistryMart as Registry, MartBase
from src.services.asset_hierarchy import read_hierarchy, MAX_DEPTH

PREFIX = "asset:MAXIMO:MXASSET:BSR:IP:"
NOW = datetime(2026, 2, 1, tzinfo=timezone.utc)


class HierarchyTest(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix="nadi-hierarchy-test-")
        self.database = MartDatabase(MartDbConfig(dsn="sqlite+pysqlite:///"+self.temp.name+"/fixture.sqlite"))
        MartBase.metadata.create_all(self.database.engine)
        self.statements = []
        event.listen(self.database.engine, "before_cursor_execute", self.capture)
        self.add("SYSTEM")
        self.add("ROOT", parent="SYSTEM", registered=True, children=True)
        self.add("PART-A", parent="ROOT", children=True)
        self.add("PART-B", parent="ROOT")
        self.add("SUBPART", parent="PART-A")
        self.add("SIBLING", parent="SYSTEM", registered=True)
        self.add("FOREIGN", parent="ROOT", site="OTHER")
        self.statements.clear()

    def tearDown(self):
        self.database.engine.dispose()
        self.temp.cleanup()

    def capture(self, conn, cursor, statement, parameters, context, executemany):
        self.statements.append(statement)

    def add(self, name, *, parent=None, registered=False, children=None, site="BSR", description="Synthetic retained equipment"):
        ref = PREFIX + name
        with Session(self.database.engine) as session:
            session.add(Asset(canonical_id=ref, contract_version="1.0", source_asset_number=name,
                parent_asset_ref=PREFIX+parent if parent else None, description=description,
                site_code=site, organization_code="IP", asset_type="PRODUCTION", status="OPERATING", unit="SYNTHETIC",
                source_updated_at=NOW, provenance={}, relationship_evidence={},
                sources={"maximo":{"children":children,"mainstr":"PM","private_field":"must not be exposed"}},
                mart_created_at=NOW, mart_updated_at=NOW))
            if registered:
                session.add(Registry(asset_ref=ref, source_asset_number=name, site_code=site, organization_code="IP",
                    registry_source="SYNTHETIC", snapshot_sha256="a"*64, snapshot_row_count=2, snapshot_imported_at=NOW))
            session.commit()

    def test_direct_children_are_paged_scoped_and_not_registered(self):
        page = read_hierarchy(self.database, PREFIX+"ROOT", limit=1)
        self.assertEqual((page.total,page.has_more,page.items[0].source_asset_number), (2,True,"PART-A"))
        self.assertFalse(page.items[0].registered)
        self.assertEqual(page.items[0].hierarchy_role,"UNKNOWN")
        self.assertEqual(page.items[0].asset_type,"PRODUCTION")
        self.assertEqual(page.items[0].source_has_children,True)
        self.assertEqual(read_hierarchy(self.database,PREFIX+"ROOT",offset=1,limit=1).items[0].source_asset_number,"PART-B")
        self.assertNotIn("private_field",page.model_dump_json())
        self.assertNotIn("mainstr",page.model_dump_json())

    def test_descendant_proof_and_ancestor_lineage(self):
        page = read_hierarchy(self.database,PREFIX+"ROOT",node_ref=PREFIX+"PART-A")
        self.assertEqual([r.source_asset_number for r in page.path],["ROOT","PART-A"])
        self.assertEqual([r.source_asset_number for r in page.ancestors],["SYSTEM"])
        self.assertEqual([r.source_asset_number for r in page.items],["SUBPART"])
        self.assertEqual(page.ancestor_state,"NO_RETAINED_PARENT")
        self.assertLessEqual(len(self.statements),7)

    def test_unregistered_root_is_rejected_before_children_count(self):
        self.assertIsNone(read_hierarchy(self.database,PREFIX+"SYSTEM"))
        self.assertEqual(len(self.statements),1)
        self.assertNotIn("count(",self.statements[0].lower())

    def test_off_root_sibling_or_foreign_node_is_denied_before_counts(self):
        for node in ["SIBLING","SYSTEM","FOREIGN","MISSING"]:
            self.statements.clear()
            self.assertIsNone(read_hierarchy(self.database,PREFIX+"ROOT",node_ref=PREFIX+node))
            self.assertFalse(any("count(" in sql.lower() for sql in self.statements))

    def test_missing_children_never_claims_source_leaf_or_complete(self):
        self.add("GAPPED",registered=True,children=True,parent="NOT-RETAINED")
        page = read_hierarchy(self.database,PREFIX+"GAPPED")
        self.assertEqual((page.total,page.completeness,page.node.source_has_children),(0,"PARTIAL",True))
        self.assertEqual(page.ancestor_state,"UNRESOLVED_PARENT")
        self.assertEqual(page.unresolved_parent_ref,PREFIX+"NOT-RETAINED")

    def test_parent_cycle_and_depth_limit_are_explicit(self):
        with Session(self.database.engine) as s:
            s.get(Asset,PREFIX+"SYSTEM").parent_asset_ref=PREFIX+"ROOT"
            s.commit()
        self.assertEqual(read_hierarchy(self.database,PREFIX+"ROOT").ancestor_state,"CYCLE")
        previous=None
        for n in range(MAX_DEPTH+1):
            self.add(f"DEEP-{n}",parent=previous)
            previous=f"DEEP-{n}"
        self.add("DEEP-ROOT",parent=previous,registered=True)
        page=read_hierarchy(self.database,PREFIX+"DEEP-ROOT")
        self.assertEqual(page.ancestor_state,"DEPTH_LIMIT")
        self.assertEqual(len(page.ancestors),MAX_DEPTH)

    def test_outside_parent_is_not_serialized(self):
        with Session(self.database.engine) as s:
            s.get(Asset,PREFIX+"ROOT").parent_asset_ref="asset:MAXIMO:MXASSET:OTHER:IP:SECRET"
            s.commit()
        page=read_hierarchy(self.database,PREFIX+"ROOT")
        self.assertEqual(page.ancestor_state,"OUT_OF_SCOPE_PARENT")
        self.assertIsNone(page.node.parent_asset_ref)
        self.assertNotIn("SECRET",page.model_dump_json())

    def test_invalid_identifiers_and_pages_fail_closed(self):
        for ref in ["", "../ROOT", "asset:OTHER:ROOT",PREFIX+"bad%2fref"]:
            self.assertIsNone(read_hierarchy(self.database,ref))
        self.assertEqual(self.statements,[])
        for offset,limit in [(-1,25),(10001,25),(0,51),(True,25),(0,False)]:
            with self.assertRaisesRegex(ValueError,"HIERARCHY_PAGE_INVALID"):
                read_hierarchy(self.database,PREFIX+"ROOT",offset=offset,limit=limit)

    def test_long_description_is_explicit_preview_and_reads_do_not_mutate(self):
        self.add("LONG",parent="ROOT",description="x"*1001)
        page=read_hierarchy(self.database,PREFIX+"ROOT",node_ref=PREFIX+"LONG")
        self.assertEqual(len(page.node.description),1000)
        self.assertTrue(page.node.description_shortened)
        self.assertTrue(all(sql.lstrip().upper().startswith("SELECT") for sql in self.statements if "INSERT" not in sql))
        with self.database.read_session() as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(Registry)),2)

    def test_http_route_validates_page_and_preserves_root_boundary(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from src.api import reliability
        app=FastAPI()
        app.include_router(reliability.router)
        app.dependency_overrides[reliability._db]=lambda:self.database
        client=TestClient(app)
        url='/v1/reliability/assets/'+PREFIX+'ROOT/hierarchy'
        response=client.get(url)
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['root_ref'],PREFIX+'ROOT')
        self.assertEqual(client.get(url,params={'limit':51}).status_code,422)
        self.assertEqual(client.get(url,params={'node_ref':PREFIX+'SIBLING'}).status_code,404)
        self.assertEqual(client.get(url.replace('ROOT/hierarchy','SYSTEM/hierarchy')).status_code,404)


if __name__ == "__main__":
    unittest.main()
