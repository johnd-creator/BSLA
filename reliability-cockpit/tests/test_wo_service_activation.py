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


def container():
    return {'Id':'old', 'Name':'/example', 'Image':'sha256:old','RestartCount':0,
      'State':dict(Status='exited',Running=False,Paused=False,Dead=False,ExitCode=0,StartedAt='old',FinishedAt='old'),
      'Config': {'Hostname':'old','Image':'sha256:old','Env':['A=1','B=2'],
       'Labels':{'org.opencontainers.image.revision':'old'},'Cmd':['safe'],'Entrypoint':None,'User':'app'},
      'HostConfig': {'Dns':[], 'DnsOptions':[], 'DnsSearch':[], 'OomKillDisable':None,
                     'Privileged':False,'ReadonlyRootfs':False,'Memory':0},
      'Mounts':[], 'NetworkSettings':{'Networks':{'existing':{}},'Ports':{}}}


class Safety(unittest.TestCase):
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
