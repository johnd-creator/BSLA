"""CI-only synthetic PostgreSQL runner. Never loads operational environment.

Accidental-I/O guards are defense in depth; run only on disposable CI workers
without source credentials, host Docker sockets or production networking.
"""
import argparse
import contextlib
import json
import os
from pathlib import Path
import platform
import re
import socket
import sys
import unittest
from unittest.mock import patch


def run(root, sha, report):
    from sqlalchemy.engine import Engine, make_url
    root = root.resolve()
    dsn = os.environ.get("NADI_TEST_POSTGRES_DSN", "")
    url = make_url(dsn)
    if (url.drivername != "postgresql+psycopg" or url.host not in ("127.0.0.1", "maximo-pg")
            or url.username != "nadi_ci" or url.database != "maximo_collector"
            or url.port != 5432 or url.query):
        raise ValueError("unapproved synthetic PostgreSQL target")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    workflow = os.environ.get("CI_WORKFLOW_SHA", "LOCAL")
    run_url = os.environ.get("CI_RUN_URL", "LOCAL")
    for key in list(os.environ):
        if (key.startswith(("MAXIMO_", "PG", "NADI_", "RELIABILITY_", "COCKPIT_"))
                or key.endswith(("_DSN", "_TOKEN", "_PASSWORD", "_SECRET"))
                or key in ("DATABASE_URL", "DATABASE_ECHO", "GH_TOKEN")):
            os.environ.pop(key)
    os.environ.update(NADI_TEST_POSTGRES_DSN=dsn, NADI_SYNTHETIC_POSTGRES="1", PYTHON_DOTENV_DISABLED="1")
    os.chdir(root); sys.path[:0] = [str(root), str(root / "tests")]
    allowed_addresses = {item[4][0] for item in socket.getaddrinfo(url.host, url.port, type=socket.SOCK_STREAM)}
    blocked = []
    def deny(kind):
        blocked.append(kind)
        raise AssertionError("UNEXPECTED_EXTERNAL_IO:" + kind)
    def audit(event, args):
        if event in ("subprocess.Popen", "os.system", "socket.sendto", "socket.sendmsg"):
            deny(event)
        if event == "socket.connect" and (args[1][0] not in allowed_addresses or args[1][1] != 5432):
            deny("network")
        if event == "socket.getaddrinfo" and (args[0] not in ("127.0.0.1", "maximo-pg") or str(args[1]) != "5432"):
            deny("dns")
    sys.addaudithook(audit)
    original = Engine.connect
    def connect(engine, *args, **kwargs):
        if engine.url != url: return deny("database")
        return original(engine, *args, **kwargs)
    with contextlib.ExitStack() as stack:
        stack.enter_context(patch.object(Engine, "connect", connect))
        stack.enter_context(patch("dotenv.load_dotenv", return_value=False))
        stack.enter_context(patch("dotenv.main.load_dotenv", return_value=False))
        stack.enter_context(patch("requests.sessions.Session.request", lambda *a, **k: deny("http")))
        suite = unittest.defaultTestLoader.discover(str(root / "postgres_tests"))
        count = suite.countTestCases()
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    success = count > 0 and result.testsRun == count and result.wasSuccessful() and not (result.skipped or result.expectedFailures or blocked)
    record = {"tested_sha": sha, "workflow_sha": workflow, "run_url": run_url, "python": platform.python_version(),
              "tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
              "skips": len(result.skipped), "blocked_io": len(blocked), "conclusion": "PASS" if success else "FAIL"}
    report.write_text(json.dumps(record, indent=2) + "\n"); print(json.dumps(record))
    if summary:
        with open(summary, "a") as f: f.write("## Maximo PostgreSQL recovery qualification\n\n```json\n" + json.dumps(record, indent=2) + "\n```\n")
    return 0 if success else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--sha", required=True); parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch("[0-9a-f]{40}", args.sha): parser.error("full source SHA required")
    sys.exit(run(args.root, args.sha, args.report.resolve()))
