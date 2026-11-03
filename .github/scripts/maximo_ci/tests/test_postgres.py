"""Negative runner boundaries; no PostgreSQL or source contact required."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

RUNNER = Path(__file__).resolve().parents[1] / "run_postgres.py"
DSN = "postgresql+psycopg://nadi_ci:synthetic-tests-only@127.0.0.1:5432/maximo_collector"


class PostgresRunnerPolicyTest(unittest.TestCase):
    def invoke(self, body, dsn=DSN):
        with tempfile.TemporaryDirectory(prefix="maximo-pg-runner-test-") as tmp:
            root = Path(tmp); (root / "postgres_tests").mkdir(); (root / "tests").mkdir()
            (root / "postgres_tests/test_synthetic.py").write_text(body)
            report = root / "report.json"
            env = dict(os.environ, NADI_TEST_POSTGRES_DSN=dsn, MAXIMO_PASSWORD="must-be-scrubbed", DATABASE_URL="must-be-scrubbed")
            result = subprocess.run([sys.executable, str(RUNNER), "--root", str(root), "--sha", "a"*40,
                                     "--report", str(report)], env=env, capture_output=True, text=True, timeout=15)
            return result, json.loads(report.read_text()) if report.exists() else None

    def test_rejects_non_synthetic_target_before_discovery(self):
        for dsn in (DSN.replace("127.0.0.1", "example.invalid"), DSN.replace("nadi_ci:", "postgres:"),
                    DSN.replace("maximo_collector", "other_database"), DSN + "?sslmode=disable"):
            result, _ = self.invoke("raise AssertionError('must not import')", dsn)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("synthetic-tests-only", result.stdout + result.stderr)

    def test_skips_and_empty_suite_cannot_pass(self):
        bodies = ("", "import unittest\nclass T(unittest.TestCase):\n @unittest.skip('not qualified')\n def test_skip(self): pass\n")
        for body in bodies:
            result, report = self.invoke(body)
            self.assertNotEqual(result.returncode, 0); self.assertEqual(report["conclusion"], "FAIL")

    def test_http_and_unapproved_database_are_denied(self):
        for body in ("import requests; requests.get('https://example.invalid')",
                     "from sqlalchemy import create_engine; create_engine('sqlite+pysqlite:///:memory:').connect()"):
            result, report = self.invoke("import unittest\nclass T(unittest.TestCase):\n def test_io(self):\n  " + body + "\n")
            self.assertNotEqual(result.returncode, 0); self.assertEqual(report["blocked_io"], 1)

    def test_source_environment_and_dotenv_are_disabled(self):
        body = "import unittest,os,dotenv\nclass T(unittest.TestCase):\n def test_guard(self):\n  self.assertNotIn('MAXIMO_PASSWORD',os.environ)\n  self.assertNotIn('DATABASE_URL',os.environ)\n  self.assertEqual(os.environ['PYTHON_DOTENV_DISABLED'],'1')\n  self.assertFalse(dotenv.load_dotenv())\n"
        result, report = self.invoke(body)
        self.assertEqual(result.returncode, 0); self.assertEqual(report["blocked_io"], 0)
