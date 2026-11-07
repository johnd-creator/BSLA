"""Hermetic safety tests for the release pins and exact-container controller."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs,unquote,urlsplit

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import runtime_release as release
import runtime_service as service

class PinTest(unittest.TestCase):
    def setUp(self):
        fake = {'project': 'synthetic-platform', 'release': 'synthetic-test', 'images': {
            name: 'sha256:' + str(index + 1) * 64 for index, name in enumerate((*release.REPRESENTATIVES, 'maximo-worker'))}}
        patcher = patch.object(release, 'lock', return_value=fake)
        patcher.start(); self.addCleanup(patcher.stop)
    def model(self):
        value=release.lock()
        return {'name':value['project'],'services':{s:{'image':i,'pull_policy':'never'} for s,i in value['images'].items()}}
    def test_accepts_exact_immutable_release(self):release.validate_model(self.model())
    def test_refuses_changed_project(self):
        model=self.model();model['name']='another-project'
        with self.assertRaises(RuntimeError):release.validate_model(model)
    def test_refuses_mutable_old_missing_or_buildable_image(self):
        for change in ({'image':'old:latest'},{'build':'./maximo-collector'},{'pull_policy':'always'},{'image':None}):
            with self.subTest(change=change):
                model=self.model();model['services']['maximo-worker'].update(change)
                with self.assertRaises(RuntimeError):release.validate_model(model)
    def test_only_default_false_normalization_is_allowed(self):
        self.assertEqual(service.normalized_host({'OomKillDisable':None}),{'OomKillDisable':False})
        self.assertNotEqual(service.normalized_host({'OomKillDisable':True}),{'OomKillDisable':False})

class Engine:
    def __init__(self):
        self.calls=[];self.uncertain=False;self.mismatch=False;self.fail_start=False
        self.image='sha256:'+'a'*64;self.original={
            'Id':'old','Image':self.image,'Name':'/test-maximo-api-1','State':{'Running':True},
            'Config':{'Env':['DATABASE_URL=synthetic-only'],'Cmd':['serve'],'User':'app','Image':self.image,
                'Labels':{'com.docker.compose.project':'test','com.docker.compose.service':'maximo-api'}},
            'HostConfig':{'OomKillDisable':None,'ReadonlyRootfs':False,'NetworkMode':'test_platform'},
            'NetworkSettings':{'Networks':{'test_platform':{'Aliases':['old','maximo-api','test-maximo-api-1']}}}}
        self.containers={'old':copy.deepcopy(self.original)}
    def get(self,key):
        for c in self.containers.values():
            if c['Id']==key or c['Name'].lstrip('/')==key:return c
        raise RuntimeError('Docker HTTP 404; response withheld')
    def __call__(self,method,path,payload=None):
        self.calls.append((method,path))
        url=urlsplit(path);parts=[unquote(p) for p in url.path.split('/') if p];query=parse_qs(url.query)
        if parts==['containers','json']:return [copy.deepcopy(c) for c in self.containers.values() if c['State']['Running']]
        if parts==['containers','create']:
            config=copy.deepcopy(payload);host=config.pop('HostConfig');net=config.pop('NetworkingConfig')
            if self.mismatch:config['User']='root'
            host['OomKillDisable']=False
            self.containers['new']={'Id':'new','Image':self.image,'Name':'/'+query['name'][0],
                'State':{'Running':False},'Config':config,'HostConfig':host,
                'NetworkSettings':{'Networks':net['EndpointsConfig']}}
            if self.uncertain:raise TimeoutError('synthetic uncertain create')
            return {'Id':'new'}
        c=self.get(parts[1]);action=parts[2] if len(parts)>2 else ''
        if method=='GET' and action=='json':return copy.deepcopy(c)
        if action=='stop':c['State']['Running']=False
        elif action=='rename':
            name='/'+query['name'][0]
            if any(x['Name']==name and x['Id']!=c['Id'] for x in self.containers.values()):raise RuntimeError('Name occupied')
            c['Name']=name
        elif action=='start':
            if self.fail_start and c['Id']=='new':raise RuntimeError('Synthetic start failure')
            c['State']['Running']=True
        else:raise AssertionError((method,path))

class ControllerTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.engine=Engine()
        patches=[patch.object(release,'RELEASE',self.root),patch.object(release,'lock',return_value={
            'project':'test','images':{'maximo-api':self.engine.image}}),
            patch.object(service,'api',side_effect=self.engine),patch.object(service,'healthy')]
        self.mocks=[p.start() for p in patches]
        for p in patches:self.addCleanup(p.stop)
    def state(self):return json.loads(next(self.root.glob('recreate-*.json')).read_text())
    def assert_original_active(self):
        self.assertTrue(self.engine.get('old')['State']['Running'])
        self.assertEqual(self.engine.get('old')['Name'],'/test-maximo-api-1')
        self.assertFalse(self.engine.get('new')['State']['Running'])
        self.assertFalse(any(m=='DELETE' for m,p in self.engine.calls))
    def test_exact_configuration_clone_preserves_env_without_modifying_original(self):
        before=copy.deepcopy(self.engine.original);payload=service.clone_payload(before,'tx')
        self.assertEqual(before,self.engine.original)
        self.assertEqual(payload['Env'],before['Config']['Env'])
        self.assertEqual(payload['HostConfig'],before['HostConfig'])
        self.assertNotIn('old',payload['NetworkingConfig']['EndpointsConfig']['test_platform']['Aliases'])
    def test_success_keeps_original_stopped_and_supports_rollback(self):
        service.recreate('maximo-api');state=self.state()
        self.assertEqual(state['status'],'ACTIVE_VERIFIED')
        self.assertTrue(self.engine.get('new')['State']['Running']);self.assertFalse(self.engine.get('old')['State']['Running'])
        self.assertNotIn('synthetic-only',next(self.root.glob('recreate-*.json')).read_text())
        service.rollback(state,next(self.root.glob('recreate-*.json')))
        self.assert_original_active()
    def test_uncertain_create_resolved_without_repeating_or_stopping_original(self):
        self.engine.uncertain=True
        with self.assertRaises(TimeoutError):service.recreate('maximo-api')
        self.assert_original_active();self.assertEqual(self.state()['status'],'ROLLED_BACK')
        self.assertEqual(sum('/containers/create?' in p for m,p in self.engine.calls),1)
        self.assertFalse(any(p.startswith('/containers/old/stop') for m,p in self.engine.calls))
    def test_configuration_mismatch_never_stops_original(self):
        self.engine.mismatch=True
        with self.assertRaisesRegex(RuntimeError,'Configuration not preserved'):service.recreate('maximo-api')
        self.assert_original_active()
        self.assertFalse(any(p.startswith('/containers/old/stop') for m,p in self.engine.calls))
    def test_failed_candidate_start_restores_original(self):
        self.engine.fail_start=True
        with self.assertRaisesRegex(RuntimeError,'Synthetic start failure'):service.recreate('maximo-api')
        self.assert_original_active()
    def test_failed_health_check_restores_original(self):
        self.mocks[-1].side_effect=[RuntimeError('synthetic health failure'),None]
        with self.assertRaisesRegex(RuntimeError,'synthetic health failure'):service.recreate('maximo-api')
        self.assert_original_active()
    def test_duplicate_running_service_refused_before_create(self):
        duplicate=copy.deepcopy(self.engine.original);duplicate['Id']='duplicate';duplicate['Name']='/duplicate'
        self.engine.containers['duplicate']=duplicate
        with self.assertRaisesRegex(RuntimeError,'Duplicate running'):service.recreate('maximo-api')
        self.assertFalse(any('/containers/create?' in p for m,p in self.engine.calls))
    def test_wrong_pinned_image_refused(self):
        self.engine.containers['old']['Image']='sha256:wrong'
        with self.assertRaisesRegex(RuntimeError,'Expected pinned'):service.recreate('maximo-api')
    def test_rollback_refuses_unrelated_container_at_original_name(self):
        service.recreate('maximo-api');state=self.state()
        self.engine.get('new')['Name']='/candidate-newer-name'
        foreign=copy.deepcopy(self.engine.original);foreign['Id']='foreign';self.engine.containers['foreign']=foreign
        with self.assertRaisesRegex(RuntimeError,'Concurrent active'):service.rollback(state,next(self.root.glob('recreate-*.json')))
        self.assertTrue(self.engine.get('foreign')['State']['Running'])

if __name__=='__main__':unittest.main()
