"""Mandatory PG16 execution: no skipped/SQLite substitute for JSON/cast safety."""
import os
from sqlalchemy.engine import make_url
from sqlalchemy import create_engine
import test_wo_executive_reconciliation as regressions
class ExecutivePostgresTest(regressions.ExecutiveEvidenceTest):
 def setUp(self):
  self.dsn=os.environ.get('NADI_MART_TEST_DSN','')
  url=make_url(self.dsn)
  if url.get_backend_name()!='postgresql' or url.database!='nadi_mart_test' or url.host not in ('127.0.0.1','localhost','maximo-pg'):
   raise RuntimeError('dedicated disposable nadi_mart_test PostgreSQL required')
  self.fixture_engine=create_engine(self.dsn)
  super().setUp()
