"""Complete synthetic GitHub evidence, no network/token or activation."""
import base64
from copy import deepcopy
from datetime import datetime,timedelta,timezone
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import unittest
import zipfile

FILE=Path(__file__).resolve().parents[2]/'deploy/development/stacked_activation_policy.py'
spec=importlib.util.spec_from_file_location('stacked_local_policy_test',FILE)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
REQUEST=dict(target_pr=120,target_sha='a'*40,base_pr=119,base_sha='b'*40,tooling_pr=121,tooling_sha='c'*40,run_id=10,engineering_run_id=11)
NOW=datetime(2026,11,2,10,tzinfo=timezone.utc)


class Api:
    def __init__(self):
        self.values={};self.zips={};self.calls=[]
        repo={'full_name':m.REPOSITORY}
        for key,ref,base in [('target','candidate','parent'),('base','parent','main'),('tooling','qualification','main')]:
            self.values[f"pulls/{REQUEST[key+'_pr']}"]={'number':REQUEST[key+'_pr'],'state':'open','merged_at':None,'merge_commit_sha':'d'*40,
                'head':{'sha':REQUEST[key+'_sha'],'ref':ref,'repo':repo},'base':{'sha':REQUEST['base_sha'] if key=='target' else 'e'*40,'ref':base,'repo':repo}}
        self.trust={'files':{'synthetic-reviewed-code':m.digest(b'reviewed')}}
        self.values['contents/synthetic-reviewed-code?ref='+REQUEST['tooling_sha']]={'encoding':'base64','content':base64.b64encode(b'reviewed').decode()}
        profile=dict(schema_version=1,purpose='stacked-local-development-only',repository=m.REPOSITORY,target_pr=120,target_sha=REQUEST['target_sha'],base_pr=119,base_sha=REQUEST['base_sha'])
        self.values['contents/'+m.PROFILE+'?ref='+REQUEST['tooling_sha']]={'encoding':'base64','content':base64.b64encode(json.dumps(profile).encode()).decode()}
        for run,sha,path in [(10,REQUEST['tooling_sha'],'.github/workflows/nadi-maximo-stacked-development.yml'),(11,REQUEST['target_sha'],'.github/workflows/nadi-engineering-candidate.yml')]:
            self.values[f'actions/runs/{run}']={'head_sha':sha,'event':'pull_request','path':path,'status':'completed','conclusion':'success','repository':repo}
        names=['select','qualify (3.11)','qualify (3.12)','Maximo stacked development evidence gate']
        jobs=[dict(name=name,status='completed',conclusion='success',steps=[dict(name='Fresh metadata recheck without executing candidate code',conclusion='success')]) for name in names]
        self.values['actions/runs/10/jobs?per_page=100&filter=latest']={'total_count':4,'jobs':jobs}
        self.values['actions/runs/11/jobs?per_page=100&filter=latest']={'total_count':2,'jobs':[dict(name=name,status='completed',conclusion='success') for name in ['backend','frontend']]}
        self.receipts={}
        for index,python in enumerate(['3.11','3.12'],start=1):
            self.receipts[index]={}
            for kind,count in [('collector',206),('contracts',14),('rehearsal',6)]:
                self.receipts[index][f'{kind}-{python}.json']=dict(tested_sha=REQUEST['target_sha'],workflow_sha='d'*40,conclusion='PASS',python=python+'.17',run_url=f'https://github.com/{m.REPOSITORY}/actions/runs/10',tests=count,discovered=count,infrastructure_error=False,failures=0,errors=0,skips=0,expected_failures=0,blocked_external_io=0,owned_root_removed=True)
        self.refresh_artifacts()

    def refresh_artifacts(self):
        artifacts=[]
        for index,python in enumerate(['3.11','3.12'],start=1):
            output=io.BytesIO()
            with zipfile.ZipFile(output,'w') as z:
                for name,value in self.receipts[index].items():z.writestr(name,json.dumps(value))
            data=output.getvalue();self.zips[index]=data
            artifacts.append(dict(id=index,name=f'stacked-development-{python}-'+REQUEST['target_sha'],expired=False,workflow_run={'head_sha':REQUEST['tooling_sha']},digest='sha256:'+m.digest(data)))
        self.values['actions/runs/10/artifacts?per_page=100']={'total_count':2,'artifacts':artifacts}

    def json(self,path):self.calls.append(path);return deepcopy(self.values[path])
    def artifact(self,identifier):return self.zips[identifier]


class LocalActivationQualificationTest(unittest.TestCase):
    def setUp(self):self.api=Api()
    def evidence(self):return m.verify_evidence(self.api,REQUEST,self.api.trust)

    def test_complete_exact_head_matrix_is_only_development_evidence(self):
        result=self.evidence();self.assertEqual(result['status'],'DEVELOPMENT_EVIDENCE_PASS')
        for key in ['production_gate_replaced','grant_authorized','activation_authorized']:self.assertFalse(result[key])
        self.assertEqual(self.api.calls.count('pulls/120'),2)

    def test_main_production_gate_failure_is_not_rewritten_or_retargeted(self):
        self.api.values['pulls/120']['base']['ref']='main'
        with self.assertRaises(ValueError):self.evidence()

    def test_fork_closed_merged_and_moving_heads_denied(self):
        for key,value in [('state','closed'),('merged_at','synthetic-time')]:
            api=Api();api.values['pulls/120'][key]=value
            with self.assertRaises(ValueError):m.verify_evidence(api,REQUEST,api.trust)
        self.api.values['pulls/120']['head']['repo']['full_name']='foreign/repo'
        with self.assertRaises(ValueError):self.evidence()

    def test_code_profile_and_stack_ancestry_inputs_cannot_be_substituted(self):
        for key in ['contents/synthetic-reviewed-code?ref='+REQUEST['tooling_sha'],'contents/'+m.PROFILE+'?ref='+REQUEST['tooling_sha']]:
            api=Api();api.values[key]['content']=base64.b64encode(b'{}').decode()
            with self.assertRaises(ValueError):m.verify_evidence(api,REQUEST,api.trust)
        self.api.values['pulls/120']['base']['sha']='f'*40
        with self.assertRaises(ValueError):self.evidence()

    def test_failed_skipped_or_missing_matrix_and_final_recheck_denied(self):
        for result in ['failure','skipped','cancelled',None]:
            api=Api();api.values['actions/runs/10/jobs?per_page=100&filter=latest']['jobs'][1]['conclusion']=result
            with self.assertRaises(ValueError):m.verify_evidence(api,REQUEST,api.trust)
        self.api.values['actions/runs/10/jobs?per_page=100&filter=latest']['jobs'][-1]['steps']=[]
        with self.assertRaises(ValueError):self.evidence()

    def test_wrong_source_skips_counts_workflow_and_corrupt_zip_denied(self):
        for key,value in [('tested_sha','f'*40),('skips',1),('tests',205),('workflow_sha','f'*40),('blocked_external_io',1)]:
            api=Api();api.receipts[1]['collector-3.11.json'][key]=value;api.refresh_artifacts()
            with self.assertRaises(ValueError):m.verify_evidence(api,REQUEST,api.trust)
        self.api.zips[1]+=b'changed'
        with self.assertRaises(ValueError):self.evidence()

    def test_owner_policy_approval_and_independent_exact_review_are_mandatory(self):
        evidence=self.evidence()
        with self.assertRaises(ValueError):m.recognize(evidence,{}, {},now=NOW,policy_digest='policy',review_digest='review')
        approval=dict(schema_version=1,purpose='LOCAL_DEVELOPMENT_ONLY',request=REQUEST,approval_ref='synthetic-owner-approval',approved_by='local:c759c2d1-19a4-4291-9b66-9218dbd12dea',expires_at=(NOW+timedelta(hours=1)).isoformat(),policy_sha256='policy',review_sha256='review')
        review=dict(status='PASS',target_sha=REQUEST['target_sha'],independent=True,security_review_complete=True)
        result=m.recognize(evidence,approval,review,now=NOW,policy_digest='policy',review_digest='review')
        self.assertEqual(result['status'],'LOCAL_DEVELOPMENT_QUALIFICATION_RECOGNIZED')
        self.assertFalse(result['activation_authorized']);self.assertFalse(result['grant_authorized'])
        for bad in [{**approval,'purpose':'PRODUCTION'},{**approval,'expires_at':(NOW-timedelta(seconds=1)).isoformat()},{**approval,'policy_sha256':'changed'}]:
            with self.assertRaises(ValueError):m.recognize(evidence,bad,review,now=NOW,policy_digest='policy',review_digest='review')
        with self.assertRaises(ValueError):m.recognize(evidence,approval,{**review,'independent':False},now=NOW,policy_digest='policy',review_digest='review')

    def test_private_recognition_approval_rejects_ambiguous_json(self):
        import tempfile,os
        with tempfile.TemporaryDirectory() as root:
            file=Path(root)/'approval.json'
            for data in [b'{"approved":true,"approved":false}',b'{"value":NaN}']:
                file.write_bytes(data);file.chmod(0o600)
                with self.assertRaises(ValueError):m.private_json(file,m.digest(data))


if __name__=='__main__':unittest.main()
