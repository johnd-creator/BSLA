"""Exact WO release admission layered over the accepted hierarchy controller.

No grant issuance, source request, lifecycle operation or database write. Owner
approval pins the complete immutable source tuple and required read grants.
"""
import importlib.util
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

_spec=importlib.util.spec_from_file_location('accepted_hierarchy_admission',Path(__file__).with_name('hierarchy_source_admission.py'))
legacy=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(legacy)
canonical,sha,private_bytes,git,object_id=(getattr(legacy,n) for n in ('canonical','sha','private_bytes','git','object_id'))
BASE_SHA='469f21fe0e6f1d44e838b7d9dc47d55a16704625'
ALLOWED_DELTA={
 'reliability-cockpit/src/api/reliability.py','reliability-cockpit/src/repositories/mart_reader.py',
 'reliability-cockpit/src/services/registered_maintenance_overview.py',
 'reliability-cockpit/src/services/wo_detail.py','reliability-cockpit/src/services/wo_evidence_sql.py',
 'reliability-cockpit/src/services/wo_overview.py','reliability-cockpit/web/lib/api.ts',
 'reliability-data-contracts/mappings/maximo-to-contracts.md',
 'reliability-data-contracts/schemas/maintenance-event.schema.json',
}
PERSISTENCE=tuple(p for p in legacy.PERSISTENCE if p!='reliability-cockpit/src/repositories')+(
 'reliability-cockpit/src/repositories/application_models.py',
 'reliability-cockpit/src/repositories/application_migrations.py',
 'reliability-cockpit/src/repositories/mart_models.py',
)
FIELDS={'version','purpose','prior_sha','recovery_sha','candidate_sha','candidate_tree',
 'objects','changed_files','subject','engineering_asset_ids','policy_prior_head','required_grants',
 'owner_decision_ref','review_ref'}
GRANT_FIELDS={'grant_id','subject','assets','capabilities','not_before','expires_at','actor',
 'approval_ref','operator_ref','scope_kind'}
ISSUER='local:c759c2d1-19a4-4291-9b66-9218dbd12dea'
READ_CAPS={'FACTUAL_DASHBOARD_READ','FACTUAL_ASSET_READ','FACTUAL_MAINTENANCE_READ'}

def decode(raw):
 value=json.loads(raw)
 if (not isinstance(value,dict) or set(value)!=FIELDS or raw!=(canonical(value)+'\n').encode()
     or type(value['version']) is not int or value['version']!=1
     or value['purpose']!='NADI_WO_INTEGRATED_LOCAL_RELEASE_01' or value['prior_sha']!=BASE_SHA):
  raise RuntimeError('EXACT_WO_RELEASE_ADMISSION_REQUIRED')
 for key in ('recovery_sha','candidate_sha','candidate_tree'):
  if not isinstance(value[key],str) or not re.fullmatch('[a-f0-9]{40}',value[key]):raise RuntimeError('EXACT_WO_REVISION_REQUIRED')
 if not re.fullmatch('[a-f0-9]{64}',value['policy_prior_head']):raise RuntimeError('EXACT_PRIOR_POLICY_REQUIRED')
 if not re.fullmatch('local:[A-Za-z0-9-]{1,150}',value['subject']):raise RuntimeError('EXACT_ENGINEER_REQUIRED')
 if value['engineering_asset_ids']!=['NADI-ASSET-001']:raise RuntimeError('ORIGINAL_ENGINEERING_SCOPE_REQUIRED')
 for key in ('owner_decision_ref','review_ref'):
  if not isinstance(value[key],str) or not re.fullmatch('[A-Za-z0-9_.:-]{1,160}',value[key]):raise RuntimeError('EXACT_OWNER_REVIEW_REQUIRED')
 if not isinstance(value['objects'],dict) or not isinstance(value['changed_files'],dict) or set(value['changed_files'])!=ALLOWED_DELTA:
  raise RuntimeError('CLOSED_WO_SOURCE_DELTA_REQUIRED')
 for mapping in (value['objects'],value['changed_files']):
  for path,pair in mapping.items():
   if (not isinstance(path,str) or path.startswith('/') or '..' in path.split('/') or
       not isinstance(pair,list) or len(pair)!=2 or any(not isinstance(x,str) or not re.fullmatch('[a-f0-9]{40}|ABSENT',x) for x in pair)):
    raise RuntimeError('WO_SOURCE_INVENTORY_INVALID')
 grants=value['required_grants']
 if not isinstance(grants,list) or len(grants)!=2:raise RuntimeError('TWO_EXACT_READ_GRANTS_REQUIRED')
 for index,grant in enumerate(grants):
  if not isinstance(grant,dict) or set(grant)!=GRANT_FIELDS or grant['subject']!=value['subject'] or grant['actor']!=ISSUER:
   raise RuntimeError('EXACT_READ_SUBJECT_ISSUER_REQUIRED')
  if (not all(isinstance(grant[k],str) and re.fullmatch('[A-Za-z0-9_.:-]{1,160}',grant[k]) for k in ('grant_id','approval_ref','operator_ref'))
      or grant['capabilities']!=sorted(set(grant['capabilities']))):raise RuntimeError('EXACT_READ_METADATA_REQUIRED')
  start,end=(_time(grant[k]) for k in ('not_before','expires_at'))
  if not 0<(end-start).total_seconds()<=86400:raise RuntimeError('BOUNDED_READ_WINDOW_REQUIRED')
  if index==0:
   if grant['scope_kind']!='REGISTERED_BSR_IP' or grant['assets']!=[] or set(grant['capabilities'])!=READ_CAPS:
    raise RuntimeError('REGISTERED_READ_ONLY_REQUIRED')
  elif (grant['scope_kind']!='EXACT_ASSETS' or not isinstance(grant['assets'],list) or len(grant['assets'])!=1 or not isinstance(grant['assets'][0],str) or not re.fullmatch(r'asset:MAXIMO:MXASSET:BSR:IP:[A-Za-z0-9_.-]{1,120}',grant['assets'][0])
        or set(grant['capabilities'])!=READ_CAPS|{'FACTUAL_HIERARCHY_READ'}):
   raise RuntimeError('EXACT_EXISTING_HIERARCHY_READ_REQUIRED')
 if grants[0]['grant_id']==grants[1]['grant_id']:raise RuntimeError('DISTINCT_READ_GRANTS_REQUIRED')
 return value

def _time(value):
 try:
  if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ',value):raise ValueError()
  parsed=datetime.strptime(value,'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
  if parsed.tzinfo is None or value.endswith('-00:00'):raise ValueError()
  return parsed.astimezone(timezone.utc)
 except (ValueError,TypeError,AttributeError):raise RuntimeError('AWARE_READ_WINDOW_REQUIRED') from None

def validate_issuer_contract(value,schema):
 # Exercise the actual issuer event schema before preparation. These in-memory
 # prospective records are validation only; no policy receipt is persisted.
 previous='0'*64
 for index,grant in enumerate(value['required_grants']):
  event={**grant,'version':index+1,'previous_sha256':previous,'action':'ISSUE','at':grant['not_before']}
  event['sha256']=sha(schema.canonical(event).encode())
  schema.validate_event(event);previous=event['sha256']

def approved(control):
 # Every historical controller/module/admission check remains mandatory.
 baseline=legacy.approved(control)
 record=json.loads(private_bytes(control.STATE/'local-development-release.json'))
 pin=record.get('wo_integrated_release',{})
 if set(pin)!={'admission_file','admission_sha256','module_sha256'}:raise RuntimeError('INSTALLED_WO_ADMISSION_REQUIRED')
 path=Path(pin['admission_file'])
 if path.parent!=control.STATE/'source-admissions':raise RuntimeError('FIXED_WO_ADMISSION_LOCATION_REQUIRED')
 if pin['module_sha256']!=sha(Path(__file__).read_bytes()):raise RuntimeError('WO_ADMISSION_MODULE_CHANGED')
 raw=private_bytes(path)
 if sha(raw)!=pin['admission_sha256']:raise RuntimeError('WO_ADMISSION_APPROVAL_CHANGED')
 value=decode(raw)
 old_raw=private_bytes(control.STATE/'factual-read-120/activation-approval.json')
 if sha(old_raw)!=baseline['factual_approval_sha256']:raise RuntimeError('ORIGINAL_READ_APPROVAL_CHANGED')
 old=json.loads(old_raw)
 if value['subject']!=baseline['subject'] or value['engineering_asset_ids']!=baseline['engineering_asset_ids'] or value['required_grants'][1]['assets']!=old['assets']:
  raise RuntimeError('ORIGINAL_ENGINEER_OR_HIERARCHY_SCOPE_CHANGED')
 return value

def compatible(control,comparator,front,recovery,candidate_sha,recovery_sha):
 value=approved(control)
 if (candidate_sha,recovery_sha)!=(value['candidate_sha'],value['recovery_sha']):
  return legacy.compatible(control,comparator,front,recovery,candidate_sha,recovery_sha)
 if git(front,'rev-parse','HEAD')!=candidate_sha or git(recovery,'rev-parse','HEAD')!=recovery_sha or git(front,'rev-parse',candidate_sha+'^{tree}')!=value['candidate_tree']:
  raise RuntimeError('WO_SOURCE_REVISION_MISMATCH')
 paths=comparator.COMPATIBILITY_PATHS
 if set(value['objects'])!=set(paths):raise RuntimeError('WO_COMPATIBILITY_PATH_SET_CHANGED')
 actual={p:[object_id(recovery,recovery_sha,p),object_id(front,candidate_sha,p)] for p in paths}
 if actual!=value['objects'] or any(pair[0]!=object_id(front,BASE_SHA,p) for p,pair in actual.items()):raise RuntimeError('WO_SOURCE_OBJECT_MISMATCH')
 for path in PERSISTENCE:
  if object_id(recovery,recovery_sha,path)!=object_id(front,candidate_sha,path):raise RuntimeError('WO_PERSISTENCE_CHANGE_DENIED')
 changed=git(front,'diff','--name-only',BASE_SHA,candidate_sha,'--',*paths).splitlines()
 if set(changed)!=ALLOWED_DELTA:raise RuntimeError('WO_UNREVIEWED_SOURCE_DELTA')
 if {p:[object_id(recovery,recovery_sha,p),object_id(front,candidate_sha,p)] for p in changed}!=value['changed_files']:
  raise RuntimeError('WO_SOURCE_LEAF_MISMATCH')
 a=json.loads(git(front,'show',candidate_sha+':reliability-cockpit/web/package.json'))
 b=json.loads(git(recovery,'show',recovery_sha+':reliability-cockpit/web/package.json'))
 for key in ('dependencies','devDependencies','engines','overrides'):
  if a.get(key)!=b.get(key):raise RuntimeError('WO_DEPENDENCY_DIFFERENCE')
 for root,revision in ((front,candidate_sha),(recovery,recovery_sha)):
  if git(root,'diff','--name-only',revision,'--',*paths) or git(root,'ls-files','--others','--exclude-standard','--',*paths):raise RuntimeError('WO_SOURCE_WORKTREE_DRIFT')
 return sha(canonical({'admission':value,'objects':actual}).encode())

def fixture_contract(control,manager,previous,root,revision):
 value=approved(control)
 if (revision,previous['sha'])!=(value['candidate_sha'],value['recovery_sha']):return None
 spec=importlib.util.spec_from_file_location('unchanged_pair_comparator',Path(__file__).with_name('frontend_preview.py'))
 comparator=importlib.util.module_from_spec(spec);spec.loader.exec_module(comparator)
 source_digest=compatible(control,comparator,root,Path(previous['root']),revision,previous['sha'])
 old=manager.fixture_probe(previous);new=manager.fixture_probe(dict(previous,root=str(root),sha=revision))
 if old!=new or any(row['status']!='APPLIED' for row in old['ledger']):raise RuntimeError('WO_FIXTURE_SCHEMA_OR_RECORDS_CHANGED')
 return sha(canonical({'source':source_digest,'fixture':old}).encode())

def _policy(control,root,value,*,require_active):
 path=control.STATE/'factual-read-120/grants.ndjson';raw=private_bytes(path)
 spec=importlib.util.spec_from_file_location('wo_approved_read_schema',root/'reliability-cockpit/src/services/factual_read_entitlements.py')
 schema=importlib.util.module_from_spec(spec);spec.loader.exec_module(schema)
 events=schema.decode(raw)
 if require_active:
  prior=value['policy_prior_head'];start=0 if prior=='0'*64 else next((i+1 for i,e in enumerate(events) if e['sha256']==prior),None)
  if start is None or len(events)<start+2:raise RuntimeError('WO_REQUIRED_READ_GRANTS_NOT_ISSUED')
  now=datetime.now(timezone.utc)
  for index,expected in enumerate(value['required_grants']):
   issued=events[start+index];latest=next(e for e in reversed(events) if e['grant_id']==expected['grant_id'])
   if (issued['action']!='ISSUE' or any(issued[k]!=expected[k] for k in GRANT_FIELDS)
       or latest!=issued or not schema.timestamp(issued['not_before'])<=now<schema.timestamp(issued['expires_at'])):
    raise RuntimeError('WO_REQUIRED_READ_GRANT_INACTIVE_OR_CHANGED')
  if any(schema.timestamp(e['at'])>now+timedelta(seconds=5) for e in events):raise RuntimeError('WO_POLICY_CLOCK_INVALID')
 return ['NADI_FACTUAL_READ_POLICY_FILE='+str(path)]

def factual_environment(control,selected):
 value=approved(control)
 if selected['sha'] not in (value['candidate_sha'],value['recovery_sha']):return legacy.factual_environment(control,selected)
 root=Path(selected['root'])
 if git(root,'rev-parse','HEAD')!=selected['sha']:raise RuntimeError('WO_SELECTED_SOURCE_CHANGED')
 # Restoring baseline transport must remain possible after read-grant expiry.
 # The unchanged application policy still denies expired/revoked data access.
 return _policy(control,root,value,require_active=selected['sha']==value['candidate_sha'])

def engineer_session(control,manager,selected,session_file):
 value=approved(control)
 if selected['sha'] not in (value['candidate_sha'],value['recovery_sha']):return legacy.engineer_session(control,manager,selected,session_file)
 if not session_file:raise RuntimeError('EXACT_WO_ENGINEER_SESSION_REQUIRED')
 proof=json.loads(private_bytes(Path(session_file),4096))
 if set(proof)!={'cookie'}:raise RuntimeError('PRIVATE_SESSION_FILE_INVALID')
 response=manager.probe(control.ORIGIN+'/api/engineering-qa/session',proof['cookie']);who=response.get('data')
 if response['status']!=200 or not isinstance(who,dict) or who.get('subject')!=value['subject'] or who.get('roles')!=['AUTHOR'] or sorted(who.get('asset_ids',[]))!=value['engineering_asset_ids']:
  raise RuntimeError('EXACT_WO_ENGINEER_AUTHOR_REQUIRED')
