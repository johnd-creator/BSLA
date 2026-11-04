"""Safety and negative admission tests; no operational Docker or DB calls."""
import copy
import importlib.util
from pathlib import Path
import unittest
import tempfile
import json
import os
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
import fcntl

path = Path(__file__).resolve().parents[2] / 'deploy/development/wo_service_activation.py'
spec = importlib.util.spec_from_file_location('wo_service_activation', path)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
rehearsal_spec = importlib.util.spec_from_file_location('wo_service_rehearsal', path.with_name('wo_service_rehearsal.py'))
r = importlib.util.module_from_spec(rehearsal_spec); rehearsal_spec.loader.exec_module(r)


def container():
    return {'Id':'old', 'Name':'/example', 'Image':'sha256:old','RestartCount':0,
      'State':dict(Status='exited',Running=False,Paused=False,Dead=False,ExitCode=0,StartedAt='old',FinishedAt='old'),
      'Config': {'Hostname':'old','Image':'sha256:old','Env':['A=1','B=2'],
       'Labels':{'org.opencontainers.image.revision':'old'},'Cmd':['safe'],'Entrypoint':None,'User':'app'},
      'HostConfig': {'Dns':[], 'DnsOptions':[], 'DnsSearch':[], 'OomKillDisable':None,
                     'Privileged':False,'ReadonlyRootfs':False,'Memory':0},
      'Mounts':[], 'NetworkSettings':{'Networks':{'existing':{}},'Ports':{}}}


class Safety(unittest.TestCase):
    def label_fixture(self):
        before = container()
        before['Config']['Labels'][m.TASK_LABEL] = 'original-task'
        old_image = {'Config': {'Labels': dict(before['Config']['Labels'])}}
        new_image = {'Config': {'Labels': {
            'org.opencontainers.image.revision': 'new', m.TASK_LABEL: 'new-task'}}}
        return before, old_image, new_image

    def test_inherited_task_label_conflict_is_not_hidden_by_equal_renders(self):
        before, old_image, new_image = self.label_fixture()
        old = {'labels': {'org.opencontainers.image.revision': 'old'}}
        new = {'labels': {'org.opencontainers.image.revision': 'new'}}
        with self.assertRaisesRegex(RuntimeError, 'EFFECTIVE_IMAGE_LABEL_CHANGE'):
            m.verify_effective_labels(before, old_image, new_image, old, new, 'new')
        new['labels'][m.TASK_LABEL] = 'original-task'
        m.verify_effective_labels(before, old_image, new_image, old, new, 'new')
        # Runtime checks still reject the historical bad container outright.
        bad = m.expected_runtime(before, 'sha256:new', 'new')
        bad['Config']['Labels'][m.TASK_LABEL] = 'new-task'
        with self.assertRaisesRegex(RuntimeError, 'RUNTIME_CONTRACT_CHANGED'):
            m.verify_runtime(bad, m.expected_runtime(before, 'sha256:new', 'new'))

    def test_effective_label_admission_rejects_baseline_drift_and_extra_labels(self):
        before, old_image, new_image = self.label_fixture()
        new = {'labels': {m.TASK_LABEL: 'original-task'}}
        old_image['Config']['Labels'][m.TASK_LABEL] = 'different-baseline'
        with self.assertRaisesRegex(RuntimeError, 'BASELINE_EFFECTIVE'):
            m.verify_effective_labels(before, old_image, new_image, {}, new, 'new')
        old_image['Config']['Labels'][m.TASK_LABEL] = 'original-task'
        new_image['Config']['Labels']['unexpected'] = 'inherited'
        with self.assertRaisesRegex(RuntimeError, 'EFFECTIVE_IMAGE_LABEL_CHANGE'):
            m.verify_effective_labels(before, old_image, new_image, {}, new, 'new')

    def test_label_maps_reject_reserved_metadata_and_ambiguous_values(self):
        for labels in ([m.TASK_LABEL + '=value'], {'flag': True}, {'': 'value'},
                       {m.COMPOSE_LABEL_PREFIX + 'service': 'maximo-init'}):
            for image, rendered in (({'Config': {'Labels': labels}}, {}),
                                    ({'Config': {}}, {'labels': labels})):
                with self.assertRaises(RuntimeError):m.effective_labels(image, rendered)
        self.assertEqual(m.effective_labels({'Config': {'Labels': {'a': 'old'}}},
                                           {'labels': {'a': 'explicit'}}), {'a': 'explicit'})

    def test_only_exact_services_and_no_dependencies(self):
        for service in m.SERVICES:
            for action in ('replace','rollback'):
                args=m.operation_args(action,service)
                self.assertIn('--no-deps',args);self.assertIn('--no-build',args)
                self.assertEqual(args[-1],service); self.assertIn('--force-recreate',args)
                self.assertEqual('--no-start' in args,service in m.WRITERS)
        for service in m.FORBIDDEN|{'','maximo-api maximo-init','--remove-orphans'}:
            with self.assertRaises(RuntimeError):m.operation_args('replace',service)
        for action in ('start','restart','down','run','create','preflight'):
            with self.assertRaises(RuntimeError):m.operation_args(action,'maximo-worker')

    def test_resume_keeps_existing_container_and_skips_dependencies(self):
        for service in m.WRITERS:
            args=m.operation_args('resume',service)
            self.assertIn('--no-deps',args);self.assertIn('--no-recreate',args)
            self.assertNotIn('--force-recreate',args)
        with self.assertRaises(RuntimeError):m.operation_args('resume','maximo-api')
        with self.assertRaises(RuntimeError):m.operation_args('quiesce','cockpit-api')

    def test_empty_default_and_env_order_are_equivalent(self):
        old=container();new=copy.deepcopy(old)
        new['Config']['Hostname']='new';new['Config']['Env'].reverse()
        for key in ('Dns','DnsOptions','DnsSearch'):new['HostConfig'][key]=None
        new['HostConfig']['OomKillDisable']=False
        m.verify_runtime(new,old)

    def test_generated_replacement_label_is_bounded(self):
        old=container();old['Config']['Labels']['com.docker.compose.service']='maximo-api'
        new=copy.deepcopy(old);new['Config']['Labels']['com.docker.compose.replace']='maximo-api-1'
        m.verify_runtime(new,old)
        new['Config']['Labels']['com.docker.compose.replace']=old['Id']
        m.verify_runtime(new,old)
        new['Config']['Labels']['com.docker.compose.replace']='a'*64
        with self.assertRaises(RuntimeError):m.verify_runtime(new,old)
        new['Config']['Labels']['com.docker.compose.replace']='different-service-1'
        with self.assertRaises(RuntimeError):m.verify_runtime(new,old)

    def test_real_host_config_changes_are_rejected(self):
        for key,value in [('Dns',['10.0.0.1']),('DnsOptions',['ndots:1']),('DnsSearch',['outside']),
                          ('OomKillDisable',True),('Privileged',True),('Memory',1024),('ReadonlyRootfs',True)]:
            old=container();new=copy.deepcopy(old);new['HostConfig'][key]=value
            with self.subTest(key=key),self.assertRaises(RuntimeError):m.verify_runtime(new,old)
        old=container();new=copy.deepcopy(old);del new['HostConfig']['Dns']
        with self.assertRaises(RuntimeError):m.verify_runtime(new,old)

    def test_environment_command_user_mount_network_image_and_labels_rejected(self):
        mutations=[lambda c:c['Config'].__setitem__('Env',['A=3','B=2']),
          lambda c:c['Config'].__setitem__('Cmd',['mxcollector','init-db']),
          lambda c:c['Config'].__setitem__('Entrypoint',['sh']),
          lambda c:c['Config'].__setitem__('User','root'),
          lambda c:c['Mounts'].append({'Source':'/other'}),
          lambda c:c['NetworkSettings'].__setitem__('Networks',{'other':{}}),
          lambda c:c.__setitem__('Image','sha256:other'),
          lambda c:c['Config']['Labels'].__setitem__('org.opencontainers.image.revision','other')]
        for mutation in mutations:
            old=container();new=copy.deepcopy(old);mutation(new)
            with self.assertRaises(RuntimeError):m.verify_runtime(new,old)
        with self.assertRaises(RuntimeError):m.environment(['A=1','A=1'])

    def test_lifecycle_events_require_known_ID_project_service_and_name(self):
        name='/'+m.PROJECT+'-maximo-api-1';old=container();old['Id']='a'*64;new=copy.deepcopy(old);new['Id']='b'*64
        event={'Action':'create','Actor':{'ID':new['Id'],'Attributes':{'name':old['Id'][:12]+'_'+name.lstrip('/'),'com.docker.compose.project':m.PROJECT,'com.docker.compose.service':'maximo-api'}}}
        m.verify_events([event],{name:old},{name:new},name,'maximo-api')
        for key,value in [('name','forbidden'),('com.docker.compose.service','maximo-init'),('com.docker.compose.project','other')]:
            bad=copy.deepcopy(event);bad['Actor']['Attributes'][key]=value
            with self.assertRaises(RuntimeError):m.verify_events([bad],{name:old},{name:new},name,'maximo-api')
        bad=copy.deepcopy(event);bad['Actor']['ID']='c'*64
        with self.assertRaises(RuntimeError):m.verify_events([bad],{name:old},{name:new},name,'maximo-api')

    def test_preservation_detects_even_successful_one_shot_or_recreation(self):
        old={'target':container(),'init':container(),'unrelated':container()}
        for key in ('init','unrelated'):
            for mutate in (lambda c:c['State'].__setitem__('StartedAt','new'),
                           lambda c:c.__setitem__('Id','new'),lambda c:c.__setitem__('RestartCount',1)):
                new=copy.deepcopy(old);mutate(new[key])
                with self.assertRaises(RuntimeError):m.verify_preservation(old,new,{'target'})
        with self.assertRaises(RuntimeError):m.verify_preservation(old,{**old,'unexpected':container()},{'target'})
        new=copy.deepcopy(old);new['target']['Id']='new';m.verify_preservation(old,new,{'target'})




class RehearsalImagePreservation(unittest.TestCase):
    def test_untagged_base_rejected_before_tag_or_container_operations(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(r.a,'run',return_value=json.dumps([{'Id':'sha256:old','RepoTags':[],'Config':{}}]).encode()) as run,patch.object(r.a,'inventory') as inventory:
                with self.assertRaisesRegex(RuntimeError,'PREEXISTING_TAGGED'):
                    r.rehearse('sha256:old',{x:{} for x in m.SERVICES},str(Path(directory)/'new'))
                self.assertEqual(run.call_count,1);inventory.assert_not_called()

    def test_onbuild_is_not_executed_by_metadata_fixture_builds(self):
        with self.assertRaisesRegex(RuntimeError,'ONBUILD_FORBIDDEN'):
            r.retained_base_tags({'RepoTags':['existing:base'],'Config':{'OnBuild':['RUN unexpected']}})

    def test_cleanup_keeps_original_tagged_image_and_only_removes_fixture_aliases(self):
        removed=[]
        def run(args):
            if args[2]=='rm':removed.append(args[-1]);return b''
            return json.dumps([{'Id':'sha256:old','RepoTags':['existing:base','fixture:base']}]).encode()
        with patch.object(r.a,'run',side_effect=run),patch.object(r.subprocess,'run') as probe:
            probe.return_value.returncode=0
            r.cleanup_fixture_images(['fixture:base','fixture:before','fixture:after'],'sha256:old',{'existing:base'})
        self.assertEqual(removed,['fixture:after','fixture:before','fixture:base'])
        self.assertNotIn('sha256:old',removed)

    def test_cleanup_preserves_last_alias_if_original_reference_disappears(self):
        removed=[]
        def run(args):
            if args[2]=='rm':removed.append(args[-1]);return b''
            return json.dumps([{'Id':'sha256:old','RepoTags':['fixture:base']}]).encode()
        with patch.object(r.a,'run',side_effect=run),patch.object(r.subprocess,'run') as probe:
            probe.return_value.returncode=0
            with self.assertRaisesRegex(RuntimeError,'PRESERVE_FIXTURE_ALIAS'):
                r.cleanup_fixture_images(['fixture:base','fixture:before','fixture:after'],'sha256:old',{'existing:base'})
        self.assertEqual(removed,['fixture:after','fixture:before'])


class OperationalAdmission(unittest.TestCase):
    def setup_operation(self, directory):
        root=Path(directory);root.chmod(0o700);self.receipts=root/'receipts';self.receipts.mkdir(mode=0o700)
        self.before={};services={}
        for role in sorted(m.SERVICES):
            row=container();name='/'+m.PROJECT+'-'+role+'-1';row['Name']=name;row['Id']=role+'-old'
            row['Config']['Labels']['com.docker.compose.service']=role
            if role=='mart-projector':row['Config']['Env'].append('RELIABILITY_CONTRACTS_ROOT=/contracts')
            self.before[name]=row;services[role]={'image_before':'sha256:old','image_after':'sha256:new','baseline_runtime':copy.deepcopy(row)}
        for i in range(31):
            row=container();row['Id']='unrelated-'+str(i);self.before['/unrelated-'+str(i)]=row
        now=datetime.now(timezone.utc)
        self.plan={'purpose':'NADI_WO_ACTIVATION_CORRECTION_01','operator':'owner-approved-operator','candidate_sha':'candidate',
                   'services':services,'role_identities':{k:[v['Id'],v['Image']] for k,v in self.before.items()},
                   'window':{'start':(now-timedelta(hours=1)).isoformat(),'end':(now+timedelta(hours=1)).isoformat()}}
        self.planpath=root/'plan.json';self.ownerpath=root/'owner.json';self.save()

    def save(self):
        self.planpath.write_text(json.dumps(self.plan));self.planpath.chmod(0o600)
        import hashlib
        self.owner={'purpose':self.plan['purpose'],'verdict':'GO','plan_sha256':hashlib.sha256(self.planpath.read_bytes()).hexdigest(),'operator':self.plan['operator']}
        self.ownerpath.write_text(json.dumps(self.owner));self.ownerpath.chmod(0o600)

    def invoke(self):return m.execute(self.planpath,'resume','maximo-worker',self.ownerpath,self.receipts)

    def test_bad_GO_expired_window_and_private_mode_fail_before_mutation(self):
        for kind in ('GO','window','mode'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as directory:
                self.setup_operation(directory)
                if kind=='GO':self.owner['plan_sha256']='wrong';self.ownerpath.write_text(json.dumps(self.owner))
                elif kind=='window':self.plan['window']['end']=(datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat();self.save()
                else:self.ownerpath.chmod(0o644)
                with patch.object(m,'validate_plan',side_effect=lambda p:p),patch.object(m,'inventory',return_value=self.before),patch.object(m,'run') as run:
                    with self.assertRaises(RuntimeError):self.invoke()
                    run.assert_not_called();self.assertEqual(list(self.receipts.glob('*.json')),[])

    def test_checkpoint_failure_prevents_command(self):
        with tempfile.TemporaryDirectory() as directory:
            self.setup_operation(directory)
            with patch.object(m,'validate_plan',side_effect=lambda p:p),patch.object(m,'inventory',return_value=self.before),patch.object(m,'compose_prefix',return_value=['docker','compose']),patch.object(m,'write_exclusive',side_effect=OSError('disk-full')),patch.object(m,'run') as run:
                with self.assertRaises(OSError):self.invoke()
                run.assert_not_called()

    def test_failed_observation_retains_prepared_and_no_completed_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            self.setup_operation(directory)
            with patch.object(m,'validate_plan',side_effect=lambda p:p),patch.object(m,'inventory',side_effect=[self.before,RuntimeError('observation-unavailable')]),patch.object(m,'compose_prefix',return_value=['docker','compose']),patch.object(m,'run',return_value=b'') as run:
                with self.assertRaises(RuntimeError):self.invoke()
                self.assertEqual(run.call_count,1)
                self.assertEqual(len(list(self.receipts.glob('resume-maximo-worker-*.json'))),1)
                self.assertEqual(list(self.receipts.glob('*.completed.json')),[])

    def test_concurrent_sequence_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            self.setup_operation(directory);fd=os.open(self.receipts/'activation.lock',os.O_CREAT|os.O_RDWR,0o600)
            try:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
                with patch.object(m,'validate_plan',side_effect=lambda p:p),patch.object(m,'run') as run:
                    with self.assertRaises(BlockingIOError):self.invoke()
                    run.assert_not_called()
            finally:os.close(fd)

    def test_unknown_engine_fails_before_image_or_compose_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            self.setup_operation(directory);self.plan.update(version=1,project=m.PROJECT,repository=directory,env_file=str(Path(directory)/'.env.platform'),container_count=35,forbidden=list(m.FORBIDDEN),docker_context='expected',compose_version='expected',engine_id='expected')
            with patch.object(m,'run',side_effect=[b'expected',b'expected',b'wrong-engine']) as run:
                with self.assertRaisesRegex(RuntimeError,'ENGINE_IDENTITY'):m.validate_plan(self.plan)
                self.assertEqual(run.call_count,3)

    def test_inherited_label_preflight_stops_before_inventory_or_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            self.setup_operation(directory)
            factual=self.plan['services']['cockpit-api']['baseline_runtime']
            factual['Config']['Labels'][m.TASK_LABEL]='original-task'
            self.plan.update(version=1,project=m.PROJECT,repository=directory,
                env_file=str(Path(directory)/'.env.platform'),container_count=35,
                forbidden=list(m.FORBIDDEN),docker_context='expected',
                compose_version='expected',engine_id='expected')
            self.save()
            old={'image':'sha256:old','labels':{'org.opencontainers.image.revision':'old'}}
            new={'image':'sha256:new','labels':{'org.opencontainers.image.revision':'candidate'}}
            def read_only(args):
                if args[1]=='image':
                    candidate=args[-1]=='sha256:new'
                    return json.dumps([{'Id':args[-1],'Config':{'Labels':{
                        'org.opencontainers.image.revision':'candidate' if candidate else 'old',
                        m.TASK_LABEL:'new-task' if candidate else 'original-task'}}}]).encode()
                if 'config' in args:
                    return json.dumps({'services':{'cockpit-api':new if 'candidate' in args else old}}).encode()
                return b'expected'
            prefix=lambda plan,service,candidate:['docker','compose','candidate' if candidate else 'baseline']
            with patch.object(m,'compose_prefix',side_effect=prefix),patch.object(m,'run',side_effect=read_only) as run,patch.object(m,'inventory') as inventory:
                with self.assertRaisesRegex(RuntimeError,'UNAPPROVED_EFFECTIVE_IMAGE_LABEL_CHANGE'):
                    self.invoke()
                inventory.assert_not_called()
                self.assertTrue(all('up' not in call.args[0] and 'stop' not in call.args[0] for call in run.call_args_list))
                self.assertEqual(list(self.receipts.glob('*.json')),[])

    def test_multi_invocation_ID_metadata_rollback_then_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            self.setup_operation(directory)
            name='/'+m.PROJECT+'-maximo-worker-1';state=copy.deepcopy(self.before)
            state[name]['State'].update(Status='running',Running=True)
            sequence=[];events=[]
            def run(args):
                if args[1]=='events':return b'\n'.join(json.dumps(event).encode() for event in events)
                service=args[-1];self.assertEqual(service,'maximo-worker');prior=copy.deepcopy(state[name]);events.clear()
                if 'stop' in args:state[name]['State'].update(Status='exited',Running=False)
                elif '--force-recreate' in args:
                    target=m.expected_runtime(self.plan['services'][service]['baseline_runtime'],'sha256:new','candidate') if 'candidate' in args else copy.deepcopy(self.plan['services'][service]['baseline_runtime'])
                    target['Id']='new-'+str(len(sequence));target['Config']['Hostname']=target['Id'];target['Config']['Labels']['com.docker.compose.replace']=prior['Id'];target['State'].update(Status='created',Running=False);state[name]=target
                else:state[name]['State'].update(Status='running',Running=True)
                events.append({'Action':'start' if state[name]['State']['Running'] else 'stop','Actor':{'ID':state[name]['Id'],'Attributes':{'name':name.lstrip('/'),'com.docker.compose.project':m.PROJECT,'com.docker.compose.service':service}}})
                sequence.append(args);return b''
            prefix=lambda plan,service,candidate:['docker','compose','candidate' if candidate else 'baseline']
            with patch.object(m,'validate_plan',side_effect=lambda p:p),patch.object(m,'inventory',side_effect=lambda:copy.deepcopy(state)),patch.object(m,'compose_prefix',side_effect=prefix),patch.object(m,'run',side_effect=run):
                for action in ('quiesce','replace','rollback','resume','quiesce','replace','resume'):
                    result=m.execute(self.planpath,action,'maximo-worker',self.ownerpath,self.receipts)
                    self.assertEqual(result['status'],'VERIFIED')
                self.assertEqual(len(sequence),7)
                self.assertTrue(state[name]['State']['Running'])
                # Unknown receipt provenance cannot admit an otherwise known-ID
                # metadata value after rollback/re-entry.
                for path in self.receipts.glob('*.json'):
                    if '.completed.' in path.name or '.observed.' in path.name:continue
                    value=json.loads(path.read_text());value['plan_sha256']='other-plan';path.write_text(json.dumps(value))
                with self.assertRaisesRegex(RuntimeError,'REPLACEMENT_LABEL'):
                    m.execute(self.planpath,'quiesce','maximo-worker',self.ownerpath,self.receipts)
                self.assertEqual(len(sequence),7)

    def test_file_and_environment_seals_fail_before_render(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);env=root/'.env.platform';env.write_text('SYNTHETIC=only');env.chmod(0o600)
            file=root/'compose.json';file.write_text('{}')
            plan={'env_file':str(env),'env_sha256':'wrong','services':{'maximo-api':{'files':[{'path':str(file),'sha256':'wrong'}]}}}
            with patch.object(m,'run') as run:
                with self.assertRaisesRegex(RuntimeError,'COMPOSE_FILE_SEAL'):m.compose_prefix(plan,'maximo-api',False)
                import hashlib
                plan['services']['maximo-api']['files'][0]['sha256']=hashlib.sha256(file.read_bytes()).hexdigest()
                with self.assertRaisesRegex(RuntimeError,'ENV_FILE_SEAL'):m.compose_prefix(plan,'maximo-api',False)
                run.assert_not_called()

if __name__=='__main__':unittest.main()
