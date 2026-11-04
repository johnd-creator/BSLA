"""Synthetic qualification tests. No source request or external DB is permitted."""
import fnmatch
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import yaml

TOOLS = Path(__file__).resolve().parents[1]
WORKFLOW = TOOLS.parents[1] / 'workflows/nadi-maximo-collector.yml'
spec = importlib.util.spec_from_file_location('maximo_qualify', TOOLS / 'qualify.py')
q = importlib.util.module_from_spec(spec)
spec.loader.exec_module(q)
HEAD = 'f16ff508f07efd56535553f49e6f0007273a44e0'


def pr():
    return {'number': 91, 'state': 'open', 'merged_at': None,
            'head': {'sha': HEAD, 'repo': {'full_name': q.REPOSITORY}},
            'base': {'ref': 'main', 'repo': {'full_name': q.REPOSITORY}}}


class SelectionTests(unittest.TestCase):
    def test_valid_exact_head(self):
        self.assertEqual(q.validate_pr(pr(), q.REPOSITORY, '91', HEAD), HEAD)

    def test_reject_stale_head(self):
        with self.assertRaisesRegex(ValueError, 'STALE_PR_HEAD'):
            q.validate_pr(pr(), q.REPOSITORY, '91', 'a' * 40)

    def test_wrong_pr(self):
        with self.assertRaisesRegex(ValueError, 'WRONG_PR'):
            q.validate_pr(pr(), q.REPOSITORY, '92', HEAD)

    def test_reject_repository_and_forks(self):
        with self.assertRaisesRegex(ValueError, 'UNEXPECTED_REPOSITORY'):
            q.validate_pr(pr(), 'someone/else', '91', HEAD)
        for side in ('head', 'base'):
            payload = pr()
            payload[side]['repo']['full_name'] = 'someone/fork'
            with self.assertRaisesRegex(ValueError, 'UNEXPECTED_PR_REPOSITORY'):
                q.validate_pr(payload, q.REPOSITORY, '91', HEAD)

    def test_closed_or_merged(self):
        for change in ({'state': 'closed'}, {'merged_at': '2026-10-16'}):
            with self.assertRaisesRegex(ValueError, 'PR_NOT_OPEN_UNMERGED'):
                q.validate_pr(pr() | change, q.REPOSITORY, '91', HEAD)

    def test_invalid_sha_or_number(self):
        for number, sha in [('0', HEAD), ('91; echo bad', HEAD), ('91', 'main'),
                            ('91', 'refs/pull/91/head'), ('91', HEAD[:12]),
                            ('91', HEAD.upper()), ('91', HEAD + '\n')]:
            with self.assertRaises(ValueError):
                q.validate_request(q.REPOSITORY, number, sha)

    def test_missing_pr_and_failed_metadata(self):
        import urllib.error
        for error in (urllib.error.HTTPError('mock', 404, 'missing', {}, None),
                      urllib.error.URLError('unavailable')):
            with patch.dict(os.environ, {'GH_TOKEN': 'synthetic'}), \
                    patch.object(q.urllib.request, 'urlopen', side_effect=error):
                with self.assertRaisesRegex(ValueError, 'PR_METADATA_UNAVAILABLE'):
                    q.current_pr(q.REPOSITORY, '91', HEAD)

    def test_recheck_catches_head_movement(self):
        payload = pr()
        payload['head']['sha'] = 'a' * 40
        with patch.dict(os.environ, {'GH_TOKEN': 'synthetic'}), \
                patch.object(q.urllib.request, 'urlopen') as request:
            request.return_value.__enter__.return_value.read.return_value = json.dumps(payload)
            with self.assertRaisesRegex(ValueError, 'STALE_PR_HEAD'):
                q.current_pr(q.REPOSITORY, '91', HEAD)

    def test_dispatch_default_branch_only(self):
        self.assertEqual(q.select('workflow_dispatch', {}, q.REPOSITORY,
                                  'refs/heads/main', 'b' * 40, '91', HEAD), ('91', HEAD))
        with self.assertRaisesRegex(ValueError, 'DEFAULT_BRANCH'):
            q.select('workflow_dispatch', {}, q.REPOSITORY, 'refs/heads/feature', HEAD, '91', HEAD)

    def test_event_selection(self):
        self.assertEqual(q.select('pull_request', {'number': 91, 'pull_request': pr()},
                                  q.REPOSITORY, 'refs/pull/91/merge', 'a' * 40), ('91', HEAD))
        self.assertEqual(q.select('push', {}, q.REPOSITORY, 'refs/heads/main', HEAD), ('', HEAD))
        with self.assertRaises(ValueError):
            q.select('pull_request_target', {}, q.REPOSITORY, 'refs/heads/main', HEAD)

    def test_checkout_rejects_wrong_sha_origin_or_dirty(self):
        correct = [HEAD, f'https://github.com/{q.REPOSITORY}', '']
        with patch.object(q.subprocess, 'check_output', side_effect=correct):
            q.verify_checkout('/synthetic', HEAD)
        for values in [['a' * 40], [HEAD, 'https://github.com/other/repo'],
                       correct[:2] + [' M src.py']]:
            with patch.object(q.subprocess, 'check_output', side_effect=values):
                with self.assertRaises(ValueError):
                    q.verify_checkout('/synthetic', HEAD)


class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # BaseLoader avoids YAML 1.1 treating GitHub's `on` key as a boolean.
        cls.workflow = yaml.load(WORKFLOW.read_text(), Loader=yaml.BaseLoader)

    def test_triggers(self):
        events = self.workflow['on']
        self.assertEqual(set(events), {'pull_request', 'push', 'workflow_dispatch'})
        for event in ('pull_request', 'push'):
            patterns = events[event]['paths']
            cases = {'maximo-collector/src/services/sync.py': True,
                     'maximo-collector/tests/test_cursor_recovery.py': True,
                     'maximo-collector/pyproject.toml': True,
                     'reliability-data-contracts/schemas/equipment.schema.json': True,
                     '.github/scripts/maximo_ci/run_offline.py': True,
                     '.github/workflows/nadi-maximo-collector.yml': True,
                     'docs/ci/NADI-AUD-04A-MAXIMO-CI.md': True,
                     'README.md': False, 'docs/design/NADI-UI-SPEC.md': False,
                     'pi-collector/src/config.py': False}
            for path, expected in cases.items():
                with self.subTest(event=event, path=path):
                    self.assertEqual(any(fnmatch.fnmatchcase(path, p) for p in patterns), expected)

    def test_read_only_pinned_no_services_or_secret_context(self):
        workflow = self.workflow
        self.assertEqual(workflow['permissions'], {'contents': 'read'})
        job = workflow['jobs']['collector']
        self.assertEqual(job['runs-on'], 'ubuntu-latest')
        self.assertNotIn('services', job)
        self.assertTrue(all(value == 'read' for j in workflow['jobs'].values()
                            for value in j.get('permissions', {}).values()))
        text = WORKFLOW.read_text()
        self.assertNotIn('secrets.', text)
        self.assertNotIn('pull_request_target', text)
        self.assertNotIn('continue-on-error', text)
        self.assertNotIn('.venv', text)
        self.assertEqual(job['strategy']['matrix']['python'], ['3.11', '3.12'])
        for step in [s for j in workflow['jobs'].values() for s in j['steps']]:
            if 'uses' in step:
                self.assertRegex(step['uses'], r'@[a-f0-9]{40}$')
            if step.get('uses', '').startswith('actions/checkout@'):
                self.assertEqual(step['with']['persist-credentials'], 'false')

    def test_gate_and_token_isolation(self):
        jobs = self.workflow['jobs']
        self.assertEqual(jobs['gate']['needs'], ['select', 'collector', 'postgres'])
        self.assertEqual(jobs['gate']['if'], '${{ always() }}')
        self.assertEqual(jobs['collector']['needs'], 'select')
        self.assertFalse(any('GH_TOKEN' in step.get('env', {}) for step in jobs['collector']['steps']))
        failure_gate = next(s for s in jobs['gate']['steps'] if 'SELECTION_RESULT' in s.get('env', {}))
        for selection, collector, expected in [('success', 'success', 0), ('success', 'failure', 1),
                                                ('failure', 'skipped', 1), ('success', 'cancelled', 1)]:
            result = subprocess.run(['bash', '-e', '-c', failure_gate['run']],
                                    env={'SELECTION_RESULT': selection, 'COLLECTOR_RESULT': collector, 'POSTGRES_RESULT':'success'},
                                    capture_output=True, timeout=5)
            self.assertEqual(result.returncode, expected)

    def test_pg_lane_failures_block_gate(self):
        jobs = self.workflow['jobs']
        self.assertEqual(jobs['postgres']['strategy']['matrix']['python'], ['3.11','3.12'])
        self.assertFalse(any('GH_TOKEN' in step.get('env', {}) for step in jobs['postgres']['steps']))
        gate = next(s for s in jobs['gate']['steps'] if 'SELECTION_RESULT' in s.get('env', {}))
        for value in ('failure','cancelled','skipped',''):
            result = subprocess.run(['bash','-e','-c',gate['run']],
                env={'SELECTION_RESULT':'success','COLLECTOR_RESULT':'success','POSTGRES_RESULT':value},
                capture_output=True, timeout=5)
            self.assertNotEqual(result.returncode,0)


class OfflineRunnerTests(unittest.TestCase):
    def invoke(self, body, *, empty=False, private_env=False):
        with tempfile.TemporaryDirectory(prefix='maximo-ci-test-') as tmp:
            root = Path(tmp)
            (root / 'tests').mkdir()
            if not empty:
                (root / 'tests/test_synthetic.py').write_text('import unittest\n' + body)
            if private_env:
                (root / '.env').write_text('PRIVATE_CANARY=must-not-load\n')
            report = root / 'result.json'
            process = subprocess.run(
                [sys.executable, str(TOOLS / 'run_offline.py'), '--root', str(root),
                 '--sha', HEAD, '--report', str(report)],
                env={key: value for key, value in os.environ.items()
                     if key not in ('GITHUB_STEP_SUMMARY', 'GH_TOKEN')},
                capture_output=True, text=True, timeout=30,
            )
            return process.returncode, json.loads(report.read_text()), process.stderr

    def test_real_discovery_and_execution(self):
        code, report, _ = self.invoke('class T(unittest.TestCase):\n def test_one(self): self.assertTrue(True)\n')
        self.assertEqual(code, 0)
        self.assertEqual((report['discovered'], report['tests'], report['conclusion']), (1, 1, 'PASS'))

    def test_intentional_failure_propagates(self):
        code, report, _ = self.invoke('class T(unittest.TestCase):\n def test_bad(self): self.fail("synthetic")\n')
        self.assertEqual(code, 1)
        self.assertEqual(report['failures'], 1)

    def test_skips_expected_failure_and_empty_fail_closed(self):
        bodies = ['class T(unittest.TestCase):\n @unittest.skip("synthetic")\n def test_s(self): pass\n',
                  'class T(unittest.TestCase):\n @unittest.expectedFailure\n def test_e(self): self.fail()\n']
        for body in bodies:
            code, report, _ = self.invoke(body)
            self.assertEqual(code, 1)
            self.assertEqual(report['conclusion'], 'FAIL')
        code, report, _ = self.invoke('', empty=True)
        self.assertEqual((code, report['discovered']), (1, 0))

    def test_discovery_error_fails(self):
        code, report, _ = self.invoke('raise RuntimeError("synthetic import error")\n')
        self.assertEqual(code, 1)
        self.assertEqual(report['errors'], 1)

    def test_blocked_io_even_if_caught(self):
        operations = [
            ('import socket', 'socket.create_connection(("192.0.2.1", 9))'),
            ('import sys', 'sys.audit("socket.connect", None, ("192.0.2.1", 9))'),
            ('import socket', 'socket.getaddrinfo("example.invalid", 80)'),
            ('from sqlalchemy import create_engine', 'create_engine("postgresql+psycopg://x:x@192.0.2.1/x").connect()'),
            ('import psycopg', 'psycopg.connect("host=192.0.2.1 dbname=synthetic")'),
            ('import sqlite3', 'sqlite3.connect("not-allowed.db")'),
            ('import subprocess', 'subprocess.run(["true"])'),
        ]
        for imports, operation in operations:
            with self.subTest(operation=operation):
                code, report, _ = self.invoke(imports + '\nclass T(unittest.TestCase):\n'
                    ' def test_io(self):\n  try: ' + operation + '\n  except AssertionError: pass\n')
                self.assertEqual(code, 1)
                self.assertGreater(report['blocked_external_io'], 0)

    def test_in_memory_sqlite_allowed(self):
        code, report, _ = self.invoke('from sqlalchemy import create_engine\nclass T(unittest.TestCase):\n'
            ' def test_memory(self):\n  with create_engine("sqlite://").connect() as c: pass\n')
        self.assertEqual(code, 0)
        self.assertEqual(report['blocked_external_io'], 0)

    def test_dotenv_is_suppressed_and_environment_scrubbed(self):
        with patch.dict(os.environ, {'MAXIMO_PASSWORD': 'synthetic', 'DATABASE_URL': 'synthetic'}):
            code, report, _ = self.invoke('import os\nfrom dotenv import load_dotenv\n'
                'class T(unittest.TestCase):\n def test_private(self):\n'
                '  load_dotenv(".env")\n  self.assertNotIn("PRIVATE_CANARY", os.environ)\n'
                '  self.assertNotIn("MAXIMO_PASSWORD", os.environ)\n'
                '  self.assertNotIn("DATABASE_URL", os.environ)\n', private_env=True)
        self.assertEqual(code, 0)
        self.assertEqual(report['conclusion'], 'PASS')


if __name__ == '__main__':
    unittest.main()


class DisposableFixtureGuardTests(unittest.TestCase):
    def setUp(self):
        module = importlib.util.spec_from_file_location('projection_pg_runner', TOOLS / 'run_projection_pg.py')
        self.runner = importlib.util.module_from_spec(module)
        module.loader.exec_module(self.runner)
        self.params = dict(host='/tmp/private-fixture/socket',port='16479',
            dbname='nadi_aud02b_disposable',user='nadi_b1_fixture')

    def test_only_exact_private_socket_and_owner_allowed(self):
        self.assertTrue(self.runner.fixture_connection_allowed(self.params,'/tmp/private-fixture/socket',16479))
        for key,value in (('host','127.0.0.1'),('host','/tmp/other/socket'),('port',15443),
                          ('dbname','maximo_collector'),('dbname','nadi_local_dev_01_test'),
                          ('user','postgres'),('password','synthetic'),('service','other'),('hostaddr','127.0.0.1')):
            with self.subTest(key=key,value=value):
                self.assertFalse(self.runner.fixture_connection_allowed(self.params|{key:value},
                    '/tmp/private-fixture/socket',16479))
