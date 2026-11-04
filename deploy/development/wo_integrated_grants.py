"""Resolve the next owner-approved read packet; never authenticates or issues it.

A separate official factual_reads CLI requires fresh issuer authentication for
 each packet. The second packet binds only to the committed first receipt.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent

def load(path):
 spec=importlib.util.spec_from_file_location('wo_grant_'+path.stem,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

admission_schema=load(HERE/'wo_integrated_source_admission.py')
policy_schema=load(HERE.parents[1]/'reliability-cockpit/src/services/factual_read_entitlements.py')

def next_approval(admission,policy,index):
 if type(index) is not int or index not in (0,1):raise RuntimeError('EXACT_GRANT_PACKET_INDEX_REQUIRED')
 events=policy_schema.decode(policy);prior=admission['policy_prior_head']
 start=0 if prior=='0'*64 else next((i+1 for i,e in enumerate(events) if e['sha256']==prior),None)
 if start is None or len(events)!=start+index:raise RuntimeError('READ_BATCH_HEAD_CHANGED')
 if index:
  first=events[start]
  if first['action']!='ISSUE' or any(first[k]!=admission['required_grants'][0][k] for k in admission_schema.GRANT_FIELDS):raise RuntimeError('FIRST_APPROVED_READ_PACKET_CHANGED')
 head=events[-1]['sha256'] if events else '0'*64
 return {'schema_version':1,'expected_head':head,'action':'ISSUE',**admission['required_grants'][index]}

def prepare(admission_path,policy_path,index,owner_path,output):
 raw=admission_schema.private_bytes(Path(admission_path));admission=admission_schema.decode(raw)
 owner=json.loads(admission_schema.private_bytes(Path(owner_path)))
 if (set(owner)!={'version','purpose','verdict','admission_sha256','owner_decision_ref'} or type(owner['version']) is not int or owner['version']!=1
     or owner['purpose']!=admission['purpose'] or owner['verdict']!='GO'
     or owner['admission_sha256']!=hashlib.sha256(raw).hexdigest() or owner['owner_decision_ref']!=admission['owner_decision_ref']):
  raise RuntimeError('EXACT_OWNER_READ_BATCH_GO_REQUIRED')
 target=Path(output);policy_schema.private_parent(target)
 packet=next_approval(admission,policy_schema.private_read(Path(policy_path)),index)
 data=(policy_schema.canonical(packet)+'\n').encode()
 from os import open as os_open,fdopen,O_WRONLY,O_CREAT,O_EXCL,O_NOFOLLOW,fsync
 fd=os_open(target,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0o600)
 with fdopen(fd,'wb') as stream:stream.write(data);stream.flush();fsync(stream.fileno())
 return {'status':'OWNER_APPROVED_PACKET_PREPARED_NOT_ISSUED','packet_index':index,'path':str(target),'sha256':hashlib.sha256(data).hexdigest()}

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__)
 for name in ('admission','policy','owner-approval','output'):parser.add_argument('--'+name,required=True)
 parser.add_argument('--index',type=int,required=True);args=parser.parse_args()
 print(json.dumps(prepare(args.admission,args.policy,args.index,args.owner_approval,args.output),sort_keys=True))
