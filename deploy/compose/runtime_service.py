#!/usr/bin/env python3
"""Restart/recreate one exact release service, retaining the original for rollback.

Unlike Compose service discovery, exact-name + immutable-ID checks never select
old rollback containers which still carry the same Compose service labels.
No environment values are printed/saved; no databases, volumes or images deleted.
"""
import argparse
import copy
import fcntl
import http.client
import json
from pathlib import Path
import socket
import time
from urllib.parse import quote
from urllib.request import urlopen
import uuid
import runtime_release as r

PORTS={'maximo-api':8002,'cockpit-api':8000}

class Docker(http.client.HTTPConnection):
    def __init__(self):super().__init__('localhost',timeout=75)
    def connect(self):
        self.sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout);self.sock.connect('/var/run/docker.sock')

def api(method,path,payload=None):
    client=Docker()
    try:
        client.request(method,path,json.dumps(payload).encode() if payload is not None else None,
                       {'Content-Type':'application/json'})
        response=client.getresponse();data=response.read()
        if response.status>=400:
            raise RuntimeError('Docker HTTP '+str(response.status)+'; response withheld')
        return json.loads(data) if data else None
    finally:client.close()

def inspect(identity):return api('GET','/containers/'+quote(identity,safe='')+'/json')
def maybe_inspect(identity):
    try:return inspect(identity)
    except RuntimeError as e:
        if str(e).startswith('Docker HTTP 404;'):return None
        raise

def save(state,path):
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(state,indent=2)+'\n');temp.replace(path)

def normalized_host(value):
    result=copy.deepcopy(value)
    # Docker normalizes its default nullable false on create. Never accept true.
    if result.get('OomKillDisable') is None:result['OomKillDisable']=False
    return result

def preserved_config(value):
    return {k:v for k,v in value.items() if k not in {'Image','Labels'}}

def clone_payload(current, transaction):
    result=copy.deepcopy(current['Config']);result['Image']=current['Image']
    result['Labels']=dict(result.get('Labels') or {})
    result['Labels'].update({'bsla.durability.transaction':transaction,'com.docker.compose.image':current['Image']})
    result['HostConfig']=copy.deepcopy(current['HostConfig'])
    endpoints={}
    for name,network in current['NetworkSettings']['Networks'].items():
        endpoint={'Aliases':[a for a in network.get('Aliases') or [] if a not in {current['Id'],current['Id'][:12]}]}
        for key in ('IPAMConfig','DriverOpts'):
            if network.get(key):endpoint[key]=copy.deepcopy(network[key])
        endpoints[name]=endpoint
    result['NetworkingConfig']={'EndpointsConfig':endpoints}
    return result

def healthy(service):
    if service not in PORTS:return
    for _ in range(25):
        try:
            with urlopen('http://127.0.0.1:'+str(PORTS[service])+'/health',timeout=2) as response:
                if response.status==200:return
        except Exception:pass
        time.sleep(1)
    raise RuntimeError('API health check failed: '+service)

def check_current(service):
    desired=r.lock();name=desired['project']+'-'+service+'-1';current=inspect(name)
    if current['Image']!=desired['images'][service] or not current['State']['Running']:
        raise RuntimeError('Expected pinned running service: '+service)
    labels=current['Config'].get('Labels') or {}
    if labels.get('com.docker.compose.project')!=desired['project'] or labels.get('com.docker.compose.service')!=service:
        raise RuntimeError('Wrong service labels')
    if set(current['NetworkSettings']['Networks'])!={desired['project']+'_platform'}:
        raise RuntimeError('Unexpected network; review before changing service')
    # The filtered list is JSON via Engine API, so multiple lines are unambiguous.
    filters=quote(json.dumps({'label':['com.docker.compose.project='+desired['project'],
                                      'com.docker.compose.service='+service]}),safe='')
    running=api('GET','/containers/json?filters='+filters)
    if {item['Id'] for item in running}!={current['Id']}:
        raise RuntimeError('Duplicate running service; no action taken')
    return current

def rollback(state,path):
    old=inspect(state['original_id'])
    if old['Image']!=state['image']:
        raise RuntimeError('Original identity changed; rollback refused')
    candidate=maybe_inspect(state.get('new_id') or state['candidate_name'])
    if candidate:
        if (candidate['Config'].get('Labels') or {}).get('bsla.durability.transaction')!=state['transaction'] or candidate['Image']!=state['image']:
            raise RuntimeError('Concurrent candidate; rollback refused')
        if candidate['State']['Running']:api('POST','/containers/'+candidate['Id']+'/stop?t=45')
        if candidate['Name'].lstrip('/')==state['original_name']:
            api('POST','/containers/'+candidate['Id']+'/rename?name='+quote(state['candidate_name'],safe=''))
    active=maybe_inspect(state['original_name'])
    if active and active['Id']!=old['Id']:
        raise RuntimeError('Concurrent active container; rollback refused')
    if old['Name'].lstrip('/')!=state['original_name']:
        api('POST','/containers/'+old['Id']+'/rename?name='+quote(state['original_name'],safe=''))
    if not inspect(old['Id'])['State']['Running']:api('POST','/containers/'+old['Id']+'/start')
    healthy(state['service']);state['status']='ROLLED_BACK';save(state,path)

def recreate(service):
    current=check_current(service);transaction=uuid.uuid4().hex
    name=current['Name'].lstrip('/');suffix=transaction[:12]
    path=r.RELEASE/('recreate-'+service+'-'+suffix+'.json')
    state={'service':service,'transaction':transaction,'original_id':current['Id'],
           'original_name':name,'image':current['Image'],
           'backup_name':name+'-before-durable-'+suffix,'candidate_name':name+'-durable-'+suffix,
           'config_sha256':r.json_digest(current['Config']),'status':'CREATE_PENDING'}
    save(state,path)
    try:
        new=api('POST','/containers/create?name='+quote(state['candidate_name'],safe=''),clone_payload(current,transaction))
        state['new_id']=new['Id'];state['status']='CREATED_NOT_STARTED';save(state,path)
        created=inspect(new['Id'])
        if preserved_config(created['Config'])!=preserved_config(current['Config']) or normalized_host(created['HostConfig'])!=normalized_host(current['HostConfig']):
            raise RuntimeError('Configuration not preserved; candidate never started')
        # Recheck identity/config immediately before stopping the original.
        fresh=check_current(service)
        if fresh['Id']!=current['Id'] or r.json_digest(fresh['Config'])!=state['config_sha256']:
            raise RuntimeError('Concurrent deployment; activation refused')
        api('POST','/containers/'+current['Id']+'/stop?t=45');state['status']='ORIGINAL_STOPPED';save(state,path)
        api('POST','/containers/'+current['Id']+'/rename?name='+quote(state['backup_name'],safe=''))
        api('POST','/containers/'+new['Id']+'/rename?name='+quote(name,safe=''))
        api('POST','/containers/'+new['Id']+'/start');state['status']='STARTED';save(state,path)
        healthy(service)
        if check_current(service)['Id']!=new['Id']:raise RuntimeError('Recreate identity mismatch')
        state['status']='ACTIVE_VERIFIED';save(state,path)
        print(json.dumps({'service':service,'status':state['status'],'image':state['image'],'rollback_state':str(path)}))
    except Exception:
        # Resolve an uncertain create by exact transaction/name before recovery.
        rollback(state,path)
        raise

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=['restart','recreate','rollback'])
    p.add_argument('target',help='Exact service name, or operation JSON for rollback')
    args=p.parse_args()
    r.lock()
    if not r.RELEASE.is_dir():raise SystemExit('Private release directory unavailable; preserve and provision the reviewed local release first')
    with (r.RELEASE/'operation.lock').open('a') as guard:
        fcntl.flock(guard,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if args.mode=='rollback':
            path=Path(args.target).resolve()
            if path.parent!=r.RELEASE or not path.name.startswith('recreate-'):raise SystemExit('Expected a recorded local recreate operation')
            state=json.loads(path.read_text())
            if state['status']!='ACTIVE_VERIFIED':raise SystemExit('Operation is not an active verified recreate')
            active=inspect(state['original_name'])
            if active['Id']!=state['new_id']:raise SystemExit('A newer deployment exists; rollback refused')
            rollback(state,path)
        else:
            if args.target not in r.lock()['images']:raise SystemExit('Service is not in the release lock')
            r.verify()
            if args.mode=='recreate':recreate(args.target)
            else:
                current=check_current(args.target)
                api('POST','/containers/'+current['Id']+'/restart?t=45');healthy(args.target)
                if check_current(args.target)['Id']!=current['Id']:raise SystemExit('Restart identity changed')
                print('RESTART_VERIFIED '+args.target+' '+current['Image'])

if __name__=='__main__':
    try:main()
    except RuntimeError as error:raise SystemExit(str(error))
