"""One exact reviewed PR119 -> hierarchy development release; no lifecycle/write API.

The installed controller manifest pins the owner-private admission bytes. Default
source equality is retained; only a separately reviewed exact candidate/recovery
tuple can use this closed exception. This module never issues a grant.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
from datetime import datetime, timezone, timedelta

BASE_SHA = '119ba2f1472facedd71433d65b74f3b7d64a6434'
FIELDS = {'version','purpose','prior_sha','recovery_sha','candidate_sha','candidate_tree',
          'objects','changed_files','factual_approval_sha256','subject','engineering_asset_ids',
          'owner_decision_ref','review_ref'}
ALLOWED_DELTA = {
    'reliability-cockpit/src/api/reliability.py',
    'reliability-cockpit/src/qa/factual_reads.py',
    'reliability-cockpit/src/services/asset_hierarchy.py',
    'reliability-cockpit/src/services/factual_read_entitlements.py',
    'reliability-cockpit/src/services/registered_maintenance_overview.py',
    'reliability-cockpit/web/lib/api.ts',
    'reliability-data-contracts/mappings/maximo-to-contracts.md',
}
PERSISTENCE = (
    'reliability-cockpit/application-migrations','reliability-cockpit/src/repositories',
    'reliability-cockpit/src/services/local_authentication.py',
    'reliability-cockpit/src/services/application_identity.py',
    'reliability-cockpit/src/api/engineering_qa.py','reliability-cockpit/pyproject.toml',
    'reliability-cockpit/tests/qa','reliability-cockpit/tests/test_condition_evidence.py',
    'reliability-cockpit/tests/test_asset_af_mapping_admin.py','pi-collector/tests/fixtures/condition_source.py',
)
CAPABILITIES = {'FACTUAL_ASSET_READ','FACTUAL_DASHBOARD_READ','FACTUAL_HIERARCHY_READ','FACTUAL_MAINTENANCE_READ'}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def private_bytes(path, maximum=4*1024*1024, *, mode=0o600):
    path=Path(path)
    parent=path.parent.lstat()
    if (path.parent.resolve()!=path.parent or not stat.S_ISDIR(parent.st_mode)
            or parent.st_uid!=os.getuid() or stat.S_IMODE(parent.st_mode)!=0o700):
        raise RuntimeError('PRIVATE_ADMISSION_DIRECTORY_REQUIRED')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as stream:
        s=os.fstat(stream.fileno())
        if (not stat.S_ISREG(s.st_mode) or s.st_uid!=os.getuid() or s.st_nlink!=1
                or stat.S_IMODE(s.st_mode)!=mode or s.st_size>maximum):
            raise RuntimeError('PRIVATE_ADMISSION_FILE_REQUIRED')
        data=stream.read(maximum+1)
        if len(data)>maximum:raise RuntimeError('ADMISSION_SIZE_LIMIT')
    return data


def git(root,*args):
    return subprocess.check_output(['git',*args],cwd=root,text=True,timeout=20).strip()


def decode(data):
    value=json.loads(data)
    if (not isinstance(value,dict) or set(value)!=FIELDS or data!=(canonical(value)+'\n').encode()
            or type(value['version']) is not int or value['version']!=1
            or value['purpose']!='NADI_HIERARCHY_LOCAL_RELEASE_01' or value['prior_sha']!=BASE_SHA):
        raise RuntimeError('EXACT_SOURCE_ADMISSION_REQUIRED')
    for key in ['recovery_sha','candidate_sha','candidate_tree']:
        if not isinstance(value[key],str) or not re.fullmatch('[a-f0-9]{40}',value[key]):
            raise RuntimeError('EXACT_SOURCE_ADMISSION_REQUIRED')
    if not re.fullmatch('[a-f0-9]{64}',value['factual_approval_sha256']):
        raise RuntimeError('EXACT_FACTUAL_APPROVAL_PIN_REQUIRED')
    if not re.fullmatch('local:[A-Za-z0-9-]{1,150}',value['subject']):
        raise RuntimeError('EXACT_ENGINEER_SUBJECT_REQUIRED')
    if (not isinstance(value['engineering_asset_ids'],list)
            or value['engineering_asset_ids']!=sorted(set(value['engineering_asset_ids']))
            or any(not isinstance(x,str) or not re.fullmatch('[A-Za-z0-9_.:-]{1,200}',x) for x in value['engineering_asset_ids'])):
        raise RuntimeError('EXISTING_ENGINEERING_SCOPE_REQUIRED')
    for key in ['owner_decision_ref','review_ref']:
        if not isinstance(value[key],str) or not re.fullmatch('[A-Za-z0-9_.:-]{1,160}',value[key]):
            raise RuntimeError('REVIEWED_OWNER_ADMISSION_REQUIRED')
    if not isinstance(value['objects'],dict) or not isinstance(value['changed_files'],dict):
        raise RuntimeError('ADMISSION_SOURCE_INVENTORY_REQUIRED')
    if set(value['changed_files'])!=ALLOWED_DELTA:
        raise RuntimeError('CLOSED_SOURCE_DELTA_REQUIRED')
    for mapping in [value['objects'],value['changed_files']]:
        for path,pair in mapping.items():
            if (not isinstance(path,str) or path.startswith('/') or '..' in path.split('/')
                    or not isinstance(pair,list) or len(pair)!=2
                    or any(not isinstance(x,str) or not re.fullmatch('[a-f0-9]{40}|ABSENT',x) for x in pair)):
                raise RuntimeError('ADMISSION_SOURCE_INVENTORY_REQUIRED')
    return value


def approved(control):
    record=json.loads(private_bytes(control.STATE/'local-development-release.json'))
    pin=record.get('hierarchy_release',{})
    if set(pin)!={'admission_file','admission_sha256','module_sha256'}:
        raise RuntimeError('INSTALLED_EXACT_SOURCE_ADMISSION_REQUIRED')
    p=Path(pin['admission_file'])
    if p.parent!=control.STATE/'source-admissions':
        raise RuntimeError('FIXED_SOURCE_ADMISSION_LOCATION_REQUIRED')
    if pin['module_sha256']!=sha(Path(__file__).read_bytes()):
        raise RuntimeError('SOURCE_ADMISSION_MODULE_CHANGED')
    data=private_bytes(p)
    if sha(data)!=pin['admission_sha256']:
        raise RuntimeError('SOURCE_ADMISSION_APPROVAL_CHANGED')
    return decode(data)


def object_id(root,revision,path):
    result=subprocess.run(['git','rev-parse','--verify',revision+':'+path],cwd=root,capture_output=True,text=True,timeout=20)
    return result.stdout.strip() if result.returncode==0 else 'ABSENT'


def compatible(control, comparator, front, recovery, candidate_sha, recovery_sha):
    value=approved(control)
    if git(front,'rev-parse','HEAD')!=candidate_sha or git(recovery,'rev-parse','HEAD')!=recovery_sha:
        raise RuntimeError('SOURCE_ADMISSION_REVISION_MISMATCH')
    if (candidate_sha,recovery_sha)!=(value['candidate_sha'],value['recovery_sha']):
        # Keep every historical exact-equality check. This branch grants no source
        # difference exception; the original conservative comparator owns it.
        return comparator.compatible(front,recovery,candidate_sha,recovery_sha)
    if git(front,'rev-parse',candidate_sha+'^{tree}')!=value['candidate_tree']:
        raise RuntimeError('SOURCE_ADMISSION_REVISION_MISMATCH')
    paths=comparator.COMPATIBILITY_PATHS
    if set(value['objects'])!=set(paths):raise RuntimeError('SOURCE_ADMISSION_PATH_SET_CHANGED')
    actual={p:[object_id(recovery,recovery_sha,p),object_id(front,candidate_sha,p)] for p in paths}
    if actual!=value['objects'] or any(pair[0]!=object_id(front,BASE_SHA,p) for p,pair in actual.items()):
        raise RuntimeError('SOURCE_ADMISSION_OBJECT_MISMATCH')
    for p in PERSISTENCE:
        if object_id(recovery,recovery_sha,p)!=object_id(front,candidate_sha,p):
            raise RuntimeError('SOURCE_ADMISSION_PERSISTENCE_CHANGE_DENIED')
    changed=git(front,'diff','--name-only',BASE_SHA,candidate_sha,'--',*paths).splitlines()
    if set(changed)!=ALLOWED_DELTA:raise RuntimeError('SOURCE_ADMISSION_UNREVIEWED_DELTA')
    leaves={p:[object_id(recovery,recovery_sha,p),object_id(front,candidate_sha,p)] for p in changed}
    if leaves!=value['changed_files']:raise RuntimeError('SOURCE_ADMISSION_LEAF_MISMATCH')
    # Keep the old comparator's dependency checks; no dependency exception exists.
    a=json.loads(git(front,'show',candidate_sha+':reliability-cockpit/web/package.json'))
    b=json.loads(git(recovery,'show',recovery_sha+':reliability-cockpit/web/package.json'))
    for key in ['dependencies','devDependencies','engines','overrides']:
        if a.get(key)!=b.get(key):raise RuntimeError('FRONTEND_DEPENDENCY_DIFFERENCE')
    for root,revision in [(front,candidate_sha),(recovery,recovery_sha)]:
        if git(root,'diff','--name-only',revision,'--',*paths) or git(root,'ls-files','--others','--exclude-standard','--',*paths):
            raise RuntimeError('SOURCE_ADMISSION_WORKTREE_DRIFT')
    return sha(canonical({'admission':value,'objects':actual}).encode())


def factual_environment(control, selected):
    value=approved(control)
    if selected['sha']!=value['candidate_sha']:return []  # Historical rollback leaves READ state untouched.
    root=Path(selected['root'])
    if git(root,'rev-parse','HEAD')!=value['candidate_sha']:
        raise RuntimeError('EXACT_FACTUAL_SOURCE_REQUIRED')
    path=control.STATE/'factual-read-120'/'activation-approval.json'
    data=private_bytes(path)
    if sha(data)!=value['factual_approval_sha256']:
        raise RuntimeError('EXACT_FACTUAL_APPROVAL_CHANGED')
    spec=importlib.util.spec_from_file_location('hierarchy_reviewed_read_schema',root/'reliability-cockpit/src/services/factual_read_entitlements.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    approval=json.loads(data)
    fields={'schema_version','expected_head','action','grant_id','subject','assets','capabilities','not_before','expires_at','actor','approval_ref','operator_ref','scope_kind'}
    if (set(approval)!=fields or data!=(module.canonical(approval)+'\n').encode()
            or type(approval['schema_version']) is not int or approval['schema_version']!=1
            or approval['action']!='ISSUE' or approval['scope_kind']!='EXACT_ASSETS'
            or approval['subject']!=value['subject'] or set(approval['capabilities'])!=CAPABILITIES
            or len(approval['assets'])!=1 or approval['actor']!=module.ISSUER
            or approval['approval_ref']!=value['owner_decision_ref']):
        raise RuntimeError('EXACT_HIERARCHY_FACTUAL_APPROVAL_REQUIRED')
    policy=path.with_name('grants.ndjson');events=module.decode(private_bytes(policy))
    event=next((e for e in reversed(events) if e['grant_id']==approval['grant_id']),None)
    now=datetime.now(timezone.utc)
    if (not event or event['action']!='ISSUE' or event['previous_sha256']!=approval['expected_head']
            or any(event[k]!=approval[k] for k in fields-{'schema_version','expected_head'})
            or not module.timestamp(event['not_before'])<=now<module.timestamp(event['expires_at'])
            or any(module.timestamp(e['at'])>now+timedelta(seconds=5) for e in events)):
        raise RuntimeError('ACTIVE_EXACT_HIERARCHY_GRANT_REQUIRED')
    return ['NADI_FACTUAL_READ_POLICY_FILE='+str(policy)]


def engineer_session(control, manager, selected, session_file):
    value=approved(control)
    if selected['sha']!=value['candidate_sha']:return
    if not session_file:raise RuntimeError('EXACT_ENGINEER_SESSION_REQUIRED')
    proof=json.loads(private_bytes(Path(session_file),4096))
    if set(proof)!={'cookie'}:raise RuntimeError('PRIVATE_SESSION_FILE_INVALID')
    result=manager.probe(control.ORIGIN+'/api/engineering-qa/session',proof['cookie'])
    who=result.get('data')
    if (result['status']!=200 or not isinstance(who,dict) or who.get('subject')!=value['subject']
            or who.get('roles')!=['AUTHOR'] or sorted(who.get('asset_ids',[]))!=value['engineering_asset_ids']):
        raise RuntimeError('EXACT_ENGINEER_AUTHOR_SESSION_REQUIRED')
