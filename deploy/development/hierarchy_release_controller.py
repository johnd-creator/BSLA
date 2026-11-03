"""Prepare one exact amendment to the accepted local controller; apply is explicit.

No source switch, service restart, DB write, account or grant administration.
All five accepted controller files are hash-bound. Only local_development gains
the closed admission and READ environment hooks; historical bridge/demo checks stay.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import uuid
import fcntl

BASELINE_FILES = {
    'nadi-dev.py':'e0d42099edb376eea01155d15ce1595f3e55dc237e42c024e589abda1d0c997f',
    'local_development.py':'46dd4423d292d16ab047a28f01c8cc00956fb3085f66ee949be49a9d6fa4b8c8',
    'local_fixture.py':'5b1deaae81544fcfa689f1a4d093ef164863876eb9c12de5bb3acd7e96582193',
    'frontend_preview.py':'285378069e2759cc60b4ac246694ac239f19173bee099e4584782b6bfeb136b3',
    'pdm_007_bridge.py':'cf750bca56495c110d4d34cfc323bdd867b28fdc55a786d3fc4f8ab0b78eb899',
}
HERE=Path(__file__).resolve().parent


def module(path):
    spec=importlib.util.spec_from_file_location('reviewed_hierarchy_'+uuid.uuid4().hex,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


def sha(data):return hashlib.sha256(data).hexdigest()


def write(path,data,mode=0o600):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode)
    with os.fdopen(fd,'wb') as f:f.write(data)


def replace(path,data,mode=0o600):
    temp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp');write(temp,data,mode);os.replace(temp,path)


def activate_metadata(wrapper,manifest,oldw,oldm,neww,newm,read,verify):
    """Only our metadata bytes may be recovered; executable wrapper stays0700."""
    try:
        replace(manifest,newm);replace(wrapper,neww,0o700)
        return verify()
    except BaseException:
        actualw=read(wrapper,mode=0o700);actualm=read(manifest)
        if actualw not in (oldw,neww) or actualm not in (oldm,newm):
            raise RuntimeError('CONTROLLER_RECOVERY_CONCURRENT_CHANGE') from None
        if actualw!=oldw:replace(wrapper,oldw,0o700)
        if actualm!=oldm:replace(manifest,oldm)
        raise


def amend(source):
    """Each exact anchor occurs once; no fuzzy patch or deleted historical gate."""
    replacements=[
      ("{'nadi-dev.py','local_development.py','local_fixture.py','frontend_preview.py','pdm_007_bridge.py'}",
       "{'nadi-dev.py','local_development.py','local_fixture.py','frontend_preview.py','pdm_007_bridge.py','hierarchy_source_admission.py'}"),
      ("        self._release_record=record\n", "        self.hierarchy_module().approved(self.c)\n        self._release_record=record\n"),
      ("        root, sha = self.resolve(root,ref)\n        if self.c.active(self.c.LEGACY_WEB):",
       "        root, sha = self.resolve(root,ref)\n        self.hierarchy_module().factual_environment(self.c,{'root':str(root),'sha':sha})\n        if self.c.active(self.c.LEGACY_WEB):"),
      ("            module.compatible(root,Path(previous['root']),sha,previous['sha'])",
       "            self.hierarchy_module().compatible(self.c,module,root,Path(previous['root']),sha,previous['sha'])"),
      ("        root=Path(value['root']);web=root/'reliability-cockpit/web'\n        self.start(",
       "        root=Path(value['root']);web=root/'reliability-cockpit/web'\n        factual_extra=self.hierarchy_module().factual_environment(self.c,value)\n        self.start("),
      ("'COCKPIT_API_BASE=http://127.0.0.1:8000','NADI_DEV_LAUNCHED_SHA='+value['sha']], '6G')",
       "'COCKPIT_API_BASE=http://127.0.0.1:8000','NADI_DEV_LAUNCHED_SHA='+value['sha'],*factual_extra], '6G')"),
      ("        data['authentication']=self.auth_readiness(session_file)\n",
       "        data['authentication']=self.auth_readiness(session_file)\n        if session_file:self.hierarchy_module().engineer_session(self.c,self,value,session_file)\n"),
      ("        value = self.preflight(root,ref)\n        if self.preservation:",
       "        value = self.preflight(root,ref)\n        self.hierarchy_module().engineer_session(self.c,self,value,self.acceptance_session_file)\n        if self.preservation:"),
    ]
    result=source
    for old,new in replacements:
        if result.count(old)!=1:raise RuntimeError('EXACT_CONTROLLER_AMENDMENT_ANCHOR_CHANGED')
        result=result.replace(old,new,1)
    anchor='    def release(self):\n'
    if result.count(anchor)!=1:raise RuntimeError('EXACT_CONTROLLER_AMENDMENT_ANCHOR_CHANGED')
    loader='''    def hierarchy_module(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location('reviewed_hierarchy_source_admission',Path(__file__).with_name('hierarchy_source_admission.py'))
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        return module

'''
    result=result.replace(anchor,loader+anchor,1)
    compile(result,'reviewed_local_development.py','exec')
    return result


def baseline(repository, admission):
    state=Path(repository).resolve()/'.nadi-dev/state';read=admission.private_bytes
    wrapper=state.parent/'nadi-dev';manifest=state/'local-development-release.json';active=state/'local-dev-01/active.json'
    raww,rawm,rawa=read(wrapper,mode=0o700),read(manifest),read(active)
    record=json.loads(rawm);value=json.loads(rawa)
    words=shlex.split(raww.decode().splitlines()[1]);old=Path(words[2])
    if (raww.decode().splitlines()[0]!='#!/bin/sh' or len(raww.decode().splitlines())!=2
            or words!=['exec','/usr/bin/python3',str(old),'$@'] or old.name!='nadi-dev.py'
            or old.parent.parent!=state/'controller-releases' or record['files']!=BASELINE_FILES
            or record['source_sha']!='1ec93d6f3507321617903d169451d77fdcc1216e'
            or record['installation_binding']['ROOT']!=str(state.parent/'worktree')
            or value['sha']!=admission.BASE_SHA):
        raise RuntimeError('EXACT_ACCEPTED_CONTROLLER_BASELINE_REQUIRED')
    blobs={n:read(old.parent/n) for n in BASELINE_FILES}
    if {n:sha(b) for n,b in blobs.items()}!=BASELINE_FILES:
        raise RuntimeError('ACCEPTED_CONTROLLER_SOURCE_CHANGED')
    return state,raww,rawm,rawa,record,value,old,blobs


def prepare(repository,candidate_root,admission_path,destination):
    helper=module(HERE/'hierarchy_source_admission.py')
    data=helper.private_bytes(admission_path);approval=helper.decode(data)
    state,raww,rawm,rawa,record,value,old,blobs=baseline(repository,helper)
    root=Path(candidate_root).resolve();candidate=approval['candidate_sha']
    if (helper.git(root,'rev-parse','HEAD')!=candidate or helper.git(root,'status','--porcelain')
            or helper.git(root,'remote','get-url','origin') not in {
                'https://github.com/johnd-creator/reliability-knowledge-starter.git',
                'git@github.com:johnd-creator/reliability-knowledge-starter.git'}):
        raise RuntimeError('CLEAN_EXACT_RELEASE_CANDIDATE_REQUIRED')
    source_helper=subprocess.check_output(['git','show',candidate+':deploy/development/hierarchy_source_admission.py'],cwd=root)
    source_installer=subprocess.check_output(['git','show',candidate+':deploy/development/hierarchy_release_controller.py'],cwd=root)
    if source_helper!=(HERE/'hierarchy_source_admission.py').read_bytes() or source_installer!=Path(__file__).read_bytes():
        raise RuntimeError('REVIEWED_CONTROLLER_SOURCE_REQUIRED')
    blobs['local_development.py']=amend(blobs['local_development.py'].decode()).encode()
    blobs['hierarchy_source_admission.py']=source_helper
    target=Path(destination);target.mkdir(mode=0o700)
    if target.resolve()!=target:raise RuntimeError('PRIVATE_PREPARATION_ROOT_REQUIRED')
    for name,body in blobs.items():write(target/name,body)
    write(target/'admission.private.json',data)
    pin_path=state/'source-admissions'/('hierarchy-'+candidate[:12]+'-'+sha(data)[:12]+'.json')
    newrecord=dict(record,files={n:sha(b) for n,b in blobs.items()},hierarchy_release={
        'admission_file':str(pin_path),'admission_sha256':sha(data),'module_sha256':sha(source_helper)})
    write(target/'manifest.private.json',(json.dumps(newrecord,indent=2)+'\n').encode())
    prepared={'version':1,'status':'PREPARED_NOT_INSTALLED','candidate_root':str(root),'candidate_sha':candidate,
              'expected_wrapper_sha256':sha(raww),'expected_manifest_sha256':sha(rawm),'expected_active_sha256':sha(rawa),
              'files':{n:sha(b) for n,b in blobs.items()},'manifest_sha256':sha((target/'manifest.private.json').read_bytes()),
              'admission_sha256':sha(data),'installer_sha256':sha(Path(__file__).read_bytes()),
              'owner_decision_ref':approval['owner_decision_ref'],'review_ref':approval['review_ref']}
    write(target/'prepared.private.json',(helper.canonical(prepared)+'\n').encode())
    return {'status':'PREPARED_NOT_INSTALLED','candidate_sha':candidate,'controller_files_changed':1,'controller_files_added':1,
            'prepared_sha256':sha((target/'prepared.private.json').read_bytes()),'services_restarted':False}


def install(repository,prepared_path,owner_path,owner_digest):
    helper=module(HERE/'hierarchy_source_admission.py');read=helper.private_bytes
    prepared_path=Path(prepared_path);stage=prepared_path.parent
    rawp=read(prepared_path);p=json.loads(rawp);rawo=read(owner_path)
    if sha(rawo)!=owner_digest:raise RuntimeError('OWNER_INSTALL_APPROVAL_CHANGED')
    owner=json.loads(rawo)
    fields={'version','verdict','prepared_sha256','candidate_sha','files','installer_sha256','owner_decision_ref','review_ref'}
    if (set(owner)!=fields or rawo!=(helper.canonical(owner)+'\n').encode() or owner['version']!=1 or owner['verdict']!='GO'
            or owner['prepared_sha256']!=sha(rawp) or any(owner[k]!=p[k] for k in fields-{'version','verdict','prepared_sha256'})
            or sha(Path(__file__).read_bytes())!=p['installer_sha256'] or p['status']!='PREPARED_NOT_INSTALLED'
            or p['files'].keys()!=set(BASELINE_FILES)|{'hierarchy_source_admission.py'}):
        raise RuntimeError('EXACT_REVIEWED_OWNER_INSTALL_APPROVAL_REQUIRED')
    state,oldw,oldm,olda,record,value,old,base=baseline(repository,helper)
    if any(sha(data)!=p[key] for data,key in [(oldw,'expected_wrapper_sha256'),(oldm,'expected_manifest_sha256'),(olda,'expected_active_sha256')]):
        raise RuntimeError('CONTROLLER_INSTALL_BASELINE_CHANGED')
    if helper.git(p['candidate_root'],'rev-parse','HEAD')!=p['candidate_sha'] or helper.git(p['candidate_root'],'status','--porcelain'):
        raise RuntimeError('CANDIDATE_SOURCE_CHANGED')
    blobs={n:read(stage/n) for n in p['files']}
    if ({n:sha(b) for n,b in blobs.items()}!=p['files'] or sha(read(stage/'manifest.private.json'))!=p['manifest_sha256']
            or sha(read(stage/'admission.private.json'))!=p['admission_sha256']):
        raise RuntimeError('PREPARED_CONTROLLER_BYTES_CHANGED')
    if blobs['local_development.py']!=amend(base['local_development.py'].decode()).encode():
        raise RuntimeError('EXACT_CONTROLLER_DELTA_REQUIRED')
    for n in BASELINE_FILES.keys()-{'local_development.py'}:
        if blobs[n]!=base[n]:raise RuntimeError('HISTORICAL_CONTROLLER_GATE_CHANGED')
    newm=read(stage/'manifest.private.json');newrecord=json.loads(newm)
    expected_pin={'admission_file':str(state/'source-admissions'/('hierarchy-'+p['candidate_sha'][:12]+'-'+p['admission_sha256'][:12]+'.json')),
                  'admission_sha256':p['admission_sha256'],'module_sha256':p['files']['hierarchy_source_admission.py']}
    if newrecord!=dict(record,files=p['files'],hierarchy_release=expected_pin):
        raise RuntimeError('PREPARED_CONTROLLER_MANIFEST_CHANGED')
    if (blobs['hierarchy_source_admission.py']!=subprocess.check_output(['git','show',p['candidate_sha']+':deploy/development/hierarchy_source_admission.py'],cwd=p['candidate_root'])
            or Path(__file__).read_bytes()!=subprocess.check_output(['git','show',p['candidate_sha']+':deploy/development/hierarchy_release_controller.py'],cwd=p['candidate_root'])):
        raise RuntimeError('REVIEWED_CONTROLLER_SOURCE_REQUIRED')
    ident='hierarchy-release-'+p['candidate_sha'][:12]+'-'+uuid.uuid4().hex[:8]
    release=state/'controller-releases'/ident;release.mkdir(mode=0o700)
    for n,b in blobs.items():write(release/n,b)
    admit=Path(newrecord['hierarchy_release']['admission_file'])
    if admit.parent!=state/'source-admissions':raise RuntimeError('FIXED_SOURCE_ADMISSION_LOCATION_REQUIRED')
    admit.parent.mkdir(mode=0o700,exist_ok=True)
    if admit.exists():
        if read(admit)!=read(stage/'admission.private.json'):raise RuntimeError('EXISTING_ADMISSION_CONFLICT')
    else:write(admit,read(stage/'admission.private.json'))
    # Real process/TLS/fixture checks against temporary metadata. No runtime pointer change.
    with tempfile.TemporaryDirectory(prefix='nadi-hierarchy-controller-') as td:
        t=Path(td);t.chmod(0o700);(t/'local-dev-01').mkdir(mode=0o700);(t/'source-admissions').mkdir(mode=0o700)
        write(t/'source-admissions/admission.json',read(admit))
        staged=dict(newrecord,hierarchy_release=dict(newrecord['hierarchy_release'],admission_file=str(t/'source-admissions/admission.json')))
        write(t/'local-development-release.json',json.dumps(staged).encode());write(t/'local-dev-01/active.json',olda)
        write(t/'localhost.pem',read(state/'localhost.pem'));(t/'python-runtime').symlink_to(state/'python-runtime',target_is_directory=True)
        c=module(release/'nadi-dev.py');c.STATE=t;manager=c.local_controller()
        if manager.status()['transport_process_readiness']!='VERIFIED':raise RuntimeError('STAGED_CONTROLLER_READINESS_FAILED')
    old_control=module(old);old_manager=old_control.local_controller();old_manager.status()
    current=module(release/'nadi-dev.py');manager=current.local_controller()
    wrapper=state.parent/'nadi-dev';manifest=state/'local-development-release.json';active=state/'local-dev-01/active.json'
    neww=('#!/bin/sh\nexec /usr/bin/python3 '+shlex.quote(str(release/'nadi-dev.py'))+' "$@"\n').encode()
    lock=os.open(state/'frontend-lifecycle.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        with manager.transaction():
            if read(wrapper,mode=0o700)!=oldw or read(manifest)!=oldm or read(active)!=olda:raise RuntimeError('CONCURRENT_CONTROLLER_CHANGE')
            before={u:old_manager.unit(u) for u in current.UNITS}
            for n,b in [('manifest-before.private.json',oldm),('wrapper-before.private.sh',oldw),('active-before.private.json',olda)]:
                write(manager.state/(ident+'-'+n),b)
            def verify():
                result=manager.status()
                if (result['transport_process_readiness']!='VERIFIED' or read(active)!=olda
                        or any(manager.unit(u)!=old for u,old in before.items())):
                    raise RuntimeError('CONTROLLER_INSTALL_CHANGED_RUNTIME')
                return result
            activate_metadata(wrapper,manifest,oldw,oldm,neww,newm,read,verify)
            outcome={'status':'INSTALLED','candidate_sha':p['candidate_sha'],'services_restarted':False,
                     'active_state_bytes_unchanged':True,'files':p['files'],'admission_sha256':p['admission_sha256']}
            write(manager.state/(ident+'-installed.private.json'),json.dumps(outcome,indent=2).encode())
            return outcome
    finally:os.close(lock)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repository',required=True);p.add_argument('--candidate-root');p.add_argument('--admission-file');p.add_argument('--destination')
    p.add_argument('--apply',action='store_true');p.add_argument('--prepared-file');p.add_argument('--owner-approval-file');p.add_argument('--owner-approval-sha256')
    a=p.parse_args()
    if a.apply:
        if not all([a.prepared_file,a.owner_approval_file,a.owner_approval_sha256]):p.error('exact prepared and owner approval required')
        result=install(a.repository,a.prepared_file,a.owner_approval_file,a.owner_approval_sha256)
    else:
        if not all([a.candidate_root,a.admission_file,a.destination]):p.error('preparation inputs required')
        result=prepare(a.repository,a.candidate_root,a.admission_file,a.destination)
    print(json.dumps(result))


if __name__=='__main__':main()
