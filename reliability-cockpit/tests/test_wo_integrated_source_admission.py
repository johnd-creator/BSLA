"""Disposable source/policy/controller metadata tests; no live DB, Docker or HTTP."""
import copy
from datetime import datetime,timezone,timedelta
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import subprocess
import unittest
from unittest.mock import Mock,patch
DEPLOY=Path(__file__).resolve().parents[2]/'deploy/development'
def load(path):
 spec=importlib.util.spec_from_file_location('synthetic_'+path.stem,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
m=load(DEPLOY/'wo_integrated_source_admission.py');installer=load(DEPLOY/'wo_integrated_controller.py')
schema=load(DEPLOY.parents[1]/'reliability-cockpit/src/services/factual_read_entitlements.py')

class AdmissionTest(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.base=Path(self.temp.name);self.base.chmod(0o700)
  self.front=self.base/'front';self.front.mkdir();self.recovery=self.base/'recovery';self.state=self.base/'state';self.state.mkdir(mode=0o700)
  self.control=SimpleNamespace(STATE=self.state,ORIGIN='https://localhost:3000')
  self.git=lambda *args,cwd=None:subprocess.check_output(['git','-c','core.hooksPath=/dev/null',*args],cwd=cwd or self.front,text=True,stderr=subprocess.PIPE).strip()
  self.git('init','-q');self.git('config','user.name','Synthetic');self.git('config','user.email','synthetic@invalid')
  for path in m.PERSISTENCE:self.put(path if Path(path).suffix else path+'/synthetic.txt','unchanged')
  for path in m.ALLOWED_DELTA:self.put(path,'baseline')
  self.put('reliability-cockpit/src/services/factual_read_entitlements.py',(DEPLOY.parents[1]/'reliability-cockpit/src/services/factual_read_entitlements.py').read_text())
  self.put('reliability-cockpit/web/package.json','{"dependencies":{"example":"1.0"}}');self.commit();self.old=self.git('rev-parse','HEAD')
  self.git('clone','--no-hardlinks','--quiet',str(self.front),str(self.recovery),cwd=self.base)
  for path in m.ALLOWED_DELTA:self.put(path,'candidate')
  self.commit();self.head=self.git('rev-parse','HEAD')
  self.comparator=SimpleNamespace(COMPATIBILITY_PATHS=('reliability-cockpit/src','reliability-cockpit/web/lib/api.ts','reliability-data-contracts'))
  base_patch=patch.object(m,'BASE_SHA',self.old);base_patch.start();self.addCleanup(base_patch.stop)
  old_approval=b'{"assets":["asset:MAXIMO:MXASSET:BSR:IP:SYNTHETIC-ROOT"]}';directory=self.state/'factual-read-120';directory.mkdir(mode=0o700);self.private(directory/'activation-approval.json',old_approval)
  legacy_patch=patch.object(m.legacy,'approved',return_value={'candidate_sha':'f'*40,'recovery_sha':'e'*40,'factual_approval_sha256':m.sha(old_approval),'subject':'local:synthetic-engineer','engineering_asset_ids':['NADI-ASSET-001']});self.legacy=legacy_patch.start();self.addCleanup(legacy_patch.stop)
  now=datetime.now(timezone.utc).replace(microsecond=0);self.now=now
  common={'subject':'local:synthetic-engineer','not_before':schema.instant(now),'expires_at':schema.instant(now+timedelta(hours=24)),'actor':m.ISSUER,'approval_ref':'synthetic-owner','operator_ref':'synthetic-private-issuer'}
  self.grants=[dict(common,grant_id='synthetic-registered',scope_kind='REGISTERED_BSR_IP',assets=[],capabilities=sorted(m.READ_CAPS)),dict(common,grant_id='synthetic-hierarchy',scope_kind='EXACT_ASSETS',assets=['asset:MAXIMO:MXASSET:BSR:IP:SYNTHETIC-ROOT'],capabilities=sorted(m.READ_CAPS|{'FACTUAL_HIERARCHY_READ'}))]
  self.value={'version':1,'purpose':'NADI_WO_INTEGRATED_LOCAL_RELEASE_01','prior_sha':self.old,'recovery_sha':self.old,'candidate_sha':self.head,'candidate_tree':self.git('rev-parse','HEAD^{tree}'),'objects':{p:[m.object_id(self.recovery,self.old,p),m.object_id(self.front,self.head,p)] for p in self.comparator.COMPATIBILITY_PATHS},'changed_files':{p:[m.object_id(self.recovery,self.old,p),m.object_id(self.front,self.head,p)] for p in m.ALLOWED_DELTA},'subject':'local:synthetic-engineer','engineering_asset_ids':['NADI-ASSET-001'],'policy_prior_head':'0'*64,'required_grants':self.grants,'owner_decision_ref':'synthetic-owner','review_ref':'synthetic-independent-review'}
  self.save()
 def put(self,path,data):
  p=self.front/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(data)
 def commit(self):self.git('add','.');self.git('commit','-qm','synthetic checkpoint')
 def private(self,path,data):path.write_bytes(data);path.chmod(0o600)
 def save(self):
  directory=self.state/'source-admissions';directory.mkdir(mode=0o700,exist_ok=True);raw=(m.canonical(self.value)+'\n').encode();self.private(directory/'approved.json',raw)
  record={'wo_integrated_release':{'admission_file':str(directory/'approved.json'),'admission_sha256':m.sha(raw),'module_sha256':m.sha((DEPLOY/'wo_integrated_source_admission.py').read_bytes())}}
  self.private(self.state/'local-development-release.json',json.dumps(record).encode())
 def check(self):return m.compatible(self.control,self.comparator,self.front,self.recovery,self.head,self.old)
 def policy(self,grants=None):
  directory=self.state/'factual-read-120';directory.mkdir(mode=0o700,exist_ok=True);previous='0'*64;events=[]
  for index,grant in enumerate(grants or self.grants):
   e={**grant,'version':index+1,'previous_sha256':previous,'action':'ISSUE','at':schema.instant(self.now)};e['sha256']=m.sha(schema.canonical(e).encode());schema.validate_event(e);events.append(e);previous=e['sha256']
  self.private(directory/'grants.ndjson',b'{"schema_version":1}\n'+b''.join(schema.canonical(e).encode()+b'\n' for e in events));return events
 def test_exact_source_admission_passes_and_historical_check_runs(self):
  self.assertEqual(len(self.check()),64);self.assertGreater(self.legacy.call_count,0)
 def test_unlisted_changed_or_untracked_source_denied(self):
  self.put('reliability-cockpit/src/services/UNREVIEWED.py','unexpected')
  with self.assertRaisesRegex(RuntimeError,'WORKTREE_DRIFT'):self.check()
  self.commit()
  with self.assertRaisesRegex(RuntimeError,'REVISION_MISMATCH'):self.check()
 def test_dependency_difference_denied(self):
  self.put('reliability-cockpit/web/package.json','{"dependencies":{"example":"2.0"}}');self.commit();self.head=self.git('rev-parse','HEAD');self.value.update(candidate_sha=self.head,candidate_tree=self.git('rev-parse','HEAD^{tree}'));self.save()
  with self.assertRaisesRegex(RuntimeError,'DEPENDENCY_DIFFERENCE'):self.check()
 def test_unknown_tuple_delegates_original_historical_guard(self):
  strict=Mock();strict.compatible.return_value='historical';self.assertEqual(m.compatible(self.control,strict,self.recovery,self.recovery,self.old,self.old),'historical');strict.compatible.assert_called_once()
 def test_app_persistence_change_refused_even_if_owner_objects_updated(self):
  path='reliability-cockpit/src/repositories/application_models.py';self.put(path,'changed');self.commit();self.head=self.git('rev-parse','HEAD');self.value.update(candidate_sha=self.head,candidate_tree=self.git('rev-parse','HEAD^{tree}'));self.value['objects']={p:[m.object_id(self.recovery,self.old,p),m.object_id(self.front,self.head,p)] for p in self.comparator.COMPATIBILITY_PATHS};self.save()
  with self.assertRaisesRegex(RuntimeError,'PERSISTENCE_CHANGE_DENIED'):self.check()
 def test_admission_rejects_nonissuer_time_and_falsy_nonlist_assets(self):
  for invalid in ('2026-11-04T10:00:00+07:00','2026-11-04T03:00:00.000Z','2026-11-04T03:00:00','2026-02-30T03:00:00Z'):
   value=copy.deepcopy(self.value);value['required_grants'][0]['not_before']=invalid
   with self.subTest(time=invalid),self.assertRaises(RuntimeError):m.decode((m.canonical(value)+'\n').encode())
  for invalid in (None,{},'',False):
   value=copy.deepcopy(self.value);value['required_grants'][0]['assets']=invalid
   with self.subTest(assets=invalid),self.assertRaises(RuntimeError):m.decode((m.canonical(value)+'\n').encode())
 def test_prepared_grants_match_real_issuer_schema_without_issuing(self):
  before=copy.deepcopy(self.value);m.validate_issuer_contract(self.value,schema);self.assertEqual(before,self.value)
  value=copy.deepcopy(self.value);value['required_grants'][0]['assets']=None
  with self.assertRaisesRegex(ValueError,'ASSETS_INVALID'):m.validate_issuer_contract(value,schema)
 def test_active_closed_grants_pass_without_engineering_write_scope_change(self):
  self.policy();before=list(self.value['engineering_asset_ids']);env=m.factual_environment(self.control,{'sha':self.head,'root':str(self.front)});self.assertEqual(len(env),1);self.assertEqual(self.value['engineering_asset_ids'],before)
 def test_missing_or_different_subject_grant_denied(self):
  self.policy(self.grants[:1])
  with self.assertRaisesRegex(RuntimeError,'NOT_ISSUED'):m.factual_environment(self.control,{'sha':self.head,'root':str(self.front)})
  grants=copy.deepcopy(self.grants);grants[1]['subject']='local:other';self.policy(grants)
  with self.assertRaisesRegex(RuntimeError,'INACTIVE_OR_CHANGED'):m.factual_environment(self.control,{'sha':self.head,'root':str(self.front)})
 def test_expired_grants_deny_candidate_but_do_not_block_baseline_transport(self):
  for grant in self.grants:grant.update(not_before=schema.instant(self.now-timedelta(hours=25)),expires_at=schema.instant(self.now-timedelta(hours=1)))
  self.value['required_grants']=self.grants;self.save();self.now-=timedelta(hours=25);self.policy()
  with self.assertRaisesRegex(RuntimeError,'INACTIVE_OR_CHANGED'):m.factual_environment(self.control,{'sha':self.head,'root':str(self.front)})
  self.assertEqual(len(m.factual_environment(self.control,{'sha':self.old,'root':str(self.recovery)})),1)
 def test_broader_hierarchy_scope_and_engineering_asset_change_denied(self):
  for change in ('hierarchy','write'):
   value=copy.deepcopy(self.value)
   if change=='hierarchy':value['required_grants'][1]['assets'].append('asset:MAXIMO:MXASSET:BSR:IP:OTHER')
   else:value['engineering_asset_ids']=['OTHER']
   with self.assertRaises(RuntimeError):m.decode((m.canonical(value)+'\n').encode())
 def test_source_only_fixture_admission_checks_records_and_schema(self):
  with patch.object(m,'compatible',return_value='pinned-source'):
   manager=SimpleNamespace(fixture_probe=Mock(return_value={'ledger':[{'status':'APPLIED'}],'records':{'count':1}}));previous={'root':str(self.recovery),'sha':self.old}
   self.assertEqual(len(m.fixture_contract(self.control,manager,previous,self.front,self.head)),64)
   manager.fixture_probe.side_effect=[{'ledger':[{'status':'APPLIED'}],'records':{'count':1}},{'ledger':[{'status':'APPLIED'}],'records':{'count':2}}]
   with self.assertRaisesRegex(RuntimeError,'SCHEMA_OR_RECORDS_CHANGED'):m.fixture_contract(self.control,manager,previous,self.front,self.head)
 def test_engineer_session_rejects_admin_other_subject_or_write_scope(self):
  proof=self.base/'proof.json';self.private(proof,b'{"cookie":"SYNTHETIC_ONLY"}')
  manager=SimpleNamespace(probe=Mock(return_value={'status':200,'data':{'subject':self.value['subject'],'roles':['AUTHOR'],'asset_ids':['NADI-ASSET-001']}}))
  m.engineer_session(self.control,manager,{'sha':self.head},str(proof))
  for changed in ({'roles':['ADMIN']},{'subject':'local:other'},{'asset_ids':['OTHER']}):
   manager.probe.return_value={'status':200,'data':{**{'subject':self.value['subject'],'roles':['AUTHOR'],'asset_ids':['NADI-ASSET-001']},**changed}}
   with self.assertRaisesRegex(RuntimeError,'EXACT_WO_ENGINEER_AUTHOR_REQUIRED'):m.engineer_session(self.control,manager,{'sha':self.head},str(proof))
 def test_private_proof_permissions_and_missing_session_denied(self):
  with self.assertRaisesRegex(RuntimeError,'SESSION_REQUIRED'):m.engineer_session(self.control,Mock(),{'sha':self.head},None)
  proof=self.base/'proof.json';proof.write_text('{"cookie":"SYNTHETIC_ONLY"}');proof.chmod(0o644)
  with self.assertRaisesRegex(RuntimeError,'PRIVATE_ADMISSION_FILE_REQUIRED'):m.engineer_session(self.control,Mock(),{'sha':self.head},str(proof))

class AmendmentTest(unittest.TestCase):
 def test_only_exact_installed_controller_anchors_are_accepted(self):
  source="""class Controller:
 def release(self):
  value={'nadi-dev.py','local_development.py','local_fixture.py','frontend_preview.py','pdm_007_bridge.py','hierarchy_source_admission.py'}
 def hierarchy_module(self):
  return spec_from_file_location('reviewed_hierarchy_source_admission',Path(__file__).with_name('hierarchy_source_admission.py'))
    def fixture_contract(self, previous, root, sha):
        return 'old persistence guard'
"""
  # Use syntactically consistent indentation while keeping the exact 4-space anchor.
  source=source.replace(' def release','    def release').replace("  value=","        value=").replace(' def hierarchy_module','    def hierarchy_module').replace('  return spec','        return spec')
  result=installer.amend(source);self.assertIn("return 'old persistence guard'",result);self.assertIn('wo_integrated_source_admission.py',result)
  with self.assertRaisesRegex(RuntimeError,'ANCHOR_CHANGED'):installer.amend(source.replace("'pdm_007_bridge.py',",''))
 def test_owner_go_is_required_before_any_controller_mutation(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);root.chmod(0o700);prepared={'destination':str(root),'status':'PREPARED_NOT_INSTALLED'}
   (root/'prepared.json').write_bytes(installer.encoded(prepared));(root/'prepared.json').chmod(0o600)
   (root/'owner.json').write_bytes(b'{"verdict":"PROPOSED"}');(root/'owner.json').chmod(0o600)
   with self.assertRaisesRegex(RuntimeError,'OWNER_GO_REQUIRED'):installer.apply(root/'prepared.json',root/'owner.json')


class MetadataRecoveryTest(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.base=Path(self.temp.name);self.base.chmod(0o700)
  self.repository=self.base/'repository';self.repository.mkdir(mode=0o700);self.state=self.repository/'.nadi-dev/state';self.state.mkdir(mode=0o700,parents=True);self.state.parent.chmod(0o700)
  for name in ('controller-releases','source-admissions','local-dev-01'):(self.state/name).mkdir(mode=0o700)
  self.dest=self.base/'prepared';self.dest.mkdir(mode=0o700)
  self.wrapper=self.state.parent/'nadi-dev';self.manifest=self.state/'local-development-release.json';self.active=self.state/'local-dev-01/active.json'
  self.private(self.wrapper,b'old-wrapper',0o700);self.private(self.manifest,b'old-manifest');self.private(self.active,b'active')
  for name,data in [('wrapper-before.private.sh',b'old-wrapper'),('manifest-before.private.json',b'old-manifest'),('wrapper.private.sh',b'new-wrapper'),('manifest.private.json',b'new-manifest'),('admission.private.json',b'new-admission'),('nadi-dev.py',b'# synthetic controller')]:self.private(self.dest/name,data)
  value={'version':1,'purpose':'NADI_WO_INTEGRATED_LOCAL_RELEASE_01','candidate_sha':'b'*40,'repository':str(self.repository),'destination':str(self.dest),'future_controller':str(self.state/'controller-releases/new'),'future_admission':str(self.state/'source-admissions/new.json'),'files':{'nadi-dev.py':installer.digest(b'# synthetic controller')},'before':{'wrapper':installer.digest(b'old-wrapper'),'manifest':installer.digest(b'old-manifest'),'active':installer.digest(b'active')},'after':{'wrapper':installer.digest(b'new-wrapper'),'manifest':installer.digest(b'new-manifest'),'admission':installer.digest(b'new-admission')},'owner_decision_ref':'synthetic-owner','review_ref':'synthetic-review','installer_sha256':installer.digest((DEPLOY/'wo_integrated_controller.py').read_bytes()),'status':'PREPARED_NOT_INSTALLED'}
  raw=installer.encoded(value);self.private(self.dest/'prepared.private.json',raw)
  owner={'version':1,'purpose':value['purpose'],'verdict':'GO','prepared_sha256':installer.digest(raw),'owner_decision_ref':'synthetic-owner','review_ref':'synthetic-review'};self.private(self.dest/'owner.private.json',installer.encoded(owner))
 def private(self,path,data,mode=0o600):path.write_bytes(data);path.chmod(mode)
 def execute(self,callback):
  original=installer.module
  def selected(path):
   if Path(path).name=='hierarchy_source_admission.py':return original(path)
   return SimpleNamespace(local_controller=lambda:SimpleNamespace(release=callback))
  with patch.object(installer,'module',side_effect=selected):return installer.apply(self.dest/'prepared.private.json',self.dest/'owner.private.json')
 def test_metadata_install_has_no_service_or_active_selection_change(self):
  result=self.execute(lambda:None);self.assertEqual(result['status'],'INSTALLED');self.assertFalse(result['services_restarted']);self.assertEqual(self.active.read_bytes(),b'active')
 def test_post_replace_failure_compensates_both_known_metadata_files(self):
  def fail():raise RuntimeError('synthetic final verification failure')
  with self.assertRaisesRegex(RuntimeError,'synthetic final'):self.execute(fail)
  self.assertEqual(self.wrapper.read_bytes(),b'old-wrapper');self.assertEqual(self.manifest.read_bytes(),b'old-manifest');self.assertEqual(self.wrapper.stat().st_mode&0o777,0o700);self.assertEqual(self.active.read_bytes(),b'active')
 def test_intervening_active_change_refused_before_install(self):
  self.active.write_bytes(b'new-active')
  with self.assertRaisesRegex(RuntimeError,'BASELINE_OR_ACTIVE_CHANGED'):self.execute(lambda:None)
  self.assertFalse((self.state/'controller-releases/new').exists());self.assertEqual(self.wrapper.read_bytes(),b'old-wrapper')
 def test_unknown_metadata_is_never_overwritten_by_compensation(self):
  def fail():self.manifest.write_bytes(b'unknown concurrent manifest');raise RuntimeError('synthetic failure')
  with self.assertRaisesRegex(RuntimeError,'UNKNOWN_CONTROLLER_METADATA_STOP'):self.execute(fail)
  self.assertEqual(self.manifest.read_bytes(),b'unknown concurrent manifest')

class GrantBatchTest(unittest.TestCase):
 def setUp(self):
  self.resolver=load(DEPLOY/'wo_integrated_grants.py')
  self.first={'grant_id':'synthetic-first','subject':'local:synthetic-engineer','assets':[],'capabilities':sorted(m.READ_CAPS),'not_before':'2026-11-04T03:00:00Z','expires_at':'2026-11-05T03:00:00Z','actor':m.ISSUER,'approval_ref':'synthetic-owner','operator_ref':'synthetic-issuer','scope_kind':'REGISTERED_BSR_IP'}
  self.second={**self.first,'grant_id':'synthetic-second','scope_kind':'EXACT_ASSETS','assets':['asset:MAXIMO:MXASSET:BSR:IP:SYNTHETIC-ROOT'],'capabilities':sorted(m.READ_CAPS|{'FACTUAL_HIERARCHY_READ'})}
  self.admission={'policy_prior_head':'0'*64,'required_grants':[self.first,self.second]}
 def event(self,grant):
  event={**grant,'version':1,'previous_sha256':'0'*64,'action':'ISSUE','at':'2026-11-04T03:00:00Z'};event['sha256']=m.sha(schema.canonical(event).encode());schema.validate_event(event);return event
 def test_first_packet_is_exact_and_does_not_write_policy(self):
  raw=b'{"schema_version":1}\n';packet=self.resolver.next_approval(self.admission,raw,0);self.assertEqual(packet['expected_head'],'0'*64);self.assertEqual(packet['assets'],[]);self.assertEqual(raw,b'{"schema_version":1}\n')
 def test_second_packet_derives_head_only_from_first_exact_receipt(self):
  event=self.event(self.first);raw=b'{"schema_version":1}\n'+schema.canonical(event).encode()+b'\n';packet=self.resolver.next_approval(self.admission,raw,1);self.assertEqual(packet['expected_head'],event['sha256']);self.assertEqual(packet['grant_id'],self.second['grant_id'])
 def test_intervening_or_wrong_receipt_refused(self):
  event=self.event(dict(self.first,subject='local:other'));raw=b'{"schema_version":1}\n'+schema.canonical(event).encode()+b'\n'
  with self.assertRaisesRegex(RuntimeError,'FIRST_APPROVED'):self.resolver.next_approval(self.admission,raw,1)
  with self.assertRaisesRegex(RuntimeError,'HEAD_CHANGED'):self.resolver.next_approval(self.admission,raw,0)
 def test_second_packet_cannot_be_prepared_before_first_is_committed(self):
  with self.assertRaisesRegex(RuntimeError,'HEAD_CHANGED'):self.resolver.next_approval(self.admission,b'{"schema_version":1}\n',1)
