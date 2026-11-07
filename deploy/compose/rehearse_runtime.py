#!/usr/bin/env python3
"""Real Compose restart/recreate proof, no credentials/network/business workers."""
import json
from pathlib import Path
import subprocess
import uuid
import runtime_release as r

TESTS = {
 'maximo-api': ['test_guard','test_reliability_evidence','test_workorder_transport','test_workorder_recency','test_workorder_partial_poll','test_workorder_status_poll','test_workorder_lifecycle','test_workorder_age','test_asset_inventory','test_asset_references'],
 'mart-projector': ['test_mart','test_local_mart_projector','test_release_projector'],
 'cockpit-api': ['test_maintenance_investigation_performance','test_reliability_mart','test_work_order_timing','test_annual_work_orders','test_inventory_work_orders','test_kpi_readiness'],
 'cockpit-worker': ['test_kpi','test_pipeline_smoke'],
}

def main():
    production = r.snapshot()
    capture=json.loads((r.RELEASE/'capture.json').read_text())
    project='bsla-durability-rehearsal-'+uuid.uuid4().hex[:10]
    file=r.RELEASE/(project+'.json')
    model={'name':project,'services':{s:{'image':i,'pull_policy':'never',
        'network_mode':'none','read_only':True,'tmpfs':['/tmp:rw,noexec,nosuid,size=64m'],
        'cap_drop':['ALL'],'security_opt':['no-new-privileges:true'],
        'command':['python','-u','-c','import time; time.sleep(1800)'],
        'labels':{'bsla.rehearsal':project}} for s,i in r.lock()['images'].items()}}
    file.write_text(json.dumps(model,indent=2)+'\n')
    cmd=['docker','compose','-f',str(file)]
    result={'project':project,'stages':{},'tests':{},'rebuilt_sources':{}}
    def dc(*args):return r.run(*cmd,*args)
    def inspect_all(stage):
        state={}
        for s,i in r.lock()['images'].items():
            c=r.dock('inspect',project+'-'+s+'-1')[0]
            assert c['Image']==i and c['State']['Running'],s
            assert c['HostConfig']['NetworkMode']=='none' and c['HostConfig']['ReadonlyRootfs'],s
            assert not {'DATABASE_URL','MAXIMO_PASSWORD','MAXIMO_BASE_URL','RELIABILITY_MART_DATABASE_URL'} & {e.split('=',1)[0] for e in c['Config']['Env']},s
            ref='maximo-api' if s=='maximo-worker' else s
            for path in ['/app/src','/usr/local/lib/python3.12/site-packages/src']:
                assert r.manifest_files(r.source_files(c['Id'],path))==capture['sources'][ref]['files'],s
            state[s]={'id':c['Id'],'image':i,'source_match':True}
        result['stages'][stage]=state
        print(json.dumps({'stage':stage,'services':len(state),'source_match':True}),flush=True)
        return state
    try:
        dc('up','-d','--no-build','--pull','never')
        first=inspect_all('start')
        dc('restart','--timeout','5')
        restarted=inspect_all('restart')
        assert all(first[s]['id']==restarted[s]['id'] for s in first)
        dc('up','-d','--no-build','--pull','never','--force-recreate')
        recreated=inspect_all('recreate')
        assert all(first[s]['id']!=recreated[s]['id'] for s in first)
        for service, modules in TESTS.items():
            name=project+'-'+service+'-1'
            component='maximo-collector' if service in ('maximo-api','mart-projector') else 'reliability-cockpit'
            base='/tmp/'+component
            r.run('docker','exec',name,'mkdir','-p',base)
            # docker cp cannot write through a read-only container root into tmpfs.
            # Stream only test fixtures/contracts to the writable ephemeral /tmp.
            tests=r.run('tar','--exclude=__pycache__','--exclude=*.pyc','-C',str(r.ROOT/component),'-cf','-','tests')
            r.run('docker','exec','-i',name,'tar','-xf','-','-C',base,input=tests)
            contracts=r.run('tar','--exclude=.git','-C',str(r.ROOT),'-cf','-','reliability-data-contracts')
            r.run('docker','exec','-i',name,'tar','-xf','-','-C','/tmp',input=contracts)
            if service=='mart-projector':
                r.run('docker','exec','-i',name,'sh','-c','cat > '+base+'/tests/test_release_projector.py',
                      input=(r.ROOT/'deploy/compose/release_tests/test_projector_evidence.py').read_bytes())
            args=['docker','exec','-w',base,'-e','PYTHONPATH='+base+':'+base+'/tests',
                  '-e','RELIABILITY_CONTRACTS_ROOT=/tmp/reliability-data-contracts',name,
                  'python','-m','unittest',*modules]
            check=subprocess.run(args,capture_output=True)
            log=r.RELEASE/(project+'-test-'+service+'.log');log.write_bytes(check.stdout+check.stderr)
            result['tests'][service]={'passed':check.returncode==0,'log':log.name}
            print(json.dumps({'tests':service,'passed':check.returncode==0,'tail':(check.stdout+check.stderr).decode(errors='replace')[-400:]}),flush=True)
        rebuilt=json.loads((r.RELEASE/'rebuilt.json').read_text())
        for service,item in rebuilt.items():
            name=project+'-rebuilt-'+service
            r.run('docker','create','--name',name,'--network','none','--read-only',item['image'],
                  'python','-c','import time;time.sleep(30)')
            try:
                for path in ['/app/src','/usr/local/lib/python3.12/site-packages/src']:
                    assert r.manifest_files(r.source_files(name,path))==capture['sources'][service]['files'],service
                result['rebuilt_sources'][service]=True
            finally:r.run('docker','rm',name)
        after=r.snapshot()
        assert all(after[s]['Id']==production[s]['Id'] and after[s]['State']['StartedAt']==production[s]['State']['StartedAt'] for s in after)
        result['production_unchanged']=True
        result['passed']=all(x['passed'] for x in result['tests'].values())
    finally:
        # Only this unique hermetic project, no data volumes and no source workers.
        dc('down','--timeout','5')
        (r.RELEASE/(project+'-result.json')).write_text(json.dumps(result,indent=2)+'\n')
    if not result.get('passed'):raise SystemExit('Focused tests failed; inspect local logs')
    (r.RELEASE/'rehearsal.json').write_text(json.dumps(result,indent=2)+'\n')
    print('RESTART_RECREATE_REBUILD_VERIFIED_PRODUCTION_UNCHANGED')

if __name__=='__main__':main()
