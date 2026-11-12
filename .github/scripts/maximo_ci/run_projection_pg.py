"""Create OWN disposable Unix-only PG cluster, qualify B1, stop OWN cluster.

No input DSN, Docker, dotenv, operational host or production credentials accepted.
Private evidence directory is retained. This accidental-I/O guard is not a
hostile-code sandbox; use an ephemeral CI runner with no plant credentials.
"""
import argparse
import contextlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


def fixture_connection_allowed(parsed, socket_path, port):
    return (parsed.get('host') == socket_path and str(parsed.get('port')) == str(port)
            and parsed.get('dbname') == 'nadi_aud02b_disposable'
            and parsed.get('user') == 'nadi_b1_fixture'
            and not any(k in parsed for k in ('password','service','hostaddr')))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--sha', required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch('[0-9a-f]{40}', args.sha):
        parser.error('exact SHA required')
    root, report = args.root.resolve(), args.report.resolve()
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    # Never inherit a libpq/private DSN/credential or dotenv into subprocess/tests.
    for key in list(os.environ):
        if (key.startswith(('PG', 'MAXIMO_', 'NADI_', 'RELIABILITY_', 'COCKPIT_'))
                or key.endswith(('_DSN','_TOKEN','_PASSWORD','_SECRET'))
                or key in ('DATABASE_URL','DATABASE_ECHO','GH_TOKEN')):
            os.environ.pop(key)
    os.environ['PYTHON_DOTENV_DISABLED'] = '1'
    env = {k: os.environ[k] for k in ('PATH','LANG','LC_ALL','HOME') if k in os.environ}
    env['PYTHON_DOTENV_DISABLED'] = '1'
    bindir = Path(shutil.which('initdb') or '/usr/lib/postgresql/16/bin/initdb').parent
    work = Path(tempfile.mkdtemp(prefix='nadi-b1-pg-', dir='/tmp'))
    work.chmod(0o700)
    data, sock = work / 'data', work / 'socket'
    sock.mkdir(mode=0o700)
    owner = 'nadi_b1_fixture'
    dbname = 'nadi_aud02b_disposable'
    port = 16479  # Unix socket suffix only; TCP is disabled, no host listener.
    started = False
    result, blocked, failure = None, [], None
    fixture = {}
    workflow_sha = os.environ.get('CI_WORKFLOW_SHA','LOCAL_WORKTREE')
    run_url = os.environ.get('CI_RUN_URL','LOCAL_WORKTREE')
    def command(*words):
        with (work / 'cluster.log').open('a') as out:
            subprocess.run([str(bindir / words[0]), *words[1:]], env=env,
                           check=True, stdout=out, stderr=out, timeout=30)
    try:
        command('initdb','-D',str(data),'--no-locale','--encoding=UTF8','-A','trust','-U',owner)
        command('pg_ctl','-D',str(data),'-l',str(work/'postgres.log'),'-w','start','-o',
                f"-h '' -k {sock} -p {port} -c max_connections=12 -c shared_buffers=32MB -c fsync=on")
        started = True
        import psycopg
        params = dict(host=str(sock),port=port,user=owner,dbname='postgres',connect_timeout=3)
        with psycopg.connect(**params, autocommit=True) as c:
            directory = Path(c.execute('SHOW data_directory').fetchone()[0]).resolve()
            assert directory == data.resolve() and directory.parent == work
            assert c.execute('SHOW listen_addresses').fetchone()[0] == ''
            system_id = c.execute('SELECT system_identifier::text FROM pg_control_system()').fetchone()[0]
            server_version = c.execute('SHOW server_version').fetchone()[0]
            # Independent on-disk cluster identity, not just a DB-name convention.
            control = subprocess.check_output([str(bindir/'pg_controldata'),str(data)],env=env,text=True)
            assert system_id in control
            c.execute('CREATE DATABASE nadi_aud02b_disposable OWNER nadi_b1_fixture')
        params['dbname'] = dbname
        original_connect = psycopg.Connection.connect
        def deny(kind):
            blocked.append(kind)
            raise AssertionError('UNEXPECTED_EXTERNAL_IO:' + kind)
        def approved_connect(cls, conninfo='', **kwargs):
            parsed = psycopg.conninfo.conninfo_to_dict(conninfo, **kwargs)
            if not fixture_connection_allowed(parsed, str(sock), port):
                return deny('unapproved_postgresql')
            return original_connect(conninfo, **kwargs)
        def audit(event, values):
            if audit_enabled[0] and event in ('socket.connect','socket.getaddrinfo','socket.sendto','socket.sendmsg',
                         'subprocess.Popen','os.system'):
                deny(event)
        # libpq uses the independently verified private Unix socket only. Python
        # HTTP/socket and all subprocesses are blocked during discovery + tests.
        from sqlalchemy.engine import Engine
        from sqlalchemy.engine.url import URL
        original_engine_connect = Engine.connect
        def engine_connect(engine, *a, **kw):
            if (engine.url.drivername != 'postgresql+psycopg' or
                    dict(engine.url.query) != {'host':str(sock),'port':str(port)} or
                    engine.url.database != dbname or engine.url.username != owner or
                    engine.url.host is not None or engine.url.password is not None):
                return deny('unapproved_engine')
            return original_engine_connect(engine,*a,**kw)
        fixture = dict(directory=str(work), system_id=system_id, socket_only=True,
                       database=dbname, owner=owner, server_version=server_version)
        os.chdir(root)
        sys.path[:0] = [str(root),str(root/'tests_postgres')]
        import fixture_context
        fixture_context.url = URL.create('postgresql+psycopg',username=owner,database=dbname,
                                        query={'host':str(sock),'port':str(port)})
        fixture_context.identity = fixture
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(psycopg.Connection,'connect',classmethod(approved_connect)))
            stack.enter_context(patch.object(psycopg,'connect',lambda conninfo='',**kw:approved_connect(None,conninfo,**kw)))
            stack.enter_context(patch.object(psycopg.AsyncConnection,'connect',lambda *a,**kw:deny('async_pg')))
            stack.enter_context(patch.object(Engine,'connect',engine_connect))
            stack.enter_context(patch('dotenv.load_dotenv',return_value=False))
            stack.enter_context(patch('dotenv.main.load_dotenv',return_value=False))
            sys.addaudithook(audit)
            suite = unittest.defaultTestLoader.discover(str(root/'tests_postgres'))
            discovered = suite.countTestCases()
            result = unittest.TextTestRunner(verbosity=2).run(suite)
    except Exception as error:
        failure = type(error).__name__
        print('PG_FIXTURE_FAILURE:'+failure,file=sys.stderr)
    finally:
        # Audit hook blocks subprocess by design. Remove only via process-local
        # flag after tests, not by weakening test guards or reusing a service.
        # See audit_enabled below for cleanup of this exact owned data directory.
        audit_enabled[0] = False
        if started:
            command('pg_ctl','-D',str(data),'-m','fast','-w','stop')
    ok = bool(result and result.wasSuccessful() and result.testsRun > 0 and
              result.testsRun == discovered and not result.skipped and
              not result.expectedFailures and not blocked and failure is None)
    output = dict(python=platform.python_version(),tested_sha=args.sha,
        workflow_sha=workflow_sha,run_url=run_url,
        tests=result.testsRun if result else 0, discovered=discovered if result else 0,
        failures=len(result.failures) if result else 0, errors=len(result.errors) if result else 0,
        skips=len(result.skipped) if result else 0, blocked_io=len(blocked),
        infrastructure_error=failure, fixture=fixture, cleanup='OWN_CLUSTER_STOPPED',
        conclusion='PASS' if ok else 'FAIL')
    report.write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(output))
    if summary:
        with open(summary,'a') as out:
            out.write('## Disposable PostgreSQL B1 qualification\n\n```json\n'+json.dumps(output,indent=2)+'\n```\n')
    return 0 if ok else 1


audit_enabled = [True]
if __name__ == '__main__':
    sys.exit(main())
