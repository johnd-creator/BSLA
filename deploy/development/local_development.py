"""Coordinated laptop-only source selection, through the existing nadi-dev lock.

Explicit reviewed refs, retained transition history, no checkout/reset or auto retry.
Normal edits in the selected worktree are expected and reported, not discarded.
"""
import hashlib
import json
import os
import re
import fcntl
import uuid
from contextlib import contextmanager
import ssl
import subprocess
import time
from pathlib import Path
from urllib.request import urlopen, Request, build_opener, HTTPRedirectHandler, HTTPSHandler, ProxyHandler
from urllib.error import HTTPError

DB = 'nadi_local_dev_01_test'
ROLE = 'nadi_local_dev_01'


def output(args, **kwargs):
    return subprocess.check_output([str(a) for a in args], text=True, timeout=30, **kwargs).strip()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def private(path):
    p = Path(path)
    st = p.lstat()
    if p.is_symlink() or not p.is_file() or st.st_uid != os.getuid() or st.st_mode & 0o077:
        raise RuntimeError('PRIVATE_LOCAL_STATE_REQUIRED')
    return json.loads(p.read_text())


def source(root, base, sha, clean=False):
    root = Path(root)
    if root.is_symlink() or root.resolve() != root or root.parent != base:
        raise RuntimeError('EXCLUSIVE_MANAGED_SOURCE_REQUIRED')
    if not re.fullmatch('[0-9a-f]{40}', sha or '') or output(['git', 'rev-parse', 'HEAD'], cwd=root) != sha:
        raise RuntimeError('EXACT_REVIEWED_SOURCE_REQUIRED')
    if clean and output(['git', 'status', '--porcelain'], cwd=root):
        raise RuntimeError('INITIAL_CLEAN_SOURCE_REQUIRED')
    web = root / 'reliability-cockpit/web'
    if any((web / p).exists() for p in ['.env', '.env.local', '.env.development', '.env.development.local']):
        raise RuntimeError('UNREVIEWED_DOTENV_DENIED')
    return root


def old_source(root, sha):
    if output(['git', 'rev-parse', 'HEAD'], cwd=root) != sha:
        raise RuntimeError('ROLLBACK_SOURCE_CHANGED')
    paths = output(['git', 'diff', '--name-only', 'HEAD'], cwd=root).splitlines()
    if output(['git', 'ls-files', '--others', '--exclude-standard'], cwd=root):
        raise RuntimeError('UNRELATED_ROLLBACK_EDITS')
    if paths:
        if paths != ['reliability-cockpit/web/next-env.d.ts']:
            raise RuntimeError('UNRELATED_ROLLBACK_EDITS')
        committed = subprocess.check_output(['git', 'show', sha+':'+paths[0]], cwd=root)
        actual = (Path(root) / paths[0]).read_bytes()
        if actual != committed.replace(b'./.next/types/routes.d.ts', b'./.next-primary-dev/types/routes.d.ts'):
            raise RuntimeError('UNRELATED_GENERATED_EDIT')
    return digest(Path(root) / 'reliability-cockpit/web/next-env.d.ts')


class SealedSource:
    """Owner-private source-only archive, approved by its exact manifest SHA256.

    No runtime state is restored. Independent recovery Git objects stay in a private
    repository; no snapshot commit/object is written into the application repository.
    """
    @staticmethod
    def path(root, name):
        from pathlib import PurePosixPath
        p = PurePosixPath(name)
        if (not name or p.is_absolute() or str(p) != name or any(x in {'.','..','.git','.nadi-dev'} for x in p.parts)
                or any(x == '.env' or x.startswith('.env.') and not x.endswith(('.example','.sample')) for x in p.parts)
                or p.suffix in {'.dump','.key','.pem'}):
            raise RuntimeError('PRESERVATION_PATH_DENIED')
        target = Path(root) / name
        for part in [target, *target.parents]:
            if part == Path(root).parent: break
            if part.is_symlink(): raise RuntimeError('PRESERVATION_SYMLINK_DENIED')
        return target

    @staticmethod
    def private_root(root):
        root = Path(root)
        if root.resolve() != root or root.is_symlink() or not root.is_dir():
            raise RuntimeError('PRIVATE_PRESERVATION_ROOT_REQUIRED')
        st = root.stat()
        if st.st_uid != os.getuid() or st.st_mode & 0o077:
            raise RuntimeError('PRIVATE_PRESERVATION_ROOT_REQUIRED')
        return root

    @staticmethod
    def git(root, *args, **kwargs):
        return subprocess.check_output(['git','-c','core.hooksPath=/dev/null',*args],cwd=root,timeout=30,**kwargs)

    @classmethod
    def scan(cls, root):
        root = Path(root)
        if root.resolve() != root or root.is_symlink() or root.stat().st_uid != os.getuid():
            raise RuntimeError('PRESERVATION_SOURCE_OWNER_REQUIRED')
        git = lambda *a: cls.git(root,*a).decode().strip()
        if cls.git(root,'ls-files','--unmerged'):
            raise RuntimeError('UNRESOLVED_INDEX_DENIED')
        names = cls.git(root,'ls-files','-z','--cached','--others','--exclude-standard').split(b'\0')
        files = {}
        for raw in sorted(set(names)):
            if not raw: continue
            name = raw.decode(); path = cls.path(root,name)
            if not path.exists(): continue  # Tracked deletions are represented by absence.
            before = path.lstat()
            if not path.is_file() or before.st_uid != os.getuid() or before.st_nlink != 1:
                raise RuntimeError('PRESERVATION_REGULAR_OWNED_FILE_REQUIRED')
            data = path.read_bytes(); after = path.lstat()
            if (before.st_ino,before.st_size,before.st_mtime_ns,before.st_mode) != (after.st_ino,after.st_size,after.st_mtime_ns,after.st_mode):
                raise RuntimeError('PRESERVATION_CONCURRENT_CHANGE')
            mode = before.st_mode & 0o777
            if mode & 0o022 or before.st_mode & 0o7000:
                raise RuntimeError('PRESERVATION_UNSAFE_FILE_MODE')
            files[name] = {'sha256':hashlib.sha256(data).hexdigest(),'size':len(data),'mode':mode,
                           'blob':hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()}
        # Even ignored frontend dotenv cannot become an implicit runtime dependency.
        for name in ['.env','.env.local','.env.development','.env.development.local']:
            if (root/'reliability-cockpit/web'/name).exists(): raise RuntimeError('UNREVIEWED_DOTENV_DENIED')
        index = cls.git(root,'ls-files','--stage','-z')
        return {'root':str(root),'head':git('rev-parse','HEAD'),'branch':git('symbolic-ref','-q','--short','HEAD') if cls.git_branch(root) else None,
                'common_dir':git('rev-parse','--path-format=absolute','--git-common-dir'),
                'origin':git('remote','get-url','origin'),'uid':os.getuid(),'files':files,
                'index_sha256':hashlib.sha256(index).hexdigest(),
                'status':cls.git(root,'status','--porcelain=v1','--untracked-files=all','-z').hex()}

    @classmethod
    def git_branch(cls, root):
        return subprocess.run(['git','symbolic-ref','-q','--short','HEAD'],cwd=root,capture_output=True,timeout=10).returncode == 0

    @classmethod
    def seal(cls, root, destination, runtime):
        root = Path(root); dest = Path(destination)
        if dest.resolve() != dest or root == dest or root in dest.parents:
            raise RuntimeError('PRESERVATION_OUTSIDE_SOURCE_REQUIRED')
        before = cls.scan(root)
        dest.mkdir(mode=0o700)  # Exclusive, never replace an existing archive.
        (dest/'objects').mkdir(mode=0o700)
        for name, item in before['files'].items():
            data = cls.path(root,name).read_bytes()
            if hashlib.sha256(data).hexdigest() != item['sha256']: raise RuntimeError('PRESERVATION_CONCURRENT_CHANGE')
            target = dest/'objects'/item['sha256']
            if not target.exists():
                fd = os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
                with os.fdopen(fd,'wb') as f: f.write(data)
        if cls.scan(root) != before: raise RuntimeError('PRESERVATION_CONCURRENT_CHANGE')
        value = {'version':1,'source':before,'runtime':runtime,'created':time.time()}
        path = dest/'manifest.json'; fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'w') as f: json.dump(value,f,sort_keys=True,separators=(',',':'))
        return {'manifest':str(path),'digest':digest(path)}

    @staticmethod
    def approved_json(path, expected, code):
        import stat
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
        with os.fdopen(fd,'rb') as f:
            st=os.fstat(f.fileno())
            if not stat.S_ISREG(st.st_mode) or st.st_uid!=os.getuid() or st.st_mode&0o077 or st.st_nlink!=1:
                raise RuntimeError('PRIVATE_PRESERVATION_OBJECT_REQUIRED')
            data=f.read(16*1024*1024+1)
            if len(data)>16*1024*1024 or hashlib.sha256(data).hexdigest()!=expected:
                raise RuntimeError(code)
        return json.loads(data)

    @classmethod
    def verify(cls, approval, original=False):
        path = Path(approval['manifest']); cls.private_root(path.parent); cls.private_root(path.parent/'objects')
        value = cls.approved_json(path,approval['digest'],'PRESERVATION_APPROVAL_MISMATCH')
        if value.get('version') != 1 or value['source']['uid'] != os.getuid(): raise RuntimeError('PRESERVATION_IDENTITY_MISMATCH')
        source = value['source']
        for name,item in source['files'].items():
            cls.path(Path(source['root']),name)
            if not re.fullmatch('[0-9a-f]{64}',item['sha256']): raise RuntimeError('PRESERVATION_HASH_INVALID')
            data_path=path.parent/'objects'/item['sha256']; st=data_path.lstat()
            if data_path.is_symlink() or not data_path.is_file() or st.st_uid!=os.getuid() or st.st_mode&0o077 or st.st_nlink!=1:
                raise RuntimeError('PRIVATE_PRESERVATION_OBJECT_REQUIRED')
            data=data_path.read_bytes()
            if (len(data)!=item['size'] or hashlib.sha256(data).hexdigest()!=item['sha256'] or
                    hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()!=item['blob']):
                raise RuntimeError('PRESERVATION_OBJECT_CORRUPT')
        if original and cls.scan(source['root']) != source: raise RuntimeError('PRESERVATION_SOURCE_CHANGED')
        return value

    @classmethod
    def prepare(cls, approval, root, base):
        value=cls.verify(approval,original=True); root=Path(root); base=Path(base)
        if root.parent!=base or root.resolve()!=root or root.exists(): raise RuntimeError('NEW_MANAGED_RECOVERY_ROOT_REQUIRED')
        root.mkdir(mode=0o700)
        cls.git(root,'init','--quiet')
        os.chmod(root/'.git',0o700)
        cls.git(root,'config','core.hooksPath','/dev/null')
        cls.git(root,'remote','add','origin',value['source']['origin'])
        cls.git(root,'config','remote.origin.pushurl','disabled://nadi-private-recovery')
        # Immutable base objects are read through an exact local alternate. New private
        # snapshot objects are written only inside this owner-private recovery repo.
        objects=Path(value['source']['common_dir'])/'objects'
        (root/'.git/objects/info/alternates').write_text(str(objects)+'\n')
        cls.git(root,'cat-file','-e',value['source']['head']+'^{commit}')
        for name,item in value['source']['files'].items():
            data=(Path(approval['manifest']).parent/'objects'/item['sha256']).read_bytes()
            path=cls.path(root,name); path.parent.mkdir(parents=True,exist_ok=True)
            fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,item['mode'])
            with os.fdopen(fd,'wb') as f: f.write(data)
            os.chmod(path,item['mode'])
            blob=cls.git(root,'hash-object','-w','--stdin',input=data).decode().strip()
            if blob!=item['blob']: raise RuntimeError('RECOVERY_BLOB_MISMATCH')
            cls.git(root,'update-index','--add','--cacheinfo',('100755' if item['mode']&0o111 else '100644')+','+blob+','+name)
        tree=cls.git(root,'write-tree').decode().strip()
        env=dict(os.environ,GIT_AUTHOR_NAME='NADI private recovery',GIT_AUTHOR_EMAIL='recovery@localhost',
                 GIT_COMMITTER_NAME='NADI private recovery',GIT_COMMITTER_EMAIL='recovery@localhost')
        sha=cls.git(root,'commit-tree',tree,'-p',value['source']['head'],input=('Private recovery for '+approval['digest']+'\n').encode(),env=env).decode().strip()
        cls.git(root,'update-ref','HEAD',sha)
        receipt=dict(approval,root=str(root),sha=sha,tree=tree)
        cls.verify_recovery(receipt)
        if cls.scan(value['source']['root'])!=value['source']: raise RuntimeError('PRESERVATION_SOURCE_CHANGED')
        return receipt

    @classmethod
    def verify_recovery(cls, receipt):
        value=cls.verify(receipt); root=cls.private_root(receipt['root']); actual=cls.scan(root)
        expected=value['source']
        cls.private_root(root/'.git')
        if actual['common_dir']!=str(root/'.git'):
            raise RuntimeError('RECOVERY_REPOSITORY_MISMATCH')
        if cls.git(root,'config','remote.origin.pushurl').decode().strip()!='disabled://nadi-private-recovery':
            raise RuntimeError('PRIVATE_RECOVERY_PUSH_DISABLED_REQUIRED')
        if (actual['files']!=expected['files'] or actual['head']!=receipt['sha'] or actual['origin']!=expected['origin'] or
                actual['status'] or cls.git(root,'rev-parse','HEAD^{tree}').decode().strip()!=receipt['tree'] or
                cls.git(root,'rev-parse','HEAD^').decode().strip()!=expected['head']):
            raise RuntimeError('SEALED_RECOVERY_SOURCE_CHANGED')
        if (root/'.git/objects/info/alternates').read_text()!=str(Path(expected['common_dir'])/'objects')+'\n':
            raise RuntimeError('RECOVERY_REPOSITORY_MISMATCH')
        return value


def node_pin(state):
    pin = private(state / 'frontend-runtime.json')
    node = Path(pin['node_path'])
    if (pin['node_version'] != '22.23.1' or digest(node) != pin['node_sha256'] or
            output([node, '-p', 'process.versions.node']) != '22.23.1'):
        raise RuntimeError('VERIFIED_NODE22_REQUIRED')
    for path, expected in pin['libnode_sha256'].items():
        if digest(path) != expected:
            raise RuntimeError('NODE_LIBRARY_CHANGED')
    return str(node)


class LocalDevelopment:
    def __init__(self, control):
        self.c = control
        self.state = control.STATE / 'local-dev-01'
        self.preservation = None
        self.acceptance_session_file = None

    def save(self, name, value):
        self.c.write_private(self.state / name, json.dumps(value, indent=2))

    def unit(self, name):
        fields = 'MainPID,WorkingDirectory,ActiveState,ControlGroup,InvocationID,NRestarts'
        data = dict(line.split('=', 1) for line in output(['systemctl', '--user', 'show', name, '-p', fields]).splitlines())
        pid = data.get('MainPID', '0')
        if data.get('ActiveState') != 'active' or pid == '0':
            raise RuntimeError('OWNED_DEVELOPMENT_UNIT_REQUIRED')
        data['start_ticks'] = self.identity(int(pid))['start_ticks']
        return data

    def identity(self, pid):
        root = Path('/proc') / str(pid)
        stat = (root / 'stat').read_text().rsplit(') ', 1)[1].split()
        return {'pid': pid, 'ppid': int(stat[1]), 'start_ticks': int(stat[19]),
                'exe': os.readlink(root / 'exe'), 'cwd': os.readlink(root / 'cwd'),
                'cgroup': (root / 'cgroup').read_text().strip().split('::', 1)[1]}

    def owners(self, unit, cwd, port):
        value = self.unit(unit)
        if value['WorkingDirectory'] != str(cwd):
            raise RuntimeError('UNEXPECTED_DEVELOPMENT_CWD')
        rows = output(['ss', '-H', '-ltnpe', 'sport = :'+str(port)]).splitlines()
        if not rows:
            raise RuntimeError('EXPECTED_LISTENER_MISSING')
        identities = {}
        for row in rows:
            if row.split()[3] not in ['127.0.0.1:'+str(port), '[::1]:'+str(port)]:
                raise RuntimeError('NON_LOOPBACK_LISTENER')
            pids = re.findall(r'pid=(\d+)', row)
            if not pids:
                raise RuntimeError('UNVERIFIED_LISTENER_OWNER')
            for pid in pids:
                ident = self.identity(int(pid))
                if ident['cgroup'] != value['ControlGroup'] or ident['cwd'] != str(cwd):
                    raise RuntimeError('UNAUTHORIZED_LISTENER_OWNER')
                # Repeat identity after observation to reject PID reuse while collecting.
                if self.identity(int(pid)) != ident:
                    raise RuntimeError('LISTENER_IDENTITY_CHANGED')
                identities[pid] = ident
        inodes = re.findall(r'ino:(\d+)', '\n'.join(rows))
        if len(inodes) != len(rows):
            raise RuntimeError('LISTENER_INODE_UNVERIFIED')
        if self.unit(unit) != value:
            raise RuntimeError('DEVELOPMENT_UNIT_CHANGED_DURING_OBSERVATION')
        return {'unit': value, 'listeners': identities, 'socket_inodes': inodes}

    def probe(self, url, cookie=None):
        # Fixed local targets, no redirects, bounded bytes, trusted CA; never source I/O.
        allowed = {self.c.ORIGIN+'/', self.c.ORIGIN+'/api/development/health',
                   self.c.ORIGIN+'/api/cockpit/health', self.c.ORIGIN+'/api/engineering-qa/session',
                   'http://127.0.0.1:13036/development/status', 'http://127.0.0.1:13036/health/ready',
                   'http://127.0.0.1:8000/health'}
        if self.c.ORIGIN != 'https://localhost:3000' or url not in allowed:
            raise RuntimeError('READINESS_TARGET_DENIED')
        if cookie is not None and (not url.startswith(self.c.ORIGIN+'/') or
                not re.fullmatch(r'__Host-nadi_session=[A-Za-z0-9_-]{40,128}',cookie)):
            raise RuntimeError('READINESS_COOKIE_DENIED')
        class NoRedirect(HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None
        context=ssl.create_default_context(cafile=str(self.c.STATE/'localhost.pem'))
        opener=build_opener(ProxyHandler({}),NoRedirect(),HTTPSHandler(context=context))
        request=Request(url,headers={'Cookie':cookie} if cookie else {})
        try:
            response=opener.open(request,timeout=10)
        except HTTPError as error:
            response=error
        with response:
            body=response.read(1048577)
            if len(body)>1048576:
                raise RuntimeError('READINESS_BODY_LIMIT')
            data=None
            if 'application/json' in response.headers.get('Content-Type','').lower():
                try:data=json.loads(body)
                except (ValueError,UnicodeError):raise RuntimeError('READINESS_INVALID_JSON') from None
            return {'status':response.status,'location':response.headers.get('Location'),
                    'cache_control':response.headers.get('Cache-Control',''),'data':data}

    def request(self, url):
        result=self.probe(url)
        if result['status']!=200 or not isinstance(result['data'],dict):
            raise RuntimeError('READINESS_RESPONSE_DENIED')
        return result['data']

    def auth_readiness(self, session_file=None):
        page=self.probe(self.c.ORIGIN+'/')
        if page['status']!=307 or page['location']!='/login?returnTo=%2F' or 'no-store' not in page['cache_control']:
            raise RuntimeError('ANONYMOUS_LOGIN_BOUNDARY_FAILED')
        denied=self.probe(self.c.ORIGIN+'/api/cockpit/health')
        if denied['status']!=401 or denied['data']!={'detail':{'code':'AUTHENTICATION_REQUIRED'}} or 'no-store' not in denied['cache_control']:
            raise RuntimeError('ANONYMOUS_API_BOUNDARY_FAILED')
        invalid=self.probe(self.c.ORIGIN+'/api/engineering-qa/session','__Host-nadi_session='+'0'*43)
        if invalid['status']!=401 or invalid['data']!={'detail':{'code':'SESSION_INVALID'}}:
            raise RuntimeError('INVALID_SESSION_ACCEPTED_OR_UNVERIFIED')
        state='NOT_PROBED_NO_SESSION'
        if session_file is not None:
            path=Path(session_file)
            if path.lstat().st_size>4096:
                raise RuntimeError('PRIVATE_SESSION_FILE_INVALID')
            value=private(path)
            if set(value)!={'cookie'} or not isinstance(value['cookie'],str):
                raise RuntimeError('PRIVATE_SESSION_FILE_INVALID')
            cookie=value['cookie']
            who=self.probe(self.c.ORIGIN+'/api/engineering-qa/session',cookie)
            data=who['data']
            if (who['status']!=200 or not isinstance(data,dict) or
                    not re.fullmatch(r'local:[A-Za-z0-9-]{1,150}',str(data.get('subject',''))) or
                    not isinstance(data.get('roles'),list) or not data['roles'] or
                    any(r not in ['ADMIN','AUTHOR','REVIEWER'] for r in data['roles']) or
                    not isinstance(data.get('asset_ids'),list) or len(data['asset_ids'])>1000 or
                    any(not isinstance(v,str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,200}',v) for v in data['asset_ids'])):
                raise RuntimeError('AUTHORIZED_SESSION_INVALID_OR_EXPIRED')
            actual=self.probe(self.c.ORIGIN+'/api/cockpit/health',cookie)
            if actual['status']!=200 or actual['data']!={'status':'ok'}:
                raise RuntimeError('AUTHORIZED_GATEWAY_FAILED')
            state='VERIFIED'
        return {'anonymous_pages':'VERIFIED_LOGIN_REDIRECT','anonymous_api':'VERIFIED_DENIED',
                'invalid_session':'VERIFIED_DENIED','authorized_session':state}

    def release(self):
        record = private(self.c.STATE / 'local-development-release.json')
        if (set(record['files']) != {'nadi-dev.py','local_development.py','local_fixture.py','frontend_preview.py'} or
                not re.fullmatch('[0-9a-f]{40}',record.get('source_sha',''))):
            raise RuntimeError('UNREVIEWED_LOCAL_CONTROLLER_RELEASE')
        for name, expected in record['files'].items():
            if digest(Path(__file__).with_name(name)) != expected:
                raise RuntimeError('LOCAL_CONTROLLER_RELEASE_CHANGED')
        return record['source_sha']

    def replace(self, name, value):
        # Exclusive temporary file plus atomic pointer replace. Immutable events use save().
        temporary = name + '.' + uuid.uuid4().hex + '.tmp'
        self.save(temporary, value)
        os.replace(self.state / temporary, self.state / name)

    @contextmanager
    def transaction(self):
        # CLI also holds the existing frontend-lifecycle.lock, shared with older commands.
        # This nested lock protects direct companion calls and deterministic simulations.
        self.state.mkdir(mode=0o700, exist_ok=True)
        info = self.state.lstat()
        if self.state.is_symlink() or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise RuntimeError('PRIVATE_LOCAL_STATE_REQUIRED')
        fd = os.open(self.state/'selection.lock', os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW, 0o600)
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:
                raise RuntimeError('DEVELOPMENT_LIFECYCLE_BUSY') from None
            yield
        finally:
            os.close(fd)

    def resolve(self, root, ref):
        if not ref or ref.startswith('-') or not re.fullmatch(r'[A-Za-z0-9_./-]+', ref):
            raise RuntimeError('EXPLICIT_REVIEWED_REF_REQUIRED')
        root = Path(root)
        # Validate path before using it as a git execution directory.
        if root.is_symlink() or root.resolve() != root or root.parent != self.c.BASE:
            raise RuntimeError('EXCLUSIVE_MANAGED_SOURCE_REQUIRED')
        sha = output(['git','rev-parse','--verify',ref+'^{commit}'],cwd=root)
        root = source(root,self.c.BASE,sha,clean=True)
        self.repository(root)
        return root, sha

    def repository(self, root):
        def git(*args, cwd):
            return output(['git',*args],cwd=cwd)
        common = ['rev-parse','--path-format=absolute','--git-common-dir']
        if git(*common,cwd=root) != git(*common,cwd=self.c.ROOT):
            raise RuntimeError('UNRELATED_SOURCE_REPOSITORY')
        remote = git('remote','get-url','origin',cwd=root)
        if remote not in {'https://github.com/johnd-creator/reliability-knowledge-starter.git',
                          'git@github.com:johnd-creator/reliability-knowledge-starter.git',
                          'https://github.com/johnd-creator/reliability-knowledge-starter'}:
            raise RuntimeError('UNTRUSTED_SOURCE_REPOSITORY')

    def fixture_contract(self, previous, root, sha):
        # Conservative schema/bootstrap/auth adapter compatibility, not inferred from SHA equality.
        # Changed persistence/dependencies require separate fixture compatibility preparation.
        paths = ('reliability-cockpit/application-migrations',
                 'reliability-cockpit/src/repositories',
                 'reliability-cockpit/src/services/local_authentication.py',
                 'reliability-cockpit/src/services/application_identity.py',
                 'reliability-cockpit/src/api/engineering_qa.py',
                 'reliability-cockpit/pyproject.toml',
                 'reliability-cockpit/tests/qa/live_server.py',
                 'reliability-cockpit/tests/test_condition_evidence.py',
                 'reliability-cockpit/tests/test_asset_af_mapping_admin.py',
                 'pi-collector/tests/fixtures/condition_source.py')
        hashes = {}
        for path in paths:
            a = output(['git','rev-parse',previous['sha']+':'+path],cwd=previous['root'])
            b = output(['git','rev-parse',sha+':'+path],cwd=root)
            if a != b:
                raise RuntimeError('FIXTURE_CONTRACT_CHANGE_REQUIRES_SEPARATE_APPROVAL: '+path)
            hashes[path] = b
        # The existing comparator validates required web/API contract files and dependencies.
        # Both selected applications must come from the same explicitly reviewed commit.
        return hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()

    def fixture_probe(self, value):
        # Read-only validation through the selected source, never prepare()/migration helpers.
        result = output(['/usr/bin/env','-i',*self.environment(Path(value['root'])),
                         'NADI_LOCAL_DEV_CONFIG='+value['config_path'],
                         str(self.c.STATE/'python-runtime/bin/python'),
                         str(Path(__file__).with_name('local_fixture.py')),'--check'])
        return json.loads(result)

    def preservation_identity(self, value):
        config_path = value.get('config_path',str(self.state/'config.json'))
        config = private(config_path)
        return {'root':value['root'],'sha':value['sha'],'workflow_sha':value['workflow_sha'],
                'controller_sha':self.release(),'config_path':config_path,'config_hash':digest(config_path),
                'accounts_hash':digest(config['accounts_file']),
                'before':{'web':self.owners(self.c.UNITS[1],Path(value['root'])/'reliability-cockpit/web',3000),
                          'api':self.owners(self.c.UNITS[0],Path(value['root'])/'reliability-cockpit',13036)}}

    def preserve(self, destination):
        with self.transaction():
            value=self.active_value()
            root=source(value['root'],self.c.BASE,value['sha']); self.repository(root)
            self.readiness(value)
            identity=self.preservation_identity(value)
            approval=SealedSource.seal(root,destination,identity)
            if self.active_value()!=value or self.preservation_identity(value)!=identity:
                raise RuntimeError('PRESERVATION_RUNTIME_CHANGED')
            return approval

    def prepare_preserved(self, approval, root):
        with self.transaction():
            sealed=SealedSource.verify(approval,original=True)
            if (sealed['runtime']!=self.preservation_identity(self.active_value()) or
                    sealed['source']['root']!=sealed['runtime']['root'] or sealed['source']['head']!=sealed['runtime']['sha']):
                raise RuntimeError('PRESERVATION_RUNTIME_CHANGED')
            receipt=SealedSource.prepare(approval,root,self.c.BASE)
            identity=sealed['runtime']
            config=private(identity['config_path'])
            if config['source_root']!=identity['root'] or config['workflow_sha']!=identity['workflow_sha']:
                raise RuntimeError('ACTIVE_FIXTURE_SOURCE_MISMATCH')
            config=dict(config,source_root=str(root))
            config_name='sealed-recovery-config-'+receipt['sha']+'.json'
            self.save(config_name,config)
            receipt['config_path']=str(self.state/config_name)
            receipt['config_hash']=digest(self.state/config_name)
            token='recovery-source-'+uuid.uuid4().hex+'.json'
            self.save(token,receipt)
            return {'receipt':str(self.state/token),'receipt_sha256':digest(self.state/token),**receipt}

    def preserved_previous(self):
        request=self.preservation
        receipt=SealedSource.approved_json(request['receipt'],request['receipt_sha256'],'RECOVERY_RECEIPT_APPROVAL_CHANGED')
        sealed=SealedSource.verify_recovery(receipt)
        SealedSource.verify(receipt,original=True)
        value=self.active_value(); identity=self.preservation_identity(value)
        if (sealed['runtime']!=identity or sealed['source']['root']!=identity['root'] or sealed['source']['head']!=identity['sha']):
            raise RuntimeError('PRESERVATION_RUNTIME_CHANGED')
        self.readiness(value)
        root=Path(receipt['root'])
        source(root,self.c.BASE,receipt['sha'],clean=True)
        config=private(identity['config_path'])
        if config['source_root']!=value['root'] or config['workflow_sha']!=value['workflow_sha']:
            raise RuntimeError('ACTIVE_FIXTURE_SOURCE_MISMATCH')
        config=dict(config,source_root=str(root))
        path=Path(receipt['config_path'])
        if path.parent!=self.state or digest(path)!=receipt['config_hash'] or private(path)!=config:
            raise RuntimeError('RECOVERY_CONFIG_CHANGED')
        dependency=root/'reliability-cockpit/web/node_modules/.package-lock.json'
        if not dependency.is_file() or dependency.is_symlink():
            raise RuntimeError('REVIEWED_RECOVERY_DEPENDENCIES_REQUIRED')
        result=dict(value,recovery_dependency_hash=digest(dependency),root=str(root),sha=receipt['sha'],backend_sha=receipt['sha'],
                    ref=receipt['sha'],config_path=str(path),sealed_source=receipt,
                    original_source={'root':value['root'],'sha':value['sha'],'manifest_digest':receipt['digest']},
                    before=identity['before'])
        result.pop('expected_web',None);result.pop('expected_api_parent',None)
        return result

    def previous(self):
        if self.preservation:
            return self.preserved_previous()
        value = self.active_value()
        root = source(value['root'],self.c.BASE,value['sha'])
        if value.get('sealed_source'):
            SealedSource.verify_recovery(value['sealed_source'])
        else:self.repository(root)
        generated = old_source(root,value['sha'])
        data = self.readiness(value)
        if data.get('engineering_data') != 'SYNTHETIC_FIXTURES':
            raise RuntimeError('UNVERIFIED_APPLICATION_PROVENANCE')
        config_path = value.get('config_path',str(self.state/'config.json'))
        config = private(config_path)
        if config['source_root'] != str(root):
            raise RuntimeError('ACTIVE_FIXTURE_SOURCE_MISMATCH')
        return dict(value,config_path=config_path,generated_hash=generated,
                    before={'web':self.owners(self.c.UNITS[1],root/'reliability-cockpit/web',3000),
                            'api':self.owners(self.c.UNITS[0],root/'reliability-cockpit',13036)})

    def preflight(self, root, ref):
        release = self.release()
        root, sha = self.resolve(root,ref)
        self.factual_read_environment(root,required=getattr(self,'require_factual_read',False))
        if self.c.active(self.c.LEGACY_WEB):
            raise RuntimeError('COMPETING_FRONTEND')
        previous = self.previous()
        contract = self.fixture_contract(previous,root,sha)
        # Same exact source supplies frontend and API; still verify the approved contract surface exists.
        import importlib.util
        spec = importlib.util.spec_from_file_location('local_pair_compatibility',Path(__file__).with_name('frontend_preview.py'))
        module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        pair = module.compatible(root,root,sha,sha)
        if previous.get('sealed_source'):
            module.compatible(root,Path(previous['root']),sha,previous['sha'])
        db = self.c.db()
        if not db or not db['State']['Running'] or db['NetworkSettings']['Ports'].get('5432/tcp') != [{'HostIp':'127.0.0.1','HostPort':'15443'}]:
            raise RuntimeError('EXISTING_DEVELOPMENT_POSTGRES_REQUIRED')
        pin = node_pin(self.c.STATE)
        web = root/'reliability-cockpit/web'
        if not (web/'node_modules/next/dist/bin/next').is_file():
            raise RuntimeError('LOCKED_DEPENDENCIES_REQUIRED')
        # Installed package identity/lock, not a global npm install or automatic dependency update.
        if digest(web/'node_modules/.package-lock.json') != digest(Path(previous['root'])/'reliability-cockpit/web/node_modules/.package-lock.json'):
            raise RuntimeError('DEPENDENCY_INSTALL_CHANGED')
        for name in ['localhost.pem','localhost.key']:
            path = self.c.STATE/name; st = path.lstat()
            if path.is_symlink() or st.st_uid != os.getuid() or st.st_mode & 0o077:
                raise RuntimeError('PRIVATE_HTTPS_REQUIRED')
        output(['openssl','x509','-in',self.c.STATE/'localhost.pem','-checkend','3600','-noout'])
        output(['openssl','x509','-in',self.c.STATE/'localhost.pem','-checkhost','localhost','-noout'])
        value = {'root':str(root),'sha':sha,'backend_sha':sha,'ref':ref,'node':pin,
                 'previous':previous,'db_container_id':db['Id'],'workflow_sha':release,
                 'fixture_contract':contract,'pair_contract':pair,
                 'config_path':previous['config_path'],'factual_read_required':bool(getattr(self,'require_factual_read',False))}
        value['fixture'] = self.fixture_probe(value)
        value['config_hash'] = digest(previous['config_path'])
        value['accounts_hash'] = digest(private(previous['config_path'])['accounts_file'])
        return value

    def backup(self, value, token):
        target = self.state/('backup-'+token+'.dump')
        with target.open('xb') as stream:
            os.chmod(target,0o600)
            subprocess.run(['docker','exec',self.c.NAME,'pg_dump','-U','nadi_dev_fixture','-d',DB,'-Fc'],
                           stdout=stream,check=True,timeout=60)
        value['backup'] = str(target)
        value['backup_sha256'] = digest(target)
        value['backup_created'] = time.time()
        for unit,name in [(self.c.UNITS[1],'web.service'),(self.c.UNITS[0],'api.service')]:
            self.c.write_private(self.state/(token+'-'+name),output(['systemctl','--user','cat',unit]))
        self.validate_backup(value)

    def validate_backup(self, value):
        path = Path(value['backup']); st = path.lstat()
        if (path.parent != self.state or path.is_symlink() or st.st_uid != os.getuid() or
                st.st_mode & 0o077 or st.st_size < 1000 or not 0 <= time.time()-value['backup_created'] <= 3600 or
                digest(path) != value['backup_sha256']):
            raise RuntimeError('FRESH_PRIVATE_BACKUP_REQUIRED')
        for args in [['--list'],['--file=/dev/null']]:
            with path.open('rb') as stream:
                result = subprocess.run(['docker','exec','-i',self.c.NAME,'pg_restore',*args],
                                        stdin=stream,capture_output=True,timeout=30)
            if result.returncode or (args == ['--list'] and
                    any(name not in result.stdout for name in [b'nadi_human_record',b'nadi_application_session',b'nadi_application_migration'])):
                raise RuntimeError('BACKUP_UNREADABLE')

    def validate_recovery(self, value):
        self.release()
        previous = value['previous']
        root = source(previous['root'],self.c.BASE,previous['sha'])
        if previous.get('sealed_source'):
            SealedSource.verify_recovery(previous['sealed_source'])
            if digest(root/'reliability-cockpit/web/node_modules/.package-lock.json')!=previous['recovery_dependency_hash']:
                raise RuntimeError('RECOVERY_DEPENDENCY_CHANGED')
        else:self.repository(root)
        if not previous.get('sealed_source') and old_source(root,previous['sha']) != previous['generated_hash']:
            raise RuntimeError('ROLLBACK_SOURCE_CHANGED')
        if (digest(previous['config_path']) != value['config_hash'] or
                digest(private(previous['config_path'])['accounts_file']) != value['accounts_hash']):
            raise RuntimeError('ROLLBACK_CONFIG_CHANGED')
        db = self.c.db()
        if not db or not db['State']['Running'] or db['Id'] != value['db_container_id']:
            raise RuntimeError('ROLLBACK_FIXTURE_CONTAINER_CHANGED')
        node_pin(self.c.STATE)
        self.validate_backup(value)
        probe = self.fixture_probe(previous)
        if probe != value['fixture']:
            raise RuntimeError('FIXTURE_SCHEMA_OR_LEDGER_CHANGED')

    def environment(self, root):
        cockpit=Path(root)/'reliability-cockpit'
        return ['PATH='+str(self.c.STATE/'frontend-node-bin')+':/usr/bin:/bin','HOME='+str(Path.home()),'LANG=C.UTF-8',
            'PYTHONPATH='+':'.join(map(str,[cockpit,cockpit/'tests',cockpit/'tests/qa',Path(__file__).parent])),
            'PYTHONUNBUFFERED=1','NADI_LOCAL_DEV_ACK='+DB,'NADI_LOCAL_DEV_CONFIG='+str(self.state/'config.json')]

    def start(self, unit, root, command, extra, memory):
        self.c.run(['systemd-run','--user','--collect','--unit='+unit,'--service-type=exec','--working-directory='+str(root),
            '--property=Restart=no','--property=MemoryMax='+memory,'--property=CPUQuota=200%',
            '--property=TasksMax=256','--property=UMask=0077','--property=KillMode=control-group','--property=TimeoutStopSec=20',
            '/usr/bin/env','-i',*self.environment(Path(root).parents[0] if Path(root).name=='reliability-cockpit' else Path(root).parents[1]),*extra,*command])

    def factual_read_environment(self, root, required=False):
        # Stable application-owned state, outside all source/worktree/DB restores.
        # Presence does not issue a grant; only the separately approved private CLI does.
        import stat
        if not required:return []
        # root has already passed the controller's exact reviewed source seal.
        schema=Path(root)/'reliability-cockpit/src/services/factual_read_entitlements.py'
        if not schema.is_file():raise RuntimeError('FACTUAL_READ_FEATURE_NOT_AVAILABLE')
        policy=self.c.STATE/'factual-read-120'/'grants.ndjson'
        if not policy.exists() and not policy.is_symlink():raise RuntimeError('APPROVED_FACTUAL_READ_POLICY_REQUIRED')
        parent=policy.parent.lstat()
        if (policy.parent.resolve()!=policy.parent or not stat.S_ISDIR(parent.st_mode) or
                parent.st_uid!=os.getuid() or stat.S_IMODE(parent.st_mode)!=0o700):
            raise RuntimeError('PRIVATE_FACTUAL_POLICY_DIRECTORY_REQUIRED')
        fd=os.open(policy,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        try:
            s=os.fstat(fd)
            if not stat.S_ISREG(s.st_mode) or s.st_uid!=os.getuid() or s.st_nlink!=1 or stat.S_IMODE(s.st_mode)!=0o600 or s.st_size>4*1024*1024:
                raise RuntimeError('PRIVATE_FACTUAL_POLICY_FILE_REQUIRED')
            chunks=[];total=0
            while True:
                chunk=os.read(fd,min(65536,4*1024*1024+1-total))
                if not chunk:break
                chunks.append(chunk);total+=len(chunk)
                if total>4*1024*1024:raise RuntimeError('PRIVATE_FACTUAL_POLICY_FILE_REQUIRED')
        finally:os.close(fd)
        import importlib.util
        spec=importlib.util.spec_from_file_location('reviewed_local_factual_read_schema',schema)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        events=module.decode(b''.join(chunks))
        approval_bytes=module.private_read(policy.parent/'activation-approval.json')
        approval=json.loads(approval_bytes)
        fields={'schema_version','expected_head','action','grant_id','subject','assets','capabilities','not_before','expires_at','actor','approval_ref','operator_ref'}
        if (set(approval)!=fields or type(approval['schema_version']) is not int or approval['schema_version']!=1 or
                approval_bytes!=(module.canonical(approval)+'\n').encode() or approval['action']!='ISSUE'):
            raise RuntimeError('EXACT_FACTUAL_ACTIVATION_APPROVAL_REQUIRED')
        event=next((e for e in reversed(events) if e['grant_id']==approval['grant_id']),None)
        from datetime import datetime,timezone,timedelta
        now=datetime.now(timezone.utc)
        if any(module.timestamp(e['at'])>now+timedelta(seconds=5) for e in events):
            raise RuntimeError('FACTUAL_POLICY_CLOCK_REGRESSION')
        if (not event or event['action']!='ISSUE' or set(event['capabilities'])!=module.CAPABILITIES or
                any(event[key]!=approval[key] for key in fields-{'schema_version','expected_head'}) or
                event['previous_sha256']!=approval['expected_head'] or
                not module.timestamp(event['not_before'])<=now<module.timestamp(event['expires_at'])):
            raise RuntimeError('ACTIVE_EXACT_FACTUAL_ENTITLEMENT_REQUIRED')
        return ['NADI_FACTUAL_READ_POLICY_FILE='+str(policy)]

    def start_pair(self, value):
        factual_extra=self.factual_read_environment(value['root'],required=value.get('factual_read_required',False))
        root=Path(value['root']);web=root/'reliability-cockpit/web'
        self.start('nadi-live-api',root/'reliability-cockpit',
            [str(self.c.STATE/'python-runtime/bin/python'),'-m','uvicorn','local_fixture:create_app','--factory','--host','127.0.0.1','--port','13036',
             '--reload','--reload-dir',str(root/'reliability-cockpit/src'),'--reload-dir',str(root/'reliability-cockpit/tests/qa'),'--no-access-log'],['NADI_LOCAL_DEV_CONFIG='+value['config_path']], '2G')
        self.start('nadi-primary-web',web,[value['node'],'node_modules/next/dist/bin/next','dev','--hostname','localhost','--port','3000',
             '--experimental-https','--experimental-https-key',str(self.c.STATE/'localhost.key'),'--experimental-https-cert',str(self.c.STATE/'localhost.pem')],
            ['NODE_ENV=development','NEXT_TELEMETRY_DISABLED=1','NODE_OPTIONS=--max-old-space-size=4096',
             'NADI_LIVE_DEV=true','NADI_PRIMARY_FRONTEND=true','NADI_ENGINEERING_WORKSPACE_ENABLED=true',
             'NADI_ENGINEERING_DEMO_ENABLED=true','NADI_ENGINEERING_QA_ENABLED=true','NADI_QA_BACKEND_URL=http://127.0.0.1:13036',
             'COCKPIT_API_BASE=http://127.0.0.1:8000','NADI_DEV_LAUNCHED_SHA='+value['sha'],*factual_extra], '6G')

    def readiness(self, value, session_file=None):
        release=self.release()
        if value.get('readiness_controller_sha') and value['readiness_controller_sha']!=release:
            raise RuntimeError('LAUNCHER_CONTROLLER_MISMATCH')
        root = source(value['root'],self.c.BASE,value['sha'])
        front = self.owners(self.c.UNITS[1],root/'reliability-cockpit/web',3000)
        api = self.owners(self.c.UNITS[0],root/'reliability-cockpit',13036)
        python = str((self.c.STATE/'python-runtime/bin/python').resolve())
        if any(r['exe'] != python for r in api['listeners'].values()):
            raise RuntimeError('BACKEND_EXECUTABLE_CHANGED')
        if any(r['exe'] != value['node'] for r in front['listeners'].values()):
            raise RuntimeError('FRONTEND_NODE_PIN_CHANGED')
        if value.get('expected_web') and front != value['expected_web']:
            raise RuntimeError('UNEXPECTED_FRONTEND_PROCESS_OR_LISTENER_REPLACEMENT')
        if value.get('expected_api_parent') and self.unit(self.c.UNITS[0]) != value['expected_api_parent']:
            raise RuntimeError('UNEXPECTED_API_PARENT_REPLACEMENT')
        backend = self.request('http://127.0.0.1:13036/development/status')
        front_data = self.request(self.c.ORIGIN+'/api/development/health')
        qa = self.request('http://127.0.0.1:13036/health/ready')
        factual = self.request('http://127.0.0.1:8000/health')
        data = {'sha':front_data.get('frontend_sha'),'frontend_sha':front_data.get('frontend_sha'),
                'backend_sha':backend.get('source_sha'),'launched_sha':front_data.get('launched_sha'),
                'dirty':front_data.get('dirty'),'stale':front_data.get('frontend_sha')!=front_data.get('launched_sha'),
                'database_identity':backend.get('database_identity'),
                'backend':'AVAILABLE' if qa.get('status')=='READY' else 'UNAVAILABLE',
                'factual_backend':'AVAILABLE' if factual=={'status':'ok'} else 'UNAVAILABLE',
                'engineering':backend.get('engineering') is True,'engineering_data':'SYNTHETIC_FIXTURES'}
        if (front_data.get('contract')!='NADI_LOCAL_TRANSPORT_V1' or front_data.get('origin')!=self.c.ORIGIN or
                front_data.get('guard')!='SERVER_SESSION_AUTHORITY' or type(front_data.get('dirty')) is not bool or
                qa.get('authentication')!='LOCAL_SESSION_AUTHORITY'):
            raise RuntimeError('AUTHENTICATION_CAPABILITY_UNVERIFIED')
        sha = value['sha']
        if (data.get('sha') != sha or data.get('backend_sha') != sha or data.get('launched_sha') != sha or
                backend.get('source_sha') != sha or backend.get('current_sha') != sha or
                backend.get('bootstrap_sha') != value['workflow_sha'] or
                backend.get('source') != 'SYNTHETIC_LOCAL_DEVELOPMENT' or
                backend.get('database') != 'DISPOSABLE_TEST' or backend.get('environment') != 'DEVELOPMENT' or
                data.get('stale') is not False or data.get('database_identity') != DB or
                backend.get('database_identity') != DB or data.get('backend') != 'AVAILABLE' or
                data.get('factual_backend') != 'AVAILABLE' or not data.get('engineering')):
            raise RuntimeError('LOCAL_PAIR_NOT_READY')
        # Never treat a random redirect/401 as authentication proof. Positive capability is separate.
        data['authentication']=self.auth_readiness(session_file)
        data['transport_process_readiness']='VERIFIED'
        data['controller_source_sha']=release
        data['bootstrap_source_sha']=value['workflow_sha']
        # Dirty source remains visible; it is never coerced to clean or discarded.
        return data

    def wait_ready(self, value):
        deadline = time.monotonic()+120
        while True:
            try:
                return self.readiness(value,session_file=self.acceptance_session_file)
            except RuntimeError as error:
                if str(error) not in {'EXPECTED_LISTENER_MISSING','LOCAL_PAIR_NOT_READY'}:
                    raise
                if time.monotonic() >= deadline:
                    raise
            except OSError:
                if time.monotonic() >= deadline:
                    raise
            time.sleep(1)

    def attest(self, value):
        value['expected_web'] = self.owners(self.c.UNITS[1],Path(value['root'])/'reliability-cockpit/web',3000)
        value['expected_api_parent'] = self.unit(self.c.UNITS[0])

    def failure(self, token, error):
        code = str(error).split(':',1)[0]
        self.save(token+'-failed.json',{'id':token,'outcome':'FAILED','error_type':type(error).__name__,
                                      'code':code if re.fullmatch('[A-Z_]+',code) else 'PRIVATE_DIAGNOSTIC_REQUIRED'})

    def select(self, root, ref):
        # Identity is allocated even for rejected attempts; no deletion enables another attempt.
        self.state.mkdir(mode=0o700,exist_ok=True)
        info = self.state.lstat()
        if self.state.is_symlink() or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise RuntimeError('PRIVATE_LOCAL_STATE_REQUIRED')
        token = 'selection-'+uuid.uuid4().hex
        self.save(token+'-requested.json',{'id':token,'candidate':str(root),'ref':ref,'at':time.time(),
                                         'before':self.active_value()['sha'],'after':'UNRESOLVED',
                                         'outcome':'REQUESTED','rollback':None})
        try:
            with self.transaction():
                self._select(root,ref,token)
        except Exception as error:
            self.failure(token,error)
            raise

    def _select(self, root, ref, token):
        if self.preservation and not self.acceptance_session_file:
            raise RuntimeError('AUTHENTICATED_ACCEPTANCE_PROOF_REQUIRED')
        for event in self.state.glob('selection-*-stopping.json'):
            stem=event.name[:-len('-stopping.json')]
            if not any((self.state/(stem+suffix)).exists() for suffix in ['-accepted.json','-failure-recovered.json']):
                raise RuntimeError('INTERRUPTED_TRANSITION_REQUIRES_REVIEW')
        value = self.preflight(root,ref)
        if self.preservation:
            self.readiness(self.active_value(),session_file=self.acceptance_session_file)
        self.backup(value,token)
        again = self.preflight(root,ref)
        if again != {k:v for k,v in value.items() if k not in {'backup','backup_sha256','backup_created'}}:
            raise RuntimeError('BASELINE_CHANGED_BEFORE_TRANSITION')
        self.validate_recovery(value)
        self.save(token+'-prepared.json',value)
        config = private(value['previous']['config_path'])
        config.update(source_root=value['root'],workflow_sha=value['workflow_sha'])
        self.save(token+'-config.json',config)
        value['config_path'] = str(self.state/(token+'-config.json'))
        value['transition_id'] = token
        self.save(token+'-stopping.json',{'before':value['previous']['sha'],'after':value['sha'],
                                       'rollback':token+'-prepared.json'})
        source(root,self.c.BASE,value['sha'],clean=True)
        if value['previous'].get('sealed_source'):
            SealedSource.verify(value['previous']['sealed_source'],original=True)
        for key,unit,suffix,port in [('web',self.c.UNITS[1],'reliability-cockpit/web',3000),
                                     ('api',self.c.UNITS[0],'reliability-cockpit',13036)]:
            if self.owners(unit,Path(value['previous'].get('original_source',{}).get('root',value['previous']['root']))/suffix,port) != value['previous']['before'][key]:
                raise RuntimeError('BASELINE_CHANGED_BEFORE_TRANSITION')
        try:
            self.c.stop_unit(self.c.UNITS[1]); self.c.stop_unit(self.c.UNITS[0])
            if self.c.primary_busy():
                raise RuntimeError('PORT_NOT_RELEASED')
            self.start_pair(value)
            data = self.wait_ready(value)
            self.attest(value)
            self.save(token+'-accepted.json',{'id':token,'before':value['previous']['sha'],
                                           'after':value['sha'],'outcome':'READY','rollback':token+'-prepared.json'})
            self.replace('active.json',value)
            print(json.dumps({'status':'READY','frontend_sha':value['sha'],'backend_sha':value['sha'],
                              'database':DB,'origin':self.c.ORIGIN,'transition':token}))
        except Exception:
            # One recovery only, never retry candidate startup. Keep all evidence on failure.
            self._recover(value,token+'-failure')
            raise

    def _recover(self, value, token):
        self.validate_recovery(value)
        previous = dict(value['previous'])
        # Existing old-format expected PIDs describe the process before stop, not restored ones.
        previous.pop('expected_web',None); previous.pop('expected_api_parent',None)
        for unit,port,suffix in [(self.c.UNITS[1],3000,'reliability-cockpit/web'),
                                 (self.c.UNITS[0],13036,'reliability-cockpit')]:
            if self.c.active(unit):
                current = self.unit(unit)
                roots = [Path(value['root'])/suffix,Path(previous['root'])/suffix]
                if previous.get('original_source'):
                    roots.append(Path(previous['original_source']['root'])/suffix)
                if current['WorkingDirectory'] not in {str(p) for p in roots}:
                    raise RuntimeError('UNEXPECTED_RECOVERY_UNIT_OWNER')
                # Known unit alone is insufficient: every extant socket must be owned.
                try:
                    self.owners(unit,Path(current['WorkingDirectory']),port)
                except RuntimeError as error:
                    if str(error) != 'EXPECTED_LISTENER_MISSING':
                        raise
        # All extant units/listeners are validated before stopping either process.
        for unit in (self.c.UNITS[1],self.c.UNITS[0]):
            self.c.stop_unit(unit)
        if self.c.primary_busy():
            raise RuntimeError('PORT_NOT_RELEASED')
        self.start_pair(previous)
        self.wait_ready(previous)
        self.attest(previous)
        self.save(token+'-recovered.json',{'outcome':'ROLLED_BACK','source':previous['sha'],
                                        'backup':value['backup'],'data_restored_or_deleted':False})
        self.replace('active.json',previous)

    def recover(self, value):
        if 'previous' not in value:
            raise RuntimeError('REUSABLE_RECOVERY_RECORD_REQUIRED: historical recovery artifacts retained')
        if value.get('previous',{}).get('sealed_source') and not self.acceptance_session_file:
            raise RuntimeError('AUTHENTICATED_ACCEPTANCE_PROOF_REQUIRED')
        token = 'rollback-'+uuid.uuid4().hex
        self.save(token+'-requested.json',{'outcome':'REQUESTED','source':value['sha']})
        try:
            with self.transaction():
                if self.active_value() != value:
                    raise RuntimeError('ACTIVE_SELECTION_CHANGED')
                self.readiness(value,session_file=self.acceptance_session_file)
                recovery = dict(value)
                self.backup(recovery,token)
                self.save(token+'-prepared.json',recovery)
                self._recover(recovery,token)
        except Exception as error:
            self.failure(token,error)
            raise

    def active_value(self):
        return private(self.state/'active.json')

    def status(self, session_file=None):
        self.release()
        return self.readiness(self.active_value(),session_file=session_file)
