"""Disposable process-only Compose rehearsal, never a source Collector.

No application credentials, DB server, host ports or external network. Copies
only the approved dependency graph into synthetic shell services. Exercises the
same operation_args as deployment and records process lifecycle, not API UAT.
"""
import argparse
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
    source_root = Path(__file__).resolve().parents[2]
    source_sha = a.run(['git','-C',str(source_root),'rev-parse','HEAD']).decode().strip()
    source_dirty = bool(a.run(['git','-C',str(source_root),'status','--porcelain']))
    base_tag = project + '-image:base'
    tags = [base_tag, project + '-image:before', project + '-image:after']
    commands = []
    image_metadata = {}
    try:
        # Metadata-only builds from an already present image. No RUN, source
        # code, credentials, package installation or database startup.
        a.run(['docker','image','tag',image_id,base_tag])
        for phase,task in (('before','synthetic-hierarchy'),('after','synthetic-wo-release')):
            context = root / ('image-' + phase); context.mkdir(mode=0o700)
            (context/'Dockerfile').write_text('FROM '+base_tag+'\nLABEL org.opencontainers.image.revision="synthetic-'+phase+'"\nLABEL nadi.local.task="'+task+'"\n')
            tag = project + '-image:' + phase
            a.run(['docker','build','--network','none','--pull=false','--tag',tag,str(context)])
            image_metadata[phase] = json.loads(a.run(['docker','image','inspect',tag]))[0]
        services = {}
        for name,deps in graph.items():
            oneshot = name.endswith('-init') or name in {'mart-ready','mart-migrate','pi-migrate','mart-reader'}
            command = ('if test -f /evidence/armed; then echo '+name+' >> /evidence/forbidden; fi; exit 0') if oneshot else "trap 'exit 0' TERM; while true; do sleep 1 & wait $!; done"
            services[name] = {'image':image_metadata['before']['Id'] if name=='cockpit-api' else image_id,
                'entrypoint':['/bin/sh'],'command':['-c',command],
                'user':str(os.getuid())+':'+str(os.getgid()),'read_only':True,'network_mode':'none',
                'volumes':[str(root)+':/evidence:rw'],'tmpfs':['/var/lib/postgresql/data:rw,size=1048576'],'restart':'no',
                'labels':{'org.opencontainers.image.revision':'synthetic-before'},
                'healthcheck':{'test':['CMD','/bin/true'],'interval':'1s','timeout':'1s','retries':5}}
            if deps:services[name]['depends_on']=deps
        base=root/'compose.json';base.write_text(json.dumps({'services':services}));base.chmod(0o600)
        candidate={'services':{s:{'labels':{'org.opencontainers.image.revision':'synthetic-after'}} for s in a.SERVICES}}
        candidate['services']['cockpit-api']['image']=image_metadata['after']['Id']
        bad=root/'historical-bad-candidate.json';bad.write_text(json.dumps(candidate));bad.chmod(0o600)
        candidate['services']['cockpit-api']['labels'][a.TASK_LABEL]='synthetic-hierarchy'
        override=root/'candidate.json';override.write_text(json.dumps(candidate));override.chmod(0o600)
        prefix=['docker','compose','-p',project,'-f',str(base)]
        def snapshots():
            ids=a.run(prefix+['ps','-aq']).decode().split()
            return {r['Name']:r for r in json.loads(a.run(['docker','inspect',*ids]))}
        def operation(command, service):
            before=snapshots();started=time.time();a.run(command);commands.append(command)
            after=snapshots();name='/'+project+'-'+service+'-1'
            a.verify_preservation(before,after,{name})
            events=[json.loads(v) for v in a.run(['docker','events','--since',str(started),'--until',str(time.time()),'--filter','type=container','--format','{{json .}}']).splitlines()]
            a.verify_events(events,before,after,name,service,project)
            if (root/'forbidden').exists():raise RuntimeError('FORBIDDEN_FIXTURE_SERVICE_EXECUTED')
            return before,after,events
        pending=set(graph)
        while pending:
            ready=[s for s in pending if not (set(graph[s]) & pending)]
            if not ready:raise RuntimeError('DEPENDENCY_CYCLE')
            for service in sorted(ready):
                a.run(prefix+['up','-d','--no-deps','--no-build','--pull','never',service]);pending.remove(service)
            for _ in range(50):
                rows=snapshots()
                if all(r['State']['Status']=='exited' or r['State'].get('Health',{}).get('Status')=='healthy' for r in rows.values()):break
                time.sleep(.1)
            else:raise RuntimeError('FIXTURE_READINESS_FAILED')
        initial=snapshots();assert len(initial)==len(graph)
        (root/'armed').write_text('synthetic fixture armed; no plant data\n')
        factual='/'+project+'-cockpit-api-1'
        old_render=json.loads(a.run(prefix+['config','--format','json']))['services']['cockpit-api']
        bad_render=json.loads(a.run(prefix+['-f',str(bad),'config','--format','json']))['services']['cockpit-api']
        good_render=json.loads(a.run(prefix+['-f',str(override),'config','--format','json']))['services']['cockpit-api']
        try:
            a.verify_effective_labels(initial[factual],image_metadata['before'],image_metadata['after'],old_render,bad_render,'synthetic-after')
        except RuntimeError as error:
            if str(error)!='UNAPPROVED_EFFECTIVE_IMAGE_LABEL_CHANGE':raise
        else:raise RuntimeError('HISTORICAL_INHERITED_LABEL_WAS_NOT_REJECTED')
        a.verify_preservation(initial,snapshots(),set())
        a.verify_effective_labels(initial[factual],image_metadata['before'],image_metadata['after'],old_render,good_render,'synthetic-after')
        # Deliberately instantiate ONLY the isolated historical bad case to
        # prove the existing runtime gate rejects it, then restore the fixture.
        # This is not a deployment path around the new preflight.
        before,bad_state,_=operation(prefix+['-f',str(bad)]+a.operation_args('replace','cockpit-api'),'cockpit-api')
        expected=a.expected_runtime(initial[factual],image_metadata['after']['Id'],'synthetic-after')
        try:a.verify_runtime(bad_state[factual],expected,predecessor=before[factual])
        except RuntimeError as error:
            if str(error)!='RUNTIME_CONTRACT_CHANGED':raise
        else:raise RuntimeError('HISTORICAL_RUNTIME_LABEL_FAILURE_NOT_REPRODUCED')
        prior,restored,_=operation(prefix+a.operation_args('rollback','cockpit-api'),'cockpit-api')
        a.verify_runtime(restored[factual],initial[factual],predecessor=prior[factual])
        if not restored[factual]['State']['Running']:raise RuntimeError('HISTORICAL_FIXTURE_ROLLBACK_FAILED')
        start=time.time();positive_events=[]
        for action in ('quiesce','replace','resume','quiesce','rollback','resume'):
            targets=sorted(a.WRITERS if action in ('quiesce','resume') else a.SERVICES)
            for service in targets:
                current=snapshots();name='/'+project+'-'+service+'-1'
                use_candidate=action=='replace' or action in ('quiesce','resume') and current[name]['Config']['Labels']['org.opencontainers.image.revision']=='synthetic-after'
                cp=prefix+(['-f',str(override)] if use_candidate else [])
                before,after,events=operation(cp+a.operation_args(action,service),service);positive_events.extend(events)
                revision=before[name]['Config']['Labels']['org.opencontainers.image.revision'] if action in ('quiesce','resume') else ('synthetic-after' if action=='replace' else 'synthetic-before')
                target_image=image_metadata['after' if revision=='synthetic-after' else 'before']['Id'] if service=='cockpit-api' else image_id
                expected=a.expected_runtime(initial[name],target_image,revision)
                try:a.verify_runtime(after[name],expected,predecessor=before[name])
                except RuntimeError:
                    (root/'failed-runtime-contract.json').write_text(json.dumps({'action':action,'service':service,'expected':a.runtime_contract(expected),'actual':a.runtime_contract(after[name])},indent=2));raise
                if action in ('quiesce','resume') and before[name]['Id']!=after[name]['Id']:raise RuntimeError('FIXTURE_UNEXPECTED_RECREATION')
                if after[name]['State']['Running']!=(action=='resume' or action in ('replace','rollback') and service not in a.WRITERS):raise RuntimeError('FIXTURE_STATE_MISMATCH')
        for event in positive_events:
            if event.get('Action') in {'create','start','restart','die','destroy','stop','kill','pause','unpause','update','rename'} and event.get('Actor',{}).get('Attributes',{}).get('com.docker.compose.service') not in a.SERVICES:raise RuntimeError('FORBIDDEN_LIFECYCLE_EVENT')
        positive={'tested_source_sha':source_sha,'tested_source_dirty':source_dirty,
          'activation_module_sha256':hashlib.sha256(Path(a.__file__).read_bytes()).hexdigest(),'graph_sha256':a.digest(graph),'compose_version':a.run(['docker','compose','version','--short']).decode().strip(),'gate':'PASS','fixture_roles':len(initial),'exact_operation_builder':True,
          'commands':commands,'maximo_init_untouched':a.digest(a.preserved(initial['/'+project+'-maximo-init-1']))==a.digest(a.preserved(snapshots()['/'+project+'-maximo-init-1'])),
          'forbidden_marker_absent':not (root/'forbidden').exists(),'lifecycle_events':positive_events,
          'inherited_label_preflight_rejection':'PASS','historical_runtime_label_failure_reproduced':'PASS','historical_bad_fixture_rollback':'PASS','explicit_original_task_label_activation_and_rollback':'PASS',
          'corrected_sequence_seconds':round(time.time()-start,3),
          'fixture_image_labels':{k:v['Config']['Labels'] for k,v in image_metadata.items()},
          'network':'none','application_or_source_credentials':False,'host_ports':False,'database_server_started':False}
        # Separately reproduce the original dependency-start hazard in this
        # armed dummy project only, after the corrected sequence has passed.
        a.run(prefix+a.operation_args('quiesce','maximo-worker'))
        old_before=snapshots();a.run(prefix+['start','maximo-worker']);old_after=snapshots()
        hazard=old_before['/'+project+'-maximo-init-1']['State']['StartedAt']!=old_after['/'+project+'-maximo-init-1']['State']['StartedAt']
        positive['old_compose_start_dependency_reproduced']=hazard
        positive['old_command_forbidden_marker']=(root/'forbidden').exists()
        if not hazard or not positive['old_command_forbidden_marker']:raise RuntimeError('ORIGINAL_CAUSE_NOT_REPRODUCED')
        (root/'result.json').write_text(json.dumps(positive,indent=2));(root/'result.json').chmod(0o600)
        return positive
    finally:
        ids=a.run(['docker','ps','-aq','--filter','label=com.docker.compose.project='+project]).decode().split()
        if ids:a.run(['docker','rm','-f','-v',*ids])
        for tag in reversed(tags):
            if subprocess.run(['docker','image','inspect',tag],capture_output=True).returncode==0:
                a.run(['docker','image','rm',tag])
        a.verify_preservation(live_before,a.inventory(),set())


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--image',required=True)
    parser.add_argument('--graph',required=True);parser.add_argument('--directory',required=True)
    args=parser.parse_args();result=rehearse(args.image,json.loads(Path(args.graph).read_text()),args.directory)
    print(json.dumps({k:result[k] for k in ('gate','fixture_roles','maximo_init_untouched','forbidden_marker_absent','old_compose_start_dependency_reproduced')}))
