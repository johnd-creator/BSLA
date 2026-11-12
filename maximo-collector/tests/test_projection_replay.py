"""Pure policy/disabled entrypoints; no DB, source I/O or fixture credentials."""
import unittest
from sqlalchemy.dialects import postgresql
from src.repositories.database import Base
from src.repositories.replay_store import ReplayStore, ReplayPolicy, targeted_scope
from src.repositories.projection_store import CaptureError, ProjectionStore, SCOPE
from src.repositories.deferred_store import POLICY_EPOCH
from src.services.projection_replay import ProjectionReplay

class ReplayPolicyTest(unittest.TestCase):
    def test_disabled_store_never_connects(self):
        with self.assertRaisesRegex(CaptureError,'disabled'): ReplayStore(None)

    def test_disabled_service_never_claims(self):
        with self.assertRaisesRegex(CaptureError,'disabled'): ProjectionReplay(None)

    def test_operational_metadata_unchanged(self):
        self.assertFalse(any(t.startswith('mart_replay_') for t in Base.metadata.tables))

    def test_bounded_policy_rejects_invalid_limits(self):
        for kw in ({'max_attempts':0},{'max_probes':65},{'seconds':31},{'work':6},{'max_events':257},
                   {'base_backoff':0},{'max_backoff':86401},{'max_attempts':True},{'seconds':1.5}):
            with self.subTest(kw=kw),self.assertRaises(ValueError): ReplayPolicy(**kw)

    def test_backoff_finite_deterministic(self):
        p=ReplayPolicy(base_backoff=2,max_backoff=10)
        self.assertEqual([p.delay(i) for i in range(1,7)],[2,4,8,10,10,10])
        with self.assertRaises(ValueError): p.delay(0)

    def test_targeted_scope_cannot_be_full_scope(self):
        scope=targeted_scope({'id':'f'*64,'source_id':'BSR001'})
        self.assertNotEqual(scope,SCOPE)
        base=ProjectionStore.__new__(ProjectionStore)
        self.assertFalse(base._scope_compatible(scope))

    def test_targeted_scope_strict_keys(self):
        store=ReplayStore.__new__(ReplayStore)
        scope=targeted_scope({'id':'f'*64,'source_id':'BSR001'})
        self.assertTrue(store._scope_compatible(scope))
        self.assertFalse(store._scope_compatible(dict(scope,arbitrary='x')))
        self.assertFalse(store._scope_compatible(dict(scope,policy_epoch='other')))
        self.assertFalse(store._scope_compatible(dict(scope,source_id='')))

    def test_due_query_keyset_has_no_source_scan(self):
        store=ReplayStore.__new__(ReplayStore); store.policy_digest='f'*64
        sql=str(store._due_query('maintenance_event',10).compile(dialect=postgresql.dialect()))
        self.assertIn('mart_replay_queue',sql); self.assertIn('ORDER BY mart_replay_queue.due_at',sql)
        self.assertNotIn('work_order',sql); self.assertNotIn('equipment',sql)

    def test_due_limit_validated_before_connection(self):
        store=ReplayStore.__new__(ReplayStore)
        for n in (0,21,True,1.5):
            with self.subTest(n=n),self.assertRaises(ValueError): store._due_query('maintenance_event',n)

    def test_unknown_domain_refused(self):
        store=ReplayStore.__new__(ReplayStore)
        with self.assertRaises(CaptureError): store._due_query('UNKNOWN',1)

    def test_invocation_deadline_is_reset_and_cannot_be_extended(self):
        from src.repositories.replay_store import INVOCATION_DEADLINE
        from src.repositories.projection_store import BudgetExceeded
        store=ReplayStore.__new__(ReplayStore); store.replay_policy=ReplayPolicy()
        with store.invocation() as outer:
            with store.invocation() as inner:
                self.assertLessEqual(inner,outer)
            self.assertEqual(INVOCATION_DEADLINE.get(),outer)
        self.assertIsNone(INVOCATION_DEADLINE.get())
        with self.assertRaises(RuntimeError):
            with store.invocation(): raise RuntimeError('synthetic')
        self.assertIsNone(INVOCATION_DEADLINE.get())

    def test_expired_invocation_refuses_before_sql(self):
        from src.repositories.replay_store import INVOCATION_DEADLINE
        from src.repositories.projection_store import BudgetExceeded
        token=INVOCATION_DEADLINE.set(0)
        try:
            with self.assertRaises(BudgetExceeded): ReplayStore.__new__(ReplayStore)._limits(None)
        finally: INVOCATION_DEADLINE.reset(token)
