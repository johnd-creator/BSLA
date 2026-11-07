"""Fresh-clone safety: no private deployment data and no Docker calls."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import runtime_release as release


class PublicRuntimeBoundaryTest(unittest.TestCase):
    def test_missing_lock_is_clear_and_does_not_contact_docker(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(release, 'LOCK', Path(temp) / 'absent'), patch.object(release, 'run') as run:
            with self.assertRaisesRegex(RuntimeError, 'Private runtime lock unavailable'):
                release.verify()
            run.assert_not_called()

    def test_example_cannot_be_mistaken_for_an_operational_lock(self):
        with patch.object(release, 'LOCK', Path(release.__file__).with_name('runtime-images.lock.example.json')):
            with self.assertRaisesRegex(RuntimeError, 'immutable local image IDs'):
                release.lock()

    def test_lock_rejects_missing_extra_service_and_nonimmutable_image(self):
        good = {'release': 'synthetic', 'project': 'synthetic-platform', 'images': {
            s: 'sha256:' + 'a' * 64 for s in (*release.REPRESENTATIVES, 'maximo-worker')}}
        with tempfile.TemporaryDirectory() as temp, patch.object(release, 'LOCK', Path(temp) / 'lock.json'):
            for mutate in (lambda v: v['images'].pop('maximo-worker'), lambda v: v['images'].update(extra='sha256:' + 'b' * 64), lambda v: v['images'].update({'maximo-api': 'mutable:latest'})):
                value = json.loads(json.dumps(good)); mutate(value)
                release.LOCK.write_text(json.dumps(value))
                with self.assertRaises(RuntimeError): release.lock()
            release.LOCK.write_text(json.dumps(good))
            self.assertEqual(release.lock(), good)

    def test_verify_and_service_cli_fail_without_writing_or_docker(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); missing = root / 'missing-release'
            env = dict(os.environ, BSLA_RUNTIME_LOCK=str(root / 'missing-lock'), BSLA_RUNTIME_RELEASE_DIR=str(missing))
            for name, args in [('runtime_release.py', ['verify']), ('runtime_service.py', ['restart', 'maximo-worker'])]:
                result = subprocess.run([sys.executable, str(Path(release.__file__).with_name(name)), *args], env=env, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('Private runtime lock unavailable', result.stderr)
                self.assertNotIn('Traceback', result.stderr)
            self.assertFalse(missing.exists())

    def test_private_compose_paths_are_explicit_and_never_shell_expanded(self):
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / 'private model.yaml'; file.write_text('name: synthetic')
            with patch.dict(os.environ, {'BSLA_RUNTIME_COMPOSE_FILES': json.dumps([str(file)])}), patch.object(release, 'run', return_value=b'{}') as run:
                self.assertEqual(release.compose_model(), {})
                self.assertIn(str(file), run.call_args.args)
            with patch.dict(os.environ, {'BSLA_RUNTIME_COMPOSE_FILES': 'not-json'}), patch.object(release, 'run') as run:
                with self.assertRaises(RuntimeError): release.compose_model()
                run.assert_not_called()
