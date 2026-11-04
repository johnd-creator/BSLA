"""Bounded owning-Compose operations; default is read-only preflight.

This tool changes no DB, grant, controller or application source selection.
A private exact-plan owner GO, fresh recovery gates and separate official paired
controller acceptance are required. Never substitute Compose start/restart.
"""
import argparse
import copy
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess

SERVICES = frozenset({'maximo-api', 'maximo-worker', 'mart-projector', 'cockpit-api'})
WRITERS = frozenset({'maximo-worker', 'mart-projector'})
FORBIDDEN = frozenset({'maximo-init', 'maximo-db', 'mart-migrate', 'mart-reader',
                       'cockpit-init', 'pi-init', 'pi-migrate', 'cems-init', 'mart-ready'})
PROJECT = 'reliability-cockpit-platform'
GENERATED_LABELS = frozenset({'com.docker.compose.config-hash',
    'com.docker.compose.image', 'com.docker.compose.project.config_files'})
ACTIONS = ('preflight', 'quiesce', 'replace', 'resume', 'rollback')


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def private_bytes(path):
    path = Path(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != 0o600):
            raise RuntimeError('PRIVATE_OWNED_0600_FILE_REQUIRED')
        return stream.read()


def environment(values):
    result = {}
    for value in values:
        key, separator, item = value.partition('=')
        if not separator or not key or key in result:
            raise RuntimeError('UNAMBIGUOUS_ENVIRONMENT_REQUIRED')
        result[key] = item
    return result


def runtime_contract(container):
    """Normalize only documented empty Docker defaults and unordered Env.

    Nonempty DNS and true OomKillDisable are retained and compared. Missing keys
    stay distinct; no other host/security/resource option is discarded.
    """
    config = copy.deepcopy(container['Config'])
    config.pop('Hostname')  # Docker-generated container identity, checked by Id.
    config['Env'] = environment(config['Env'])
    replacement = config['Labels'].pop('com.docker.compose.replace', None)
    if replacement is not None and replacement != config['Labels'].get('com.docker.compose.service', '') + '-1':
        raise RuntimeError('UNEXPECTED_COMPOSE_REPLACEMENT_LABEL')
    for key in GENERATED_LABELS:
        config['Labels'].pop(key, None)
    host = copy.deepcopy(container['HostConfig'])
    for key in ('Dns', 'DnsOptions', 'DnsSearch'):
        if key in host and host[key] is None:
            host[key] = []
    if 'OomKillDisable' in host and host['OomKillDisable'] is None:
        host['OomKillDisable'] = False
    return {'config': config, 'host': host, 'mounts': container['Mounts'],
            'networks': sorted(container['NetworkSettings']['Networks']),
            'image': container['Image']}


def expected_runtime(before, image, revision, contract_root=None):
    value = copy.deepcopy(before)
    value['Image'] = image
    value['Config']['Image'] = image
    value['Config']['Labels']['org.opencontainers.image.revision'] = revision
    if contract_root is not None:
        env = environment(value['Config']['Env'])
        if env.get('RELIABILITY_CONTRACTS_ROOT') != '/contracts':
            raise RuntimeError('ORIGINAL_PROJECTOR_CONTRACT_ROOT_REQUIRED')
        env['RELIABILITY_CONTRACTS_ROOT'] = contract_root
        value['Config']['Env'] = [key + '=' + item for key, item in env.items()]
    return value


def verify_runtime(actual, expected):
    if digest(runtime_contract(actual)) != digest(runtime_contract(expected)):
        raise RuntimeError('RUNTIME_CONTRACT_CHANGED')


def operation_args(action, service):
    if service not in SERVICES or service in FORBIDDEN:
        raise RuntimeError('EXACT_SERVICE_ALLOWLIST_REQUIRED')
    if action == 'quiesce':
        if service not in WRITERS:
            raise RuntimeError('ONLY_TWO_WRITERS_MAY_QUIESCE')
        return ['stop', '--timeout', '60', service]
    base = ['up', '-d', '--no-deps', '--no-build', '--pull', 'never']
    if action == 'resume':
        if service not in WRITERS:
            raise RuntimeError('ONLY_TWO_WRITERS_MAY_RESUME')
        return base + ['--no-recreate', service]
    if action in ('replace', 'rollback'):
        if service in WRITERS:
            return base + ['--force-recreate', '--no-start', service]
        return base + ['--force-recreate', service]
    raise RuntimeError('EXACT_OPERATION_REQUIRED')


def preserved(container):
    state = {key: container['State'][key] for key in
             ('Status', 'Running', 'Paused', 'Dead', 'ExitCode', 'StartedAt', 'FinishedAt')}
    return {**{key: container[key] for key in
               ('Id', 'Name', 'Image', 'RestartCount', 'Config', 'HostConfig', 'Mounts')},
            'state': state, 'network': container['NetworkSettings']}


def verify_preservation(before, after, allowed_names):
    if set(before) != set(after):
        raise RuntimeError('CONTAINER_SET_CHANGED')
    for name in before:
        if name not in allowed_names and digest(preserved(before[name])) != digest(preserved(after[name])):
            raise RuntimeError('UNEXPECTED_SERVICE_ACTIVATION_OR_CHANGE')


def run(args):
    # Never print rendered environments, inspect contents or process stderr.
    result = subprocess.run(args, capture_output=True, timeout=180)
    if result.returncode:
        raise RuntimeError('DOCKER_OPERATION_FAILED_PRIVATE_DIAGNOSTICS_REQUIRED')
    return result.stdout


def inventory():
    ids = run(['docker', 'ps', '-aq']).decode().split()
    if not ids:
        raise RuntimeError('EXISTING_CONTAINER_INVENTORY_REQUIRED')
    rows = json.loads(run(['docker', 'inspect', *ids]))
    return {row['Name']: row for row in rows}


def write_exclusive(path, value):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(encoded(value) + b'\n'); stream.flush(); os.fsync(stream.fileno())
    directory = os.open(Path(path).parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def compose_prefix(plan, service, candidate):
    spec = plan['services'][service]
    prefix = ['docker', 'compose', '--env-file', plan['env_file'], '-p', PROJECT]
    seals = spec['files'] + ([spec['override']] if candidate else [])
    for item in seals:
        path = Path(item['path'])
        if not path.is_absolute() or path.resolve() != path or not path.is_file():
            raise RuntimeError('EXACT_LOCAL_COMPOSE_FILE_REQUIRED')
        if hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            raise RuntimeError('COMPOSE_FILE_SEAL_CHANGED')
        prefix += ['-f', str(path)]
    if hashlib.sha256(private_bytes(plan['env_file'])).hexdigest() != plan['env_sha256']:
        raise RuntimeError('ENV_FILE_SEAL_CHANGED')
    rendered = json.loads(run(prefix + ['config', '--format', 'json']))
    if rendered['name'] != PROJECT:
        raise RuntimeError('COMPOSE_PROJECT_CHANGED')
    value = rendered['services'][service]
    if digest(value) != spec['rendered_candidate' if candidate else 'rendered_baseline']:
        raise RuntimeError('RENDERED_SERVICE_CONTRACT_CHANGED')
    # Dependencies are preserved, not erased to make a command appear safe.
    if value.get('depends_on', {}) != spec['dependencies']:
        raise RuntimeError('DEPENDENCY_GRAPH_CHANGED')
    if value.get('pre_start') or value.get('post_start') or value.get('pre_stop'):
        raise RuntimeError('UNREVIEWED_LIFECYCLE_HOOK')
    return prefix


def validate_plan(plan):
    if (plan['version'] != 1 or plan['purpose'] != 'NADI_WO_ACTIVATION_CORRECTION_01'
            or plan['project'] != PROJECT or set(plan['services']) != SERVICES
            or plan['container_count'] != 35 or set(plan['forbidden']) != FORBIDDEN
            or len(plan['role_identities']) != 35):
        raise RuntimeError('EXACT_CLOSED_SERVICE_PLAN_REQUIRED')
    root = Path(plan['repository'])
    if root.resolve() != root or plan['env_file'] != str(root / '.env.platform'):
        raise RuntimeError('EXISTING_OWNER_REPOSITORY_REQUIRED')
    if run(['docker', 'context', 'show']).decode().strip() != plan['docker_context']:
        raise RuntimeError('DOCKER_OWNER_CONTEXT_CHANGED')
    if run(['docker', 'compose', 'version', '--short']).decode().strip() != plan['compose_version']:
        raise RuntimeError('COMPOSE_VERSION_CHANGED')
    if run(['docker', 'info', '--format', '{{.ID}}']).decode().strip() != plan['engine_id']:
        raise RuntimeError('DOCKER_ENGINE_IDENTITY_CHANGED')
    for service, spec in plan['services'].items():
        for key in ('image_before', 'image_after'):
            image = json.loads(run(['docker', 'image', 'inspect', spec[key]]))[0]
            if key == 'image_after' and image['Config'].get('Labels', {}).get('org.opencontainers.image.revision') != plan['candidate_sha']:
                raise RuntimeError('CANDIDATE_IMAGE_SOURCE_REVISION_MISMATCH')
            if image['Id'] != spec[key]:
                raise RuntimeError('PINNED_IMAGE_UNAVAILABLE')
        old_prefix = compose_prefix(plan, service, False)
        new_prefix = compose_prefix(plan, service, True)
        old = json.loads(run(old_prefix + ['config', '--format', 'json']))['services'][service]
        new = json.loads(run(new_prefix + ['config', '--format', 'json']))['services'][service]
        expected = copy.deepcopy(old); expected['image'] = spec['image_after']
        expected.setdefault('labels', {})['org.opencontainers.image.revision'] = plan['candidate_sha']
        if service == 'mart-projector':
            if expected['environment'].get('RELIABILITY_CONTRACTS_ROOT') != '/contracts':
                raise RuntimeError('ORIGINAL_CONTRACT_ROOT_CHANGED')
            expected['environment']['RELIABILITY_CONTRACTS_ROOT'] = '/reliability-data-contracts'
        if digest(new) != digest(expected):
            raise RuntimeError('UNAPPROVED_RENDERED_CONFIGURATION_CHANGE')
    return plan


def execute(plan_path, action, service, owner_path, receipt_dir):
    raw = private_bytes(plan_path); plan = validate_plan(json.loads(raw))
    root = Path(receipt_dir)
    if (root.resolve() != root or stat.S_IMODE(root.stat().st_mode) != 0o700
            or root.stat().st_uid != os.getuid()):
        raise RuntimeError('PRIVATE_EXISTING_RECEIPT_DIRECTORY_REQUIRED')
    fd = os.open(root / 'activation.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        before = inventory()
        if len(before) != 35:
            raise RuntimeError('EXACT_35_EXISTING_ROLES_REQUIRED')
        for name, image_id in plan['role_identities'].items():
            if name not in before or (name not in {'/'+PROJECT+'-'+s+'-1' for s in SERVICES}
                    and (before[name]['Id'], before[name]['Image']) != tuple(image_id)):
                raise RuntimeError('BASELINE_ROLE_IDENTITY_CHANGED')
        for role, spec in plan['services'].items():
            current = before['/'+PROJECT+'-'+role+'-1']
            if current['Image'] == spec['image_before']:
                verify_runtime(current, spec['baseline_runtime'])
            elif current['Image'] == spec['image_after']:
                verify_runtime(current, expected_runtime(spec['baseline_runtime'], spec['image_after'], plan['candidate_sha'],
                    '/reliability-data-contracts' if role=='mart-projector' else None))
            else:
                raise RuntimeError('UNEXPECTED_CURRENT_SERVICE_IMAGE')
        if action == 'preflight':
            return {'status': 'PREFLIGHT_PASS', 'containers': 35, 'writes': 0}
        owner = json.loads(private_bytes(owner_path))
        if owner != {'purpose': plan['purpose'], 'verdict': 'GO',
                     'plan_sha256': hashlib.sha256(raw).hexdigest(), 'operator': plan['operator']}:
            raise RuntimeError('EXACT_OWNER_OPERATIONAL_GO_REQUIRED')
        now = datetime.now(timezone.utc)
        start, end = (datetime.fromisoformat(plan['window'][k]) for k in ('start', 'end'))
        if start.tzinfo is None or end.tzinfo is None or not start <= now < end:
            raise RuntimeError('APPROVED_OPERATING_WINDOW_REQUIRED')
        args = operation_args(action, service)
        name = '/' + PROJECT + '-' + service + '-1'; spec = plan['services'][service]
        actual = before[name]
        seed = spec['baseline_runtime']
        candidate = expected_runtime(seed, spec['image_after'], plan['candidate_sha'],
                                     '/reliability-data-contracts' if service == 'mart-projector' else None)
        if actual['Image'] == spec['image_before']:
            verify_runtime(actual, seed)
        elif actual['Image'] == spec['image_after']:
            verify_runtime(actual, candidate)
        else:
            raise RuntimeError('UNEXPECTED_CURRENT_IMAGE')
        if action in ('replace', 'rollback') and service in WRITERS and actual['State']['Running']:
            raise RuntimeError('QUIESCED_WRITER_REQUIRED')
        target_candidate = action != 'rollback' and (action != 'quiesce' or actual['Image'] == spec['image_after'])
        if action == 'resume':
            if actual['State']['Running']:
                raise RuntimeError('WRITER_ALREADY_RUNNING')
            target_candidate = actual['Image'] == spec['image_after']
        prefix = compose_prefix(plan, service, target_candidate)
        receipt = root / (action + '-' + service + '-' + now.strftime('%Y%m%dT%H%M%S%f') + '.json')
        write_exclusive(receipt, {'state': 'PREPARED', 'plan_sha256': hashlib.sha256(raw).hexdigest(),
                         'command': prefix + args, 'before': before})
        command_start = datetime.now(timezone.utc).isoformat()
        try:
            run(prefix + args)
        finally:
            after = inventory()
            until = datetime.now(timezone.utc).isoformat()
            events = [json.loads(line) for line in run(['docker', 'events', '--since', command_start,
                      '--until', until, '--filter', 'type=container', '--format', '{{json .}}']).splitlines()]
            write_exclusive(receipt.with_suffix('.observed.json'), {'after': after, 'events': events})
        verify_preservation(before, after, {name})
        for event in events:
            if event.get('Action') in {'create','start','restart','die','destroy','stop','kill','pause','unpause','update','rename'}:
                if event.get('Actor', {}).get('Attributes', {}).get('name') != name.lstrip('/'):
                    raise RuntimeError('UNEXPECTED_SERVICE_LIFECYCLE_EVENT')
        if after[name]['RestartCount'] != 0 and after[name]['Id'] != actual['Id']:
            raise RuntimeError('NEW_SERVICE_RESTARTED_UNEXPECTEDLY')
        verify_runtime(after[name], candidate if target_candidate else seed)
        expected_running = action == 'resume' or action in ('replace', 'rollback') and service not in WRITERS
        if after[name]['State']['Running'] != expected_running:
            raise RuntimeError('SERVICE_STATE_MISMATCH')
        if action in ('quiesce', 'resume') and after[name]['Id'] != actual['Id']:
            raise RuntimeError('UNEXPECTED_SERVICE_RECREATION')
        write_exclusive(receipt.with_suffix('.completed.json'), {'state': 'VERIFIED',
                        'after': after, 'command': prefix + args})
        return {'status': 'VERIFIED', 'action': action, 'service': service,
                'unrelated_services_preserved': 34, 'receipt': str(receipt)}
    finally:
        os.close(fd)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True); parser.add_argument('--receipts', required=True)
    parser.add_argument('--action', choices=ACTIONS, default='preflight')
    parser.add_argument('--service', choices=sorted(SERVICES)); parser.add_argument('--owner')
    options = parser.parse_args()
    if options.action != 'preflight' and not (options.service and options.owner):
        parser.error('exact --service and private --owner GO required')
    print(json.dumps(execute(options.plan, options.action, options.service, options.owner, options.receipts)))
