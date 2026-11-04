"""PostgreSQL-only synthetic concurrency tests. Invoked by guarded CI runner."""
import os
import threading
import time
import unittest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from test_wo_actual_date_rollback import RollbackScenarios
from test_wo_actual_dates import RAW
from src.config import DbConfig
from src.repositories.database import Database, Base
from src.repositories import models, mart_models
from src.services.wo_actual_date_recovery import rollback_cohort


class PostgresRollbackTest(RollbackScenarios, unittest.TestCase):
    target = "maximo_collector"

    def setUp(self):
        dsn = os.environ["NADI_TEST_POSTGRES_DSN"]
        url = make_url(dsn)
        if (url.host not in ("127.0.0.1", "maximo-pg") or url.username != "nadi_ci"
                or url.database != "maximo_collector" or url.drivername != "postgresql+psycopg"
                or os.environ.get("NADI_SYNTHETIC_POSTGRES") != "1"):
            raise RuntimeError("synthetic PostgreSQL target required")
        self.db = Database(DbConfig(dsn))
        with self.db.session() as s:
            if s.scalar(text("select rolsuper from pg_roles where rolname=current_user")):
                raise RuntimeError("synthetic tests require non-superuser owner")
        self.db.create_all(); self.saved = []

    def tearDown(self):
        # Dedicated ephemeral database. Never used against a restored plant DB.
        Base.metadata.drop_all(self.db.engine)
        self.db.engine.dispose()

    def test_worker_commit_while_rollback_waits_for_row_lock(self):
        self.prepare(); errors = []; done = threading.Event(); results = []
        held = self.db.engine.connect(); tx = held.begin()
        held.execute(text("select id from work_order where id=:id for update"), {"id": RAW["wonum"]})
        held.execute(text("update work_order set status='CAN' where id=:id"), {"id": RAW["wonum"]})
        held.execute(text("update maintenance_event set failure_code='CONCURRENT'"))
        def rollback():
            try: results.append(self.rollback())
            except Exception as e: errors.append(e)
            finally: done.set()
        t = threading.Thread(target=rollback); t.start()
        try:
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                with self.db.session() as s:
                    waiting = s.scalar(text("select count(*) from pg_locks where not granted and pid in (select pid from pg_stat_activity where datname=current_database() and usename=current_user)"))
                if waiting: break
                time.sleep(.02)
            self.assertTrue(waiting, "rollback must actually wait for the independent writer")
            self.assertFalse(done.is_set()); tx.commit()
            self.assertTrue(done.wait(10)); self.assertEqual(errors, []); self.assertRestored(results[0])
            current = self.snapshots()[RAW["wonum"]]
            self.assertEqual(current["legacy"]["status"], "CAN")
            self.assertEqual(current["mart"]["failure_code"], "CONCURRENT")
        finally:
            if tx.is_active: tx.rollback()
            held.close(); t.join(10)

    def test_newer_writer_commits_before_rollback_acquires_locks(self):
        self.prepare(); self.worker(dict(RAW, changedate="2026-09-04T00:00:00Z", actstart="2026-09-01T01:00:00Z"))
        with self.assertRaises(ValueError): self.rollback()

    def test_postgres_requires_durable_rollback_checkpoint(self):
        self.prepare()
        with self.assertRaises(ValueError):
            rollback_cohort(self.db, self.receipt, expected_database=self.target)
        self.assertIsNotNone(self.snapshots()[RAW["wonum"]]["mart"]["actual_start"])
