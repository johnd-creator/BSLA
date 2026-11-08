"""No Docker/network in these tests. Cutover must fail closed."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from src.live.activation import ensure_legacy_stopped, LEGACY_SERVICES, PROJECT
from src.live.__main__ import main


def result(text='', code=0):
    return SimpleNamespace(stdout=text, returncode=code)


def states(status='exited', restart='no'):
    return '\n'.join(f'/{PROJECT}-{s}-1 {status} {restart}' for s in LEGACY_SERVICES)


class ActivationTest(unittest.TestCase):
    def test_verified_stopped_services_and_no_extra_worker(self):
        run=Mock(side_effect=[result(states()), result()])
        ensure_legacy_stopped(run)
        self.assertEqual(run.call_count, 2)

    def test_running_restartable_missing_or_extra_workers_rejected(self):
        for responses in ([result(states('running'))], [result(states(restart='unless-stopped'))],
                          [result('', 1)], [result(states()), result('worker-id')],
                          [result(states().splitlines()[0])]):
            with self.subTest(responses=responses), self.assertRaises(RuntimeError):
                ensure_legacy_stopped(Mock(side_effect=responses))

    def test_plc_launch_requires_explicit_safe_cutover(self):
        with patch('sys.stderr'), self.assertRaises(SystemExit) as raised:
            main(['--source', 'plc'])
        self.assertEqual(raised.exception.code, 2)

    def test_unverified_host_refused_before_preflight(self):
        with patch('src.live.activation.ensure_legacy_stopped') as preflight, patch('sys.stderr'), self.assertRaises(SystemExit):
            main(['--source', 'plc','--confirm-exclusive-reader','--plc-host','guessed.example'])
        preflight.assert_not_called()

    def test_preflight_failure_never_calls_server(self):
        with patch('src.live.activation.ensure_legacy_stopped', side_effect=RuntimeError('not stopped')), patch('sys.stderr'), self.assertRaises(SystemExit):
            main(['--source','plc','--confirm-exclusive-reader','--plc-host','127.0.0.1'])
