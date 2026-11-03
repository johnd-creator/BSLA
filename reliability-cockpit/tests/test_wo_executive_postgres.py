"""Mandatory PG16 execution: no skipped/SQLite substitute for JSON/cast safety."""
import os
from sqlalchemy.engine import make_url
from sqlalchemy import create_engine
import test_wo_executive_reconciliation as regressions
class ExecutivePostgresTest(regressions.ExecutiveEvidenceTest):
 def setUp(self):
  self.dsn=os.environ.get('NADI_MART_TEST_DSN','')
  url=make_url(self.dsn)
  if url.drivername!='postgresql+psycopg' or url.database!='nadi_mart_test' or url.host not in ('127.0.0.1','localhost','maximo-pg') or url.port!=5432 or url.username not in ('postgres','nadi_ci') or url.query:
   raise RuntimeError('dedicated disposable nadi_mart_test PostgreSQL required')
  self.fixture_engine=create_engine(self.dsn)
  with self.fixture_engine.connect() as connection:
   database,actor=connection.exec_driver_sql('SELECT current_database(),current_user').one()
   if database!='nadi_mart_test' or actor!=url.username:raise RuntimeError('disposable target identity mismatch')
  super().setUp()
