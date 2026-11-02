"""Synthetic metadata/policy tests; no real token, source service or database."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import yaml

TOOLS = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('stacked_qualify', TOOLS / 'qualify.py')
q = importlib.util.module_from_spec(spec)
spec.loader.exec_module(q)
REQUEST = json.loads(q.PROFILE.read_text())


def metadata(number, sha, ref, base='main', base_sha='a'*40):
    return {'number': number, 'state': 'open', 'merged_at': None,
        'head': {'sha': sha, 'ref': ref, 'repo': {'full_name': q.REPOSITORY}},
        'base': {'sha': base_sha, 'ref': base, 'repo': {'full_name': q.REPOSITORY}}}


def pair():
    return (metadata(120, REQUEST['target_sha'], 'candidate', 'parent', REQUEST['base_sha']),
            metadata(119, REQUEST['base_sha'], 'parent'))


class StackedTests(unittest.TestCase):
    def test_exact_reviewed_stack(self):
        self.assertEqual(q.validate_stack(REQUEST, *pair()), REQUEST)

    def test_profile_rejects_options_refs_foreign_purpose_and_unknown_fields(self):
        for delta in [{'repository':'foreign/repo'}, {'purpose':'production'},
            {'target_pr':True}, {'target_pr':-1}, {'target_sha':'main'},
            {'target_sha':'--upload-pack=evil'}, {'target_sha':None},
            {'base_sha':'119ba2f'}, {'base_pr':120}, {'extra':True}]:
            with self.subTest(delta=delta), self.assertRaises(ValueError):
                q.validate_profile({**REQUEST, **delta})

    def test_target_and_dependency_must_stay_open_exact_same_repository(self):
        for index in (0, 1):
            for change in ('closed','merged','fork-head','foreign-base','sha','number'):
                p = list(copy.deepcopy(pair()))
                if change == 'closed': p[index]['state'] = 'closed'
                if change == 'merged': p[index]['merged_at'] = '2026-01-01'
                if change == 'fork-head': p[index]['head']['repo']['full_name'] = 'foreign/repo'
                if change == 'foreign-base': p[index]['base']['repo']['full_name'] = 'foreign/repo'
                if change == 'sha': p[index]['head']['sha'] = '0'*40
                if change == 'number': p[index]['number'] = 999
                with self.subTest(index=index,change=change), self.assertRaises(ValueError):
                    q.validate_stack(REQUEST, *p)

    def test_main_target_or_moved_retargeted_dependency_fails(self):
        for delta in [{'ref':'main'}, {'ref':'unrelated'}, {'sha':'0'*40}]:
            candidate,parent=pair();candidate['base'].update(delta)
            with self.subTest(delta=delta),self.assertRaises(ValueError):
                q.validate_stack(REQUEST,candidate,parent)

    def test_original_main_selector_and_files_preserved(self):
        q.verify_policy_pins()
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED_PR_BASE'):
            q.main_policy.validate_pr(pair()[0],q.REPOSITORY,'120',REQUEST['target_sha'])

    def test_current_rechecks_tooling_and_both_current_heads(self):
        with patch.dict(os.environ,{'GITHUB_REPOSITORY':q.REPOSITORY,'GITHUB_EVENT_NAME':'pull_request',
                'TOOLS_SHA':'b'*40,'REQUESTER_PR':'121'}), \
                patch.object(q.main_policy,'current_pr') as check, \
                patch.object(q.main_policy,'verify_checkout') as checkout, \
                patch.object(q,'fetch_pr',side_effect=pair()) as fetch:
            self.assertEqual(q.current(),REQUEST)
            check.assert_called_once_with(q.REPOSITORY,'121','b'*40)
            checkout.assert_called_once_with(q.ROOT,'b'*40)
            self.assertEqual([x.args[0] for x in fetch.call_args_list],[120,119])

    def test_untrusted_events_and_metadata_failure_fail_closed(self):
        for event in ['pull_request_target','push','workflow_dispatch']:
            with patch.dict(os.environ,{'GITHUB_REPOSITORY':q.REPOSITORY,'GITHUB_EVENT_NAME':event}),self.assertRaises(ValueError):
                q.current()
        with patch.dict(os.environ,{'GH_TOKEN':'SYNTHETIC_ONLY'}), \
                patch.object(q.urllib.request,'urlopen',side_effect=OSError('synthetic')), \
                self.assertRaisesRegex(ValueError,'PR_METADATA_UNAVAILABLE'):
            q.fetch_pr(120)

    def test_source_ancestry_and_dirty_checks_are_required(self):
        with patch.object(q.main_policy,'verify_checkout') as checkout,patch.object(q.subprocess,'run') as run:
            q.verify_source(Path('source'),REQUEST['target_sha'],REQUEST['base_sha'])
            checkout.assert_called_once_with(Path('source'),REQUEST['target_sha'])
            self.assertEqual(run.call_args.args[0][-3:],['--is-ancestor',REQUEST['base_sha'],REQUEST['target_sha']])
        with patch.object(q.main_policy,'verify_checkout'),patch.object(q.subprocess,'run',side_effect=subprocess.CalledProcessError(1,['git'])):
            with self.assertRaises(subprocess.CalledProcessError):
                q.verify_source(Path('source'),REQUEST['target_sha'],REQUEST['base_sha'])

    def test_workflow_read_only_separation_full_suites_and_fresh_gate(self):
        workflow=q.ROOT/'.github/workflows/nadi-maximo-stacked-development.yml'
        text=workflow.read_text();data=yaml.safe_load(text)
        trigger=data.get('on',data.get(True))
        self.assertEqual(set(trigger),{'pull_request'})
        self.assertNotIn('secrets.',text)
        self.assertNotIn('pull_request_target',text)
        self.assertNotIn('continue-on-error',text)
        self.assertEqual(data['permissions'],{'contents':'read'})
        jobs=data['jobs'];self.assertEqual(jobs['qualify']['strategy']['matrix']['python'],['3.11','3.12'])
        self.assertNotIn('GH_TOKEN',json.dumps(jobs['qualify']))
        for name,job in jobs.items():
            self.assertEqual(job['runs-on'],'ubuntu-latest')
            self.assertNotIn('environment',job)
            for permission in job.get('permissions',{}).values():self.assertEqual(permission,'read')
            for step in job['steps']:
                if 'actions/checkout@' in step.get('uses',''):
                    self.assertIs(step['with']['persist-credentials'],False)
        commands='\n'.join(s.get('run','') for s in jobs['qualify']['steps'])
        for required in ['maximo_ci/run_offline.py','source/maximo-collector','source/reliability-data-contracts','maximo_ci/run_rehearsal.py','maximo_ci/tests','maximo_stacked_ci/tests']:
            self.assertIn(required,commands)
        gate=jobs['development-gate'];self.assertEqual(gate['needs'],['select','qualify'])
        self.assertIn('always()',gate['if']);self.assertIn('recheck',gate['steps'][-1]['run'])
        self.assertNotIn('source/',json.dumps(gate))


if __name__=='__main__':unittest.main()
