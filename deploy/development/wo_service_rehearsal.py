"""Disposable process-only Compose rehearsal, never a source Collector.

No application credentials, DB server, host ports or external network. Copies
only the approved dependency graph into synthetic shell services. Exercises the
same operation_args as deployment and records process lifecycle, not API UAT.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import time

_spec = importlib.util.spec_from_file_location('activation', Path(__file__).with_name('wo_service_activation.py'))
a = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(a)


def rehearse(image, graph, directory):
    root = Path(directory).resolve()
    root.mkdir(mode=0o700, parents=True, exist_ok=False)
    os.chmod(root, 0o700)
    image_id = json.loads(a.run(['docker','image','inspect',image]))[0]['Id']
    project = 'nadi-wo-compose-rehearsal-' + secrets.token_hex(6)
    if not a.SERVICES <= set(graph) or not all(re.fullmatch('[a-z][a-z0-9-]{0,60}', k) for k in graph):
        raise RuntimeError('CLOSED_SYNTHETIC_GRAPH_REQUIRED')
    if any(dep not in graph for deps in graph.values() for dep in deps):
        raise RuntimeError('COMPLETE_DEPENDENCY_GRAPH_REQUIRED')
    live_before = a.inventory()
    services = {}
    for name,deps in graph.items():
        oneshot = name.endswith('-init') or name in {'mart-ready','mart-migrate','pi-migrate','mart-reader'}
        command = ('if test -f /evidence/armed; then echo '+name+' >> /evidence/forbidden; fi; exit 0') if oneshot else "trap 'exit 0' TERM; while true; do sleep 1 & wait $!; done"
        services[name] = {'image':image_id,'entrypoint':['/bin/sh'],'command':['-c',command],
            'user':str(os.getuid())+':'+str(os.getgid()),'read_only':True,'network_mode':'none',
            'volumes':[str(root)+':/evidence:rw'],'tmpfs':['/var/lib/postgresql/data:rw,size=1048576'],'restart':'no',
            'labels':{'org.opencontainers.image.revision':'synthetic-before'},
            'healthcheck':{'test':['CMD','/bin/true'],'interval':'1s','timeout':'1s','retries':5}}
        if deps:services[name]['depends_on']=deps
    base=root/'compose.json';base.write_text(json.dumps({'services':services}));base.chmod(0o600)
    override=root/'candidate.json';override.write_text(json.dumps({'services':{s:{'labels':{'org.opencontainers.image.revision':'synthetic-after'}} for s in a.SERVICES}}));override.chmod(0o600)
    prefix=['docker','compose','-p',project,'-f',str(base)]
    def snapshots():
        rows=json.loads(a.run(['docker','inspect',*a.run(prefix+['ps','-aq']).decode().split()]))
        return {r['Name']:r for r in rows}
    commands=[];events=[];created=set()
    try:
        pending=set(graph)
        while pending:
            ready=[s for s in pending if not (set(graph[s]) & pending)]
            if not ready:raise RuntimeError('DEPENDENCY_CYCLE')
            for service in sorted(ready):
                a.run(prefix+['up','-d','--no-deps','--no-build','--pull','never',service]);pending.remove(service)
            # Wait for fixture health/completion before initializing its children.
            for _ in range(50):
                rows=snapshots()
                if all(r['State']['Status']=='exited' or r['State'].get('Health',{}).get('Status')=='healthy' for r in rows.values()):break
                time.sleep(.1)
            else:raise RuntimeError('FIXTURE_READINESS_FAILED')
        initial=snapshots();assert len(initial)==len(graph)
        created={r['Id'] for r in initial.values()}
        (root/'armed').write_text('synthetic fixture armed; no plant data\n')
        start=time.time()
        for action in ('quiesce','replace','resume','quiesce','rollback','resume'):
            targets=sorted(a.WRITERS if action in ('quiesce','resume') else a.SERVICES)
            for service in targets:
                before=snapshots();cp=prefix+(['-f',str(override)] if action in ('replace','resume','quiesce') else [])
                # Resume of rolled-back roles must use their baseline config.
                if action=='resume':
                    row=next(r for r in before.values() if r['Config']['Labels']['com.docker.compose.service']==service)
                    cp=prefix+(['-f',str(override)] if row['Config']['Labels']['org.opencontainers.image.revision']=='synthetic-after' else [])
                command=cp+a.operation_args(action,service);operation_start=time.time();a.run(command);commands.append(command)
                after=snapshots();name='/'+project+'-'+service+'-1'
                a.verify_preservation(before,after,{name})
                operation_events=[json.loads(v) for v in a.run(['docker','events','--since',str(operation_start),'--until',str(time.time()),'--filter','type=container','--format','{{json .}}']).splitlines()]
                a.verify_events(operation_events,before,after,name,service,project)
                expected=copy.deepcopy(initial[name])
                revision=before[name]['Config']['Labels']['org.opencontainers.image.revision'] if action in ('quiesce','resume') else ('synthetic-after' if action=='replace' else 'synthetic-before')
                expected['Config']['Labels']['org.opencontainers.image.revision']=revision
                try:a.verify_runtime(after[name],expected,predecessor=before[name])
                except RuntimeError:
                    (root/'failed-runtime-contract.json').write_text(json.dumps({'action':action,'service':service,'expected':a.runtime_contract(expected),'actual':a.runtime_contract(after[name])},indent=2))
                    raise
                if action in ('quiesce','resume') and before[name]['Id']!=after[name]['Id']:raise RuntimeError('FIXTURE_UNEXPECTED_RECREATION')
                if after[name]['State']['Running']!=(action=='resume' or action in ('replace','rollback') and service not in a.WRITERS):raise RuntimeError('FIXTURE_STATE_MISMATCH')
                if (root/'forbidden').exists():raise RuntimeError('FORBIDDEN_FIXTURE_SERVICE_EXECUTED')
        until=time.time()
        events=[json.loads(v) for v in a.run(['docker','events','--since',str(start),'--until',str(until),'--filter','label=com.docker.compose.project='+project,'--format','{{json .}}']).splitlines()]
        lifecycle={'create','start','restart','die','destroy','stop','kill','pause','unpause','update','rename'}
        for event in events:
            if event.get('Action') in lifecycle and event.get('Actor',{}).get('Attributes',{}).get('com.docker.compose.service') not in a.SERVICES:raise RuntimeError('FORBIDDEN_LIFECYCLE_EVENT')
        positive={'activation_module_sha256':hashlib.sha256(Path(a.__file__).read_bytes()).hexdigest(),'graph_sha256':a.digest(graph),'compose_version':a.run(['docker','compose','version','--short']).decode().strip(),'gate':'PASS','fixture_roles':len(initial),'exact_operation_builder':True,
          'commands':commands,'maximo_init_untouched':a.digest(a.preserved(initial['/'+project+'-maximo-init-1']))==a.digest(a.preserved(snapshots()['/'+project+'-maximo-init-1'])),
          'forbidden_marker_absent':not (root/'forbidden').exists(),'lifecycle_events':events,
          'network':'none','application_or_source_credentials':False,'host_ports':False,'database_server_started':False}
        # Separately reproduce the old start hazard only in the armed dummy stack.
        a.run(prefix+a.operation_args('quiesce','maximo-worker'))
        old_before=snapshots();a.run(prefix+['start','maximo-worker']);old_after=snapshots()
        hazard=old_before['/'+project+'-maximo-init-1']['State']['StartedAt']!=old_after['/'+project+'-maximo-init-1']['State']['StartedAt']
        positive['old_compose_start_dependency_reproduced']=hazard
        positive['old_command_forbidden_marker']=(root/'forbidden').exists()
        if not hazard or not positive['old_command_forbidden_marker']:raise RuntimeError('ORIGINAL_CAUSE_NOT_REPRODUCED')
        (root/'result.json').write_text(json.dumps(positive,indent=2));(root/'result.json').chmod(0o600)
        return positive
    finally:
        # Cleanup only this unpredictable synthetic project, never whole platform.
        ids=a.run(['docker','ps','-aq','--filter','label=com.docker.compose.project='+project]).decode().split()
        if ids:a.run(['docker','rm','-f','-v',*ids])
        a.verify_preservation(live_before,a.inventory(),set())


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--image',required=True)
    parser.add_argument('--graph',required=True);parser.add_argument('--directory',required=True)
    args=parser.parse_args();result=rehearse(args.image,json.loads(Path(args.graph).read_text()),args.directory)
    print(json.dumps({k:result[k] for k in ('gate','fixture_roles','maximo_init_untouched','forbidden_marker_absent','old_compose_start_dependency_reproduced')}))
