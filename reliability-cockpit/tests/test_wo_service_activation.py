"""Safety and negative admission tests; no operational Docker or DB calls."""
import copy
import importlib.util
from pathlib import Path
import unittest

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

    def test_preservation_detects_even_successful_one_shot_or_recreation(self):
        old={'target':container(),'init':container(),'unrelated':container()}
        for key in ('init','unrelated'):
            for mutate in (lambda c:c['State'].__setitem__('StartedAt','new'),
                           lambda c:c.__setitem__('Id','new'),lambda c:c.__setitem__('RestartCount',1)):
                new=copy.deepcopy(old);mutate(new[key])
                with self.assertRaises(RuntimeError):m.verify_preservation(old,new,{'target'})
        with self.assertRaises(RuntimeError):m.verify_preservation(old,{**old,'unexpected':container()},{'target'})
        new=copy.deepcopy(old);new['target']['Id']='new';m.verify_preservation(old,new,{'target'})


if __name__=='__main__':unittest.main()
