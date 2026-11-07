#!/usr/bin/env python3
"""Capture, rebuild and verify the exact local release without source credentials.

Never starts a production worker. A private Compose override pins local images;
the rebuild rehearsal uses a separate image tag, no network, no live DB/mounts.
All Docker config/env comparisons occur in memory. Only hashes are persisted.
"""
import argparse
import hashlib
import io
import json
import os
import re
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[2]
LOCK = Path(os.environ.get('BSLA_RUNTIME_LOCK', str(ROOT / '.nadi-dev/runtime-images.lock.json'))).expanduser().resolve()
RELEASE = Path(os.environ.get('BSLA_RUNTIME_RELEASE_DIR', str(ROOT / '.nadi-dev/runtime-release'))).expanduser().resolve()
REPRESENTATIVES = ('maximo-api', 'mart-projector', 'cockpit-api', 'cockpit-worker')

def run(*args, input=None):
    return subprocess.check_output(args, input=input, stderr=subprocess.PIPE)

def dock(*args):
    return json.loads(run('docker', *args))

def digest(data):
    return hashlib.sha256(data).hexdigest()

def json_digest(value):
    return digest(json.dumps(value, sort_keys=True, separators=(',', ':')).encode())

def lock():
    if not LOCK.is_file():
        raise RuntimeError('Private runtime lock unavailable. Provision the reviewed local release; a fresh clone cannot operate captured images.')
    try:
        value = json.loads(LOCK.read_text())
    except (OSError, ValueError) as error:
        raise RuntimeError('Private runtime lock is unreadable or invalid') from error
    required = {*REPRESENTATIVES, 'maximo-worker'}
    if (not isinstance(value, dict) or not isinstance(value.get('project'), str)
            or not re.fullmatch(r'[a-z0-9][a-z0-9_-]*', value['project'])
            or not isinstance(value.get('release'), str) or not value['release'].strip()
            or not isinstance(value.get('images'), dict) or set(value['images']) != required):
        raise RuntimeError('Private runtime lock has an invalid schema or service set')
    if any(not isinstance(image, str) or not re.fullmatch(r'sha256:[a-f0-9]{64}', image)
           or image == 'sha256:' + '0' * 64 for image in value['images'].values()):
        raise RuntimeError('Private runtime lock requires real immutable local image IDs')
    return value

def snapshot():
    value = lock()
    result = {}
    for service, image in value['images'].items():
        current = dock('inspect', value['project'] + '-' + service + '-1')[0]
        if current['Image'] != image or not current['State']['Running']:
            raise RuntimeError('Runtime changed: ' + service)
        result[service] = current
    return result

def files_from_tar(data):
    result = {}
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        for member in archive:
            name = Path(member.name)
            if member.isdir() or '__pycache__' in name.parts:
                continue
            if not member.isfile() or name.is_absolute() or '..' in name.parts:
                raise RuntimeError('Unsafe source archive member')
            content = archive.extractfile(member).read()
            result[str(name)] = content
    return result

def source_files(container, path):
    return files_from_tar(run('docker', 'cp', container + ':' + path, '-'))

def manifest_files(files):
    return {name: digest(data) for name, data in sorted(files.items())}

def capture():
    if (RELEASE / 'capture.json').exists():
        raise RuntimeError('Capture already exists; never overwrite release evidence')
    RELEASE.mkdir(parents=True, exist_ok=True)
    before = snapshot()
    result = {'release': lock()['release'], 'services': {}, 'sources': {}}
    (RELEASE / 'compose.yaml.before').write_bytes((ROOT / 'compose.yaml').read_bytes())
    (RELEASE / 'compose.dev.yaml.before').write_bytes((ROOT / 'compose.dev.yaml').read_bytes())
    for service, current in before.items():
        result['services'][service] = {'container_id': current['Id'], 'image': current['Image'],
            'started_at': current['State']['StartedAt'], 'config_sha256': json_digest(current['Config']),
            'host_config_sha256': json_digest(current['HostConfig'])}
    for service in REPRESENTATIVES:
        c = before[service]
        image_config = dock('image', 'inspect', c['Image'])[0]['Config']
        allowed = {'PATH', 'LANG', 'GPG_KEY', 'PYTHON_VERSION', 'PYTHON_SHA256', 'PYTHONDONTWRITEBYTECODE', 'PYTHONUNBUFFERED', 'RELIABILITY_MART_MIGRATIONS_ROOT'}
        if any(e.split('=',1)[0] not in allowed for e in image_config.get('Env', [])):
            raise RuntimeError('Review unexpected image environment before saving: ' + service)
        context = RELEASE / service
        context.mkdir(exist_ok=True)
        manifests = {}
        for target, path in [('app', '/app/src'), ('installed', '/usr/local/lib/python3.12/site-packages/src')]:
            files = source_files(c['Id'], path)
            for name, data in files.items():
                p = context / target / name
                p.parent.mkdir(parents=True, exist_ok=True)
                if p.exists() and p.read_bytes() != data:
                    raise RuntimeError('Partial snapshot differs; preserve and review it')
                p.write_bytes(data)
            manifests[target] = manifest_files(files)
        if manifests['app'] != manifests['installed']:
            raise RuntimeError('App/installed source divergence: ' + service)
        source_hash = json_digest(manifests['app'])
        base_tag = 'bsla-durable-base-' + service + ':' + c['Image'].split(':')[1][:12]
        run('docker', 'tag', c['Image'], base_tag)
        (context / 'Dockerfile').write_text(
            f'FROM {base_tag}\n'
            'COPY --chown=app:app app/src/ /app/src/\n'
            'COPY --chown=app:app installed/src/ /usr/local/lib/python3.12/site-packages/src/\n'
            f'LABEL bsla.durable.source.sha256="{source_hash}"\n')
        result['sources'][service] = {'image': c['Image'], 'base_tag': base_tag,
            'source_sha256': source_hash, 'files': manifests['app']}
    after = snapshot()
    if any(after[s]['Id'] != before[s]['Id'] for s in before):
        raise RuntimeError('Concurrent deployment during capture')
    archive = RELEASE / 'runtime-images.tar'
    run('docker', 'image', 'save', '--output', str(archive), *[result['sources'][s]['base_tag'] for s in REPRESENTATIVES])
    with archive.open('rb') as f:
        result['image_archive_sha256'] = hashlib.file_digest(f, 'sha256').hexdigest()
    result['image_archive_bytes'] = archive.stat().st_size
    (RELEASE / 'capture.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'captured_services': len(before), 'source_images': len(REPRESENTATIVES),
                      'image_archive_bytes': archive.stat().st_size}))

def validate_model(model):
    desired = lock()
    if model.get('name') != desired['project']:
        raise RuntimeError('Compose project mismatch')
    for service, image in desired['images'].items():
        spec = model['services'][service]
        if spec.get('image') != image or 'build' in spec or spec.get('pull_policy') != 'never':
            raise RuntimeError('Image pin/build/pull mismatch: ' + service)

def compose_model():
    # JSON list avoids shell expansion and supports private paths containing spaces.
    try:
        files = json.loads(os.environ.get('BSLA_RUNTIME_COMPOSE_FILES', '["compose.yaml", "compose.dev.yaml"]'))
    except ValueError as error:
        raise RuntimeError('BSLA_RUNTIME_COMPOSE_FILES must be a JSON list of reviewed Compose files') from error
    if not isinstance(files, list) or not files or any(not isinstance(f, str) or not f for f in files):
        raise RuntimeError('Expected a nonempty list of reviewed Compose files')
    args = ['docker', 'compose', '--env-file', str(ROOT/'.env.platform')]
    for filename in files:
        path = Path(filename).expanduser()
        if not path.is_absolute():
            path = ROOT / path
        if not path.is_file():
            raise RuntimeError('A required private Compose file is unavailable')
        args.extend(['-f', str(path)])
    return json.loads(run(*args, 'config', '--format', 'json'))

def verify():
    current = snapshot()
    model = compose_model()
    validate_model(model)
    differences = {}
    for service, item in current.items():
        spec = model['services'][service]
        actual = dict(e.split('=',1) for e in item['Config']['Env'])
        image_env = dict(e.split('=',1) for e in dock('image', 'inspect', item['Image'])[0]['Config']['Env'])
        desired = dict(image_env, **spec.get('environment', {}))
        env_difference = sorted(k for k in actual.keys() | desired.keys() if actual.get(k) != desired.get(k))
        if env_difference:
            differences[service] = {'environment_keys': env_difference}
        command = spec.get('command') or dock('image', 'inspect', item['Image'])[0]['Config']['Cmd']
        command = [part.replace('$$', '$') for part in command]
        if command != item['Config']['Cmd']:
            differences.setdefault(service, {})['command'] = True
    if differences:
        raise RuntimeError('Compose/runtime mismatch (names only): ' + json.dumps(differences))
    result = {'pinned_services': len(current), 'environment_and_command_match': True,
              'services': {s: {'image': c['Image'], 'id': c['Id'], 'started_at': c['State']['StartedAt']} for s,c in current.items()}}
    print(json.dumps(result))
    return result

def rebuild():
    lock()
    if not (RELEASE/'capture.json').is_file():
        raise RuntimeError('Private source snapshot unavailable; no source-replay build can run')
    captured = json.loads((RELEASE/'capture.json').read_text())
    result = {}
    for service in REPRESENTATIVES:
        item = captured['sources'][service]
        context = RELEASE/service
        for target in ('app', 'installed'):
            files = {str(p.relative_to(context/target)): p.read_bytes() for p in (context/target).rglob('*') if p.is_file()}
            if manifest_files(files) != item['files']:
                raise RuntimeError('Source snapshot changed: ' + service)
        if dock('image','inspect',item['base_tag'])[0]['Id'] != item['image']:
            raise RuntimeError('Pinned dependency image changed: ' + service)
        tag = 'bsla-durable-rebuilt-' + service + ':' + item['source_sha256'][:12]
        output = run('docker','build','--network=none','--pull=false','-t',tag,str(context))
        (RELEASE/('build-'+service+'.log')).write_bytes(output)
        result[service] = {'tag':tag, 'image': dock('image','inspect',tag)[0]['Id']}
        print(json.dumps({'rebuilt': service, **result[service]}), flush=True)
    (RELEASE/'rebuilt.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=['capture','verify','rebuild'])
    mode=p.parse_args().mode
    try:
        {'capture':capture,'verify':verify,'rebuild':rebuild}[mode]()
    except RuntimeError as error:
        raise SystemExit(str(error))
    except subprocess.CalledProcessError as error:
        raise SystemExit('External command failed (details withheld to avoid secret disclosure), exit=' + str(error.returncode))
