"""Prepare/install an exact local WO controller amendment. Preparation is default.

Installation needs a separately recorded owner GO for the prepared digest. Neither
mode starts services, issues grants, switches source or mutates application data.
"""
import argparse
from contextlib import contextmanager
import copy
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shlex
import stat
import uuid

BASELINE_FILES={
 'nadi-dev.py':'e0d42099edb376eea01155d15ce1595f3e55dc237e42c024e589abda1d0c997f',
 'local_development.py':'62681724d6105b8c3a9c7122915881558b9ca58c9338104a17352d3a4f245249',
 'local_fixture.py':'5b1deaae81544fcfa689f1a4d093ef164863876eb9c12de5bb3acd7e96582193',
 'frontend_preview.py':'285378069e2759cc60b4ac246694ac239f19173bee099e4584782b6bfeb136b3',
 'pdm_007_bridge.py':'cf750bca56495c110d4d34cfc323bdd867b28fdc55a786d3fc4f8ab0b78eb899',
 'hierarchy_source_admission.py':'83b61096fc2b3cf0a79c07643532cd00b4d761411e0b1a7a8d0ffdf543520dd0',
}
HERE=Path(__file__).resolve().parent

def module(path):
 spec=importlib.util.spec_from_file_location('reviewed_wo_'+uuid.uuid4().hex,path)
 value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value

def digest(data):return hashlib.sha256(data).hexdigest()
def encoded(value):return (json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode()

def write(path,data,mode=0o600):
 fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode)
 with os.fdopen(fd,'wb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
 directory=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(directory)
 finally:os.close(directory)

def replace(path,data,mode=0o600):
 temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp');write(temporary,data,mode);os.replace(temporary,path)
 directory=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(directory)
 finally:os.close(directory)

def amend(source):
 replacements=[
  ("{'nadi-dev.py','local_development.py','local_fixture.py','frontend_preview.py','pdm_007_bridge.py','hierarchy_source_admission.py'}",
   "{'nadi-dev.py','local_development.py','local_fixture.py','frontend_preview.py','pdm_007_bridge.py','hierarchy_source_admission.py','wo_integrated_source_admission.py'}"),
  ("spec_from_file_location('reviewed_hierarchy_source_admission',Path(__file__).with_name('hierarchy_source_admission.py'))",
   "spec_from_file_location('reviewed_hierarchy_source_admission',Path(__file__).with_name('wo_integrated_source_admission.py'))"),
  ('    def fixture_contract(self, previous, root, sha):\n',
   '    def fixture_contract(self, previous, root, sha):\n        exact=self.hierarchy_module().fixture_contract(self.c,self,previous,root,sha)\n        if exact is not None:return exact\n'),
 ]
 for old,new in replacements:
  if source.count(old)!=1:raise RuntimeError('EXACT_WO_CONTROLLER_ANCHOR_CHANGED')
  source=source.replace(old,new,1)
 compile(source,'reviewed_wo_controller','exec');return source

def _state(repository):
 repository=Path(repository).resolve();state=repository/'.nadi-dev/state'
 if repository.is_symlink() or state.resolve()!=state or stat.S_IMODE(state.stat().st_mode)!=0o700 or state.stat().st_uid!=os.getuid():raise RuntimeError('PRIVATE_EXISTING_CONTROLLER_STATE_REQUIRED')
 return state

def prepare(repository,admission_path,destination):
 state=_state(repository);reader=module(HERE/'hierarchy_source_admission.py').private_bytes
 wrapper=state.parent/'nadi-dev';old_wrapper=reader(wrapper,mode=0o700)
 words=shlex.split(old_wrapper.decode().splitlines()[1])
 if len(words)!=4 or words[:2]!=['exec','/usr/bin/python3'] or words[3]!='$@':raise RuntimeError('EXACT_CONTROLLER_WRAPPER_REQUIRED')
 old_root=Path(words[2]).parent
 if old_root.parent!=state/'controller-releases':raise RuntimeError('OWNED_CONTROLLER_RELEASE_REQUIRED')
 old_manifest=reader(state/'local-development-release.json');record=json.loads(old_manifest)
 if record['files']!=BASELINE_FILES:raise RuntimeError('ACCEPTED_CONTROLLER_BASELINE_CHANGED')
 source={name:reader(old_root/name) for name in BASELINE_FILES}
 if any(digest(raw)!=BASELINE_FILES[name] for name,raw in source.items()):raise RuntimeError('CONTROLLER_BASELINE_BYTES_CHANGED')
 raw=reader(Path(admission_path));admission_module=module(HERE/'wo_integrated_source_admission.py');admission=admission_module.decode(raw)
 admission_module.validate_issuer_contract(admission,module(HERE.parents[1]/'reliability-cockpit/src/services/factual_read_entitlements.py'))
 dest=Path(destination)
 if not dest.is_absolute() or dest.resolve()!=dest or dest.exists():raise RuntimeError('NEW_PRIVATE_PREPARED_DIRECTORY_REQUIRED')
 dest.mkdir(mode=0o700)
 source['local_development.py']=amend(source['local_development.py'].decode()).encode()
 source['wo_integrated_source_admission.py']=(HERE/'wo_integrated_source_admission.py').read_bytes()
 files={name:digest(data) for name,data in source.items()}
 future=state/'controller-releases'/('wo-integrated-'+admission['candidate_sha'][:12]+'-'+digest(raw+source['local_development.py'].strip())[:12])
 target=state/'source-admissions'/('wo-integrated-'+admission['candidate_sha'][:12]+'-'+digest(raw)[:12]+'.json')
 manifest=copy.deepcopy(record);manifest['files']=files
 manifest['wo_integrated_release']={'admission_file':str(target),'admission_sha256':digest(raw),'module_sha256':files['wo_integrated_source_admission.py']}
 new_manifest=encoded(manifest);new_wrapper=('#!/bin/sh\nexec /usr/bin/python3 '+shlex.quote(str(future/'nadi-dev.py'))+' "$@"\n').encode()
 for name,data in source.items():write(dest/name,data)
 for name,data in [('admission.private.json',raw),('manifest.private.json',new_manifest),('wrapper.private.sh',new_wrapper),('manifest-before.private.json',old_manifest),('wrapper-before.private.sh',old_wrapper)]:write(dest/name,data)
 prepared={'version':1,'purpose':'NADI_WO_INTEGRATED_LOCAL_RELEASE_01','candidate_sha':admission['candidate_sha'],'repository':str(Path(repository).resolve()),'destination':str(dest),'future_controller':str(future),'future_admission':str(target),'files':files,'before':{'wrapper':digest(old_wrapper),'manifest':digest(old_manifest),'active':digest(reader(state/'local-dev-01/active.json'))},'after':{'wrapper':digest(new_wrapper),'manifest':digest(new_manifest),'admission':digest(raw)},'owner_decision_ref':admission['owner_decision_ref'],'review_ref':admission['review_ref'],'installer_sha256':digest(Path(__file__).read_bytes()),'status':'PREPARED_NOT_INSTALLED'}
 write(dest/'prepared.private.json',encoded(prepared));return {**prepared,'prepared_sha256':digest(encoded(prepared))}

@contextmanager
def locks(state):
 fds=[]
 try:
  for path in (state/'frontend-lifecycle.lock',state/'local-dev-01/selection.lock'):
   fd=os.open(path,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600);fds.append(fd);fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
  yield
 finally:
  for fd in reversed(fds):os.close(fd)

def apply(prepared_path,owner_path):
 reader=module(HERE/'hierarchy_source_admission.py').private_bytes
 raw=reader(Path(prepared_path));prepared=json.loads(raw);dest=Path(prepared['destination'])
 if dest!=Path(prepared_path).parent or raw!=encoded(prepared) or prepared['status']!='PREPARED_NOT_INSTALLED':raise RuntimeError('EXACT_PREPARED_CONTROLLER_REQUIRED')
 owner=json.loads(reader(Path(owner_path)))
 if (set(owner)!={'version','purpose','verdict','prepared_sha256','owner_decision_ref','review_ref'} or type(owner['version']) is not int or owner['version']!=1
     or owner['purpose']!=prepared['purpose'] or owner['verdict']!='GO' or owner['prepared_sha256']!=digest(raw)
     or owner['owner_decision_ref']!=prepared['owner_decision_ref'] or owner['review_ref']!=prepared['review_ref']):raise RuntimeError('EXACT_EXPLICIT_OWNER_GO_REQUIRED')
 if prepared['installer_sha256']!=digest(Path(__file__).read_bytes()):raise RuntimeError('REVIEWED_INSTALLER_CHANGED')
 state=_state(prepared['repository']);wrapper=state.parent/'nadi-dev';manifest=state/'local-development-release.json';active=state/'local-dev-01/active.json'
 before={'wrapper':reader(dest/'wrapper-before.private.sh'),'manifest':reader(dest/'manifest-before.private.json')}
 after={'wrapper':reader(dest/'wrapper.private.sh'),'manifest':reader(dest/'manifest.private.json'),'admission':reader(dest/'admission.private.json')}
 if any(digest(before[k])!=prepared['before'][k] for k in before) or any(digest(after[k])!=prepared['after'][k] for k in after):raise RuntimeError('PREPARED_CONTROLLER_BYTES_CHANGED')
 for name,expected in prepared['files'].items():
  if digest(reader(dest/name))!=expected:raise RuntimeError('PREPARED_CONTROLLER_CODE_CHANGED')
 future=Path(prepared['future_controller']);admission=Path(prepared['future_admission'])
 if future.parent!=state/'controller-releases' or admission.parent!=state/'source-admissions':raise RuntimeError('FIXED_CONTROLLER_TARGET_REQUIRED')
 with locks(state):
  if digest(reader(wrapper,mode=0o700))!=prepared['before']['wrapper'] or digest(reader(manifest))!=prepared['before']['manifest'] or digest(reader(active))!=prepared['before']['active']:raise RuntimeError('CONTROLLER_BASELINE_OR_ACTIVE_CHANGED')
  if future.exists() or admission.exists():raise RuntimeError('CONTROLLER_INSTALL_TARGET_ALREADY_EXISTS')
  future.mkdir(mode=0o700)
  for name in prepared['files']:write(future/name,reader(dest/name))
  write(admission,after['admission'])
  try:
   replace(manifest,after['manifest']);replace(wrapper,after['wrapper'],0o700)
   control=module(future/'nadi-dev.py');control.local_controller().release()
   if digest(reader(active))!=prepared['before']['active']:raise RuntimeError('ACTIVE_SELECTION_CHANGED_DURING_CONTROLLER_INSTALL')
  except BaseException:
   # Compensate only known metadata. Interrupted/power-loss states require the
   # documented owner procedure; this is not a two-file atomicity claim.
   if reader(manifest) not in (before['manifest'],after['manifest']) or reader(wrapper,mode=0o700) not in (before['wrapper'],after['wrapper']):raise RuntimeError('UNKNOWN_CONTROLLER_METADATA_STOP') from None
   replace(manifest,before['manifest']);replace(wrapper,before['wrapper'],0o700);raise
 return {'status':'INSTALLED','candidate_sha':prepared['candidate_sha'],'services_restarted':False,'active_selection_unchanged':True,'files':prepared['files']}

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--repository');parser.add_argument('--admission');parser.add_argument('--output');parser.add_argument('--apply');parser.add_argument('--owner-approval');args=parser.parse_args()
 if args.apply:
  if not args.owner_approval:parser.error('--owner-approval is required')
  result=apply(args.apply,args.owner_approval)
 else:
  if not all((args.repository,args.admission,args.output)):parser.error('preparation needs --repository --admission --output')
  result=prepare(args.repository,args.admission,args.output)
 print(json.dumps(result,sort_keys=True))
