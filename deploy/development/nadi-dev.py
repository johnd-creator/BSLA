#!/usr/bin/env python3
"""Explicit laptop-only supervisor. Never sources dotenv or operational configuration."""
import argparse
import json
import os
import secrets
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen
import socket
import ssl
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT.parent
STATE = BASE / 'state'
NAME = 'nadi-dev-live-postgres'
UNITS = ('nadi-live-api.service', 'nadi-primary-web.service')
LEGACY_WEB = 'nadi-live-web.service'
ORIGIN = 'https://localhost:3000'
WEB_CONTAINER = 'reliability-cockpit-platform-cockpit-web-1'

def run(args, **kwargs):
    return subprocess.run([str(a) for a in args], check=True, **kwargs)

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()

def load():
    p=STATE/'config.json'; info=p.lstat()
    if p.is_symlink() or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise RuntimeError('PRIVATE_CONFIG_REQUIRED')
    return json.loads(p.read_text())

def db():
    result=subprocess.run(['docker','inspect',NAME],capture_output=True,text=True)
    if result.returncode:return None
    value=json.loads(result.stdout)[0]
    if value['Config']['Labels'].get('nadi.scope')!='disposable-laptop-development':
        raise RuntimeError('UNEXPECTED_DATABASE_CONTAINER')
    return value

def write_private(path, data):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'w') as f:f.write(data)

def setup():
    STATE.mkdir(mode=0o700,parents=True,exist_ok=True)
    if (STATE/'config.json').exists():
        load();print('Existing private configuration retained');return
    if db():raise RuntimeError('UNTRACKED_DEVELOPMENT_DATABASE')
    password=secrets.token_urlsafe(32)
    accounts={name:{'username':'fixture-'+name,'password':secrets.token_urlsafe(24)} for name in ('admin','engineer','reviewer')}
    write_private(STATE/'accounts.json',json.dumps(accounts,indent=2))
    write_private(STATE/'postgres.env','POSTGRES_DB=nadi_live_dev_test\nPOSTGRES_USER=nadi_dev_fixture\nPOSTGRES_PASSWORD='+password+'\n')
    config={'application_dsn':'postgresql+psycopg://nadi_dev_fixture:'+password+'@127.0.0.1:15443/nadi_live_dev_test',
            'accounts_file':str(STATE/'accounts.json')}
    write_private(STATE/'config.json',json.dumps(config,indent=2))
    (STATE/'attachments').mkdir(mode=0o700,exist_ok=True)
    (STATE/'postgres-data').mkdir(mode=0o700,exist_ok=True)
    run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',STATE/'localhost.key','-out',STATE/'localhost.pem',
         '-days','365','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost,IP:127.0.0.1'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    os.chmod(STATE/'localhost.key',0o600)
    os.chmod(STATE/'localhost.pem',0o600)
    print('Private disposable configuration generated; no credentials printed')

def common_env():
    return ['PATH=/home/linuxbrew/.linuxbrew/bin:/usr/local/bin:/usr/bin:/bin',
            'HOME='+str(Path.home()),'LANG=C.UTF-8','COCKPIT_CONFIG_MODE=managed',
            'PYTHONPATH='+str(ROOT/'reliability-cockpit')+':'+str(ROOT/'reliability-cockpit/tests'),
            'PYTHONUNBUFFERED=1','NADI_DISPOSABLE_QA_ACK=persistent-laptop-fixture',
            'NADI_DEV_CONFIG='+str(STATE/'config.json'),'NADI_DEV_LAUNCHED_SHA='+git('rev-parse','HEAD')]

def start_unit(name, cwd, command, extra=()):
    run(['systemd-run','--user','--collect','--unit='+name,'--service-type=exec',
         '--working-directory='+str(cwd),'--property=Restart=on-failure',
         '--property=RestartSec=3','--property=MemoryMax=2500M','--property=CPUQuota=200%',
         '--property=TasksMax=128','--property=UMask=0077','--property=TimeoutStopSec=20',
         '/usr/bin/env','-i',*common_env(),*extra,*command])

def active(unit):
    return subprocess.run(['systemctl','--user','is-active','--quiet',unit]).returncode==0

def selected_ref(preview_ref=None):
    # No implicit branch switches, merges or resets, including for merged-main updates.
    ref = preview_ref or 'origin/main'
    sha = git('rev-parse', '--verify', ref + '^{commit}')
    if git('rev-parse', 'HEAD') != sha:
        raise RuntimeError('SELECT_REVIEWED_REF_FIRST: default origin/main; feature previews require --preview-ref')
    return sha

def preflight(preview_ref=None):
    load()
    selected_ref(preview_ref)
    required = ['reliability-cockpit/tests/qa/live_server.py', 'reliability-cockpit/web/components/DevelopmentStatus.tsx']
    if any(not (ROOT / p).is_file() for p in required):
        raise RuntimeError('SELECTED_REF_MISSING_DEVELOPMENT_FOUNDATION')
    if any((ROOT / 'reliability-cockpit/web' / p).exists() for p in ['.env', '.env.local', '.env.development', '.env.development.local']):
        raise RuntimeError('UNREVIEWED_DOTENV_CONFIGURATION_DENIED')
    value = db()
    if not value or not value['State']['Running']:
        raise RuntimeError('EXISTING_FIXTURE_DATABASE_MUST_BE_RUNNING: no automatic creation or replacement')
    if not (STATE / 'localhost.key').is_file() or not (STATE / 'localhost.pem').is_file():
        raise RuntimeError('EXISTING_HTTPS_CERTIFICATE_REQUIRED')
    return value

def primary_busy():
    # Check both localhost address families: Next binds to localhost, never source networks.
    for address in ('127.0.0.1', '::1'):
        try:
            with socket.create_connection((address, 3000), timeout=1):
                return True
        except OSError:
            pass
    return False

def web_start():
    start_unit('nadi-primary-web', ROOT / 'reliability-cockpit/web',
        ['/home/linuxbrew/.linuxbrew/bin/node', 'node_modules/next/dist/bin/next', 'dev',
         '--hostname', 'localhost', '--port', '3000', '--experimental-https',
         '--experimental-https-key', str(STATE / 'localhost.key'),
         '--experimental-https-cert', str(STATE / 'localhost.pem')],
        ['NODE_ENV=development', 'NEXT_TELEMETRY_DISABLED=1', 'NODE_OPTIONS=--max-old-space-size=2048',
         'NADI_LIVE_DEV=true', 'NADI_PRIMARY_FRONTEND=true', 'NADI_ENGINEERING_WORKSPACE_ENABLED=true',
         'NADI_ENGINEERING_DEMO_ENABLED=true', 'NADI_ENGINEERING_QA_ENABLED=true',
         'NADI_QA_BACKEND_URL=http://127.0.0.1:13036', 'COCKPIT_API_BASE=http://127.0.0.1:8000'])

def api_start():
    start_unit('nadi-live-api', ROOT / 'reliability-cockpit',
        [str(STATE / 'python-runtime/bin/python'), '-m', 'uvicorn', 'live_server:create_live_app',
         '--app-dir', 'tests/qa', '--factory', '--host', '127.0.0.1', '--port', '13036',
         '--reload', '--reload-dir', 'src', '--reload-dir', 'tests/qa', '--no-access-log'])

def start(preview_ref=None):
    preflight(preview_ref)
    if active(UNITS[1]) or primary_busy():
        raise RuntimeError('PRIMARY_FRONTEND_ALREADY_OWNED: use status or explicit cutover')
    if active(LEGACY_WEB):
        raise RuntimeError('LEGACY_PREVIEW_RUNNING: use controlled cutover')
    if not active(UNITS[0]):
        api_start()
    web_start()
    print('Primary development frontend: ' + ORIGIN)

def container():
    result = subprocess.run(['docker', 'inspect', WEB_CONTAINER], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError('ROLLBACK_FRONTEND_CONTAINER_MISSING')
    value = json.loads(result.stdout)[0]
    labels = value['Config'].get('Labels') or {}
    if labels.get('com.docker.compose.project') != 'reliability-cockpit-platform' or labels.get('com.docker.compose.service') != 'cockpit-web':
        raise RuntimeError('UNEXPECTED_FRONTEND_CONTAINER')
    return value

def ready():
    context = ssl.create_default_context(cafile=str(STATE / 'localhost.pem'))
    with urlopen(ORIGIN + '/api/development/status', context=context, timeout=10) as reply:
        data = json.load(reply)
    if (data.get('sha') != git('rev-parse', 'HEAD') or data.get('stale') is not False
            or data.get('backend') != 'AVAILABLE' or data.get('factual_backend') != 'AVAILABLE'
            or data.get('database_identity') != 'nadi_live_dev_test' or not data.get('engineering')):
        raise RuntimeError('PRIMARY_FRONTEND_NOT_READY')
    return data

def cutover(preview_ref=None):
    preflight(preview_ref)
    if git('status', '--porcelain'):
        raise RuntimeError('DIRTY_CUTOVER_DENIED: commit or preserve changes first')
    if active(UNITS[1]):
        raise RuntimeError('PRIMARY_PREVIEW_ALREADY_RUNNING')
    value = container()
    if not value['State']['Running'] and primary_busy():
        raise RuntimeError('PRIMARY_PORT_UNEXPECTED_OWNER')
    snapshot = STATE / 'frontend-rollback.json'
    if snapshot.exists():
        old = json.loads(snapshot.read_text())
        if old['id'] != value['Id']:
            raise RuntimeError('ROLLBACK_CONTAINER_ID_CHANGED')
    else:
        write_private(snapshot, json.dumps({'id': value['Id'], 'image': value['Config']['Image'],
            'revision': value['Config']['Labels'].get('org.opencontainers.image.revision'),
            'was_running': value['State']['Running']}, indent=2))
    # Do not recreate this container or touch Compose dependencies.
    if value['State']['Running']:
        run(['docker', 'stop', WEB_CONTAINER], stdout=subprocess.DEVNULL)
    try:
        if primary_busy():
            raise RuntimeError('PRIMARY_PORT_STILL_OWNED')
        if not active(UNITS[0]):
            api_start()
        web_start()
        for _ in range(30):
            try:
                ready()
                print('Primary ready: ' + ORIGIN + '; run browser checks before retire-legacy')
                return
            except Exception:
                time.sleep(1)
        raise RuntimeError('PRIMARY_READINESS_FAILED')
    except Exception:
        rollback()
        raise

def stop_unit(unit):
    result = subprocess.run(['systemctl', '--user', 'stop', unit], capture_output=True)
    # A collected transient unit may already be gone. All other failures are blockers.
    if result.returncode not in (0, 5):
        raise RuntimeError('DEVELOPMENT_UNIT_STOP_FAILED')

def rollback():
    # Verify recovery owner BEFORE stopping the current frontend.
    saved = json.loads((STATE / 'frontend-rollback.json').read_text())
    value = container()
    if value['Id'] != saved['id'] or value['Config']['Image'] != saved['image']:
        raise RuntimeError('ROLLBACK_CONTAINER_ID_CHANGED')
    stop_unit(UNITS[1])
    run(['docker', 'start', WEB_CONTAINER], stdout=subprocess.DEVNULL)
    print('Restored preserved frontend container on http://localhost:3000; fixture API/database retained')

def retire_legacy():
    ready()
    stop_unit(LEGACY_WEB)
    print('Retired 13035 frontend only; worktree, API, sessions and PostgreSQL retained')

def stop():
    for unit in UNITS:
        stop_unit(unit)
    print('Development processes stopped; database remains running and records retained')

def reload(preview_ref=None):
    # Validate BEFORE stopping any working process. UI HMR does not need this command.
    preflight(preview_ref)
    if active(LEGACY_WEB):
        raise RuntimeError('RETIRE_LEGACY_BEFORE_RELOAD')
    stop()
    start(preview_ref)

def status():
    if (STATE / "frontend-active.json").exists():
        print(json.dumps(frontend_controller().status(), indent=2))
        return
    value = db() or {}
    print(json.dumps({'branch': git('branch', '--show-current') or 'DETACHED',
        'source_sha': git('rev-parse', 'HEAD'), 'main_sha': git('rev-parse', 'origin/main'),
        'dirty': bool(git('status', '--porcelain')), 'origin': ORIGIN,
        'services': {u: active(u) for u in (*UNITS, LEGACY_WEB)},
        'database': 'nadi_live_dev_test' if value.get('State', {}).get('Running') else 'STOPPED_OR_ABSENT'}, indent=2))

def switch(ref='origin/main'):
    if any(active(u) for u in (*UNITS, LEGACY_WEB)):
        raise RuntimeError('STOP_PREVIEW_BEFORE_SWITCH')
    if git('status', '--porcelain'):
        raise RuntimeError('DIRTY_WORKTREE_SWITCH_DENIED')
    git('rev-parse', '--verify', ref + '^{commit}')
    # Check target before changing checkout. Unmerged foundation is not silently overlaid on main.
    git('cat-file', '-e', ref + ':deploy/development/nadi-dev.py')
    run(['git', 'switch', '--detach', ref], cwd=ROOT)
    print('Selected reviewed ref; verify dependencies/migration compatibility before start')

def backup():
    value = db()
    if not value or not value['State']['Running']:
        raise RuntimeError('START_DEVELOPMENT_DATABASE_FIRST')
    target = STATE / ('backup-' + time.strftime('%Y%m%d-%H%M%S') + '.dump')
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as f:
        run(['docker', 'exec', NAME, 'pg_dump', '-U', 'nadi_dev_fixture', '-d', 'nadi_live_dev_test', '-Fc'], stdout=f)
    print('Private development backup created:', target)

def frontend_controller():
    # The reviewed companion is installed beside the pinned controller, never in the API checkout.
    import importlib.util
    from types import SimpleNamespace
    spec = importlib.util.spec_from_file_location('frontend_preview', Path(__file__).with_name('frontend_preview.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.FrontendPreview(SimpleNamespace(**globals()))


def local_controller():
    import importlib.util
    from types import SimpleNamespace
    spec = importlib.util.spec_from_file_location('local_development', Path(__file__).with_name('local_development.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.LocalDevelopment(SimpleNamespace(**globals()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['setup', 'start', 'status', 'logs', 'stop', 'reload', 'switch', 'backup', 'cutover', 'rollback', 'retire-legacy', 'frontend-preflight', 'frontend-select', 'frontend-rollback', 'local-preflight', 'local-select', 'local-status', 'local-rollback', 'local-preserve', 'local-prepare-recovery'])
    parser.add_argument('ref', nargs='?')
    parser.add_argument('--preview-ref', help='Explicit feature ref; must resolve to this checkout HEAD')
    parser.add_argument('--backup', help='Existing private backup, validated read-only')
    parser.add_argument('--session-file', help='Optional owner-only current session proof for local status; no credentials on command line')
    parser.add_argument('--preservation', help='Owner-private source manifest, never runtime credentials')
    parser.add_argument('--preservation-sha256', help='Exact reviewed preservation manifest digest')
    parser.add_argument('--recovery-receipt', help='Owner-private independently prepared recovery receipt')
    parser.add_argument('--recovery-receipt-sha256', help='Exact reviewed recovery receipt digest')
    parser.add_argument('--acceptance-session-file', help='Private existing-session proof required for preserved paired acceptance')
    parser.add_argument('--require-factual-read', action='store_true', help='Explicit task-scoped active owner-approved Factual READ gate; does not issue a grant')
    args = parser.parse_args()
    if args.require_factual_read and args.command not in ('local-preflight','local-select'):
        raise RuntimeError('FACTUAL_READ_APPROVAL_SELECTION_ONLY')
    if (args.preservation or args.preservation_sha256) and args.command != 'local-prepare-recovery':
        raise RuntimeError('PRESERVATION_APPROVAL_PREPARATION_ONLY')
    if args.acceptance_session_file and args.command not in ('local-select','local-rollback'):
        raise RuntimeError('ACCEPTANCE_SESSION_LIFECYCLE_ONLY')
    if bool(args.recovery_receipt) != bool(args.recovery_receipt_sha256):
        raise RuntimeError('EXACT_RECOVERY_RECEIPT_APPROVAL_REQUIRED')
    if args.recovery_receipt and args.command not in ('local-preflight','local-select'):
        raise RuntimeError('RECOVERY_APPROVAL_SELECTION_ONLY')
    if args.session_file and args.command not in ('status','local-status'):
        raise RuntimeError('SESSION_PROOF_STATUS_ONLY')
    # Serialize official lifecycle mutations, including old all-service commands.
    lock_fd = None
    if STATE.exists() and args.command not in ('status', 'logs', 'frontend-preflight'):
        import fcntl
        lock_fd = os.open(STATE / 'frontend-lifecycle.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(lock_fd)
            raise RuntimeError('DEVELOPMENT_LIFECYCLE_BUSY')
    if (STATE / 'local-dev-01/active.json').exists() and not args.command.startswith('local-') and args.command not in ('status','logs','backup'):
        raise RuntimeError('LOCAL_PAIRED_SOURCE_ACTIVE: use local lifecycle; no independent source selection')
    if args.command == 'status' and (STATE / 'local-dev-01/active.json').exists():
        print(json.dumps(local_controller().status(session_file=args.session_file), indent=2)); return
    if args.command.startswith('local-'):
        manager = local_controller()
        manager.require_factual_read=args.require_factual_read
        manager.acceptance_session_file=args.acceptance_session_file
        if args.recovery_receipt:
            manager.preservation={'receipt':args.recovery_receipt,'receipt_sha256':args.recovery_receipt_sha256}
        if args.command == 'local-preserve':
            if not args.ref:raise RuntimeError('PRIVATE_ARCHIVE_DESTINATION_REQUIRED')
            print(json.dumps(manager.preserve(Path(args.ref)),indent=2))
        elif args.command == 'local-prepare-recovery':
            if not args.ref or not args.preservation or not args.preservation_sha256:
                raise RuntimeError('EXACT_PRESERVATION_APPROVAL_REQUIRED')
            print(json.dumps(manager.prepare_preserved({'manifest':args.preservation,'digest':args.preservation_sha256},Path(args.ref)),indent=2))
        elif args.command == 'local-status':
            print(json.dumps(manager.status(session_file=args.session_file), indent=2))
        elif args.command == 'local-rollback':
            manager.recover(manager.active_value())
        elif not args.ref or not args.preview_ref:
            raise RuntimeError('EXPLICIT_LOCAL_WORKTREE_AND_REVIEWED_REF_REQUIRED')
        elif args.command == 'local-preflight':
            print(json.dumps(manager.preflight(Path(args.ref), args.preview_ref), indent=2))
        else:
            manager.select(Path(args.ref), args.preview_ref)
        return
    if (STATE / 'frontend-active.json').exists() and args.command in ('start', 'stop', 'reload', 'switch', 'cutover', 'rollback', 'setup'):
        raise RuntimeError('FRONTEND_ONLY_SELECTION_ACTIVE: use frontend-select/rollback; shared-source lifecycle denied')
    if args.command.startswith('frontend-'):
        manager = frontend_controller()
        if args.command == 'frontend-rollback':
            manager.rollback(args.ref)
        elif not args.ref or not args.preview_ref or not args.backup:
            raise RuntimeError('FRONTEND_SOURCE_SHA_BACKUP_REQUIRED')
        elif args.command == 'frontend-select':
            manager.select(Path(args.ref), args.preview_ref, args.backup)
        else:
            approval, previous = manager.preflight(Path(args.ref), args.preview_ref, args.backup)
            print(json.dumps({'preflight': 'PASS', 'approval': approval, 'rollback_source': previous['sha']}, indent=2))
        return
    if args.command == 'switch':
        switch(args.ref or 'origin/main')
    elif args.command in ('start', 'cutover', 'reload'):
        globals()[args.command](args.preview_ref)
    elif args.command == 'retire-legacy':
        retire_legacy()
    elif args.command == 'logs':
        run(['journalctl', '--user', '-u', UNITS[0], '-u', UNITS[1], '-n', '80', '--no-pager'])
    else:
        globals()[args.command]()
if __name__ == '__main__':
    try:
        main()
    except RuntimeError as error:
        sys.exit(str(error))
    except Exception:
        sys.exit('DEVELOPMENT_COMMAND_FAILED: inspect private service logs; no automatic retry')
