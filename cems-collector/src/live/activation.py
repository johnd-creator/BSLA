"""Fail-closed local cutover preflight; no source request or external mutation."""
from __future__ import annotations

import subprocess

LEGACY_SERVICES = ('cems-worker', 'cems-aggregator', 'cems-api', 'cems-web')
PROJECT = 'reliability-cockpit-platform'


def ensure_legacy_stopped(run=subprocess.run):
    names = [f'{PROJECT}-{service}-1' for service in LEGACY_SERVICES]
    result = run(['docker', 'inspect', '--format',
                  '{{.Name}} {{.State.Status}} {{.HostConfig.RestartPolicy.Name}}', *names],
                 capture_output=True, text=True, timeout=10, check=False)
    if result.returncode:
        raise RuntimeError('cannot verify retained legacy CEMS services')
    lines = result.stdout.strip().splitlines()
    if len(lines) != len(names):
        raise RuntimeError('legacy CEMS identity check incomplete')
    expected = {f'/{name}' for name in names}
    for line in lines:
        parts = line.split()
        if len(parts) != 3 or parts[0] not in expected or parts[1] not in {'exited', 'created'} or parts[2] != 'no':
            raise RuntimeError('legacy CEMS service may still collect or restart')
        expected.remove(parts[0])
    if expected:
        raise RuntimeError('legacy CEMS identity check incomplete')
    extra = run(['docker', 'ps', '--filter', f'label=com.docker.compose.project={PROJECT}',
                 '--filter', 'label=com.docker.compose.service=cems-worker', '--format', '{{.ID}}'],
                capture_output=True, text=True, timeout=10, check=False)
    if extra.returncode or extra.stdout.strip():
        raise RuntimeError('another legacy CEMS worker may be running')
