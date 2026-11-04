"""Same detail recovery scenarios on dedicated synthetic PostgreSQL."""
import test_wo_detail_reconciliation as detail_fixtures
import test_wo_actual_date_postgres as pg_fixtures
class PostgresDetailTest(detail_fixtures.DetailTest):
 target="maximo_collector"
 def setUp(self):
  pg_fixtures.PostgresRollbackTest.setUp(self)
  self.seed_detail()
 def tearDown(self): pg_fixtures.PostgresRollbackTest.tearDown(self)
