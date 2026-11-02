"""Synthetic-only native PG qualification; never accepts the live fixture port.

The demo target URL check is unit-tested separately. Integration tests patch only
that check to permit this disposable cluster's different port, retaining real
database/role/scope/bootstrap-audit checks and real PostgreSQL advisory locks.
"""
import json
import io
import os
import secrets
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from argon2 import PasswordHasher
from sqlalchemy import create_engine, select, text, update, event
from sqlalchemy.engine import make_url
from src.domain.engineering import EngineeringError, Role
from src.repositories.application_boundary import ApplicationStore
from src.repositories.application_migrations import ApplicationMigrator
from src.services.application_identity import SessionAuthority
from src.services.local_authentication import LocalIdentityProvider, PasswordPolicy, ACCOUNT, EVENT
from src.services.local_demo_accounts import DemoPasswordProfile, EXPECTED, ACK, load_demo_profile


class DemoTargetTest(unittest.TestCase):
    def test_default_policy_stays_fifteen_and_global_eight_is_forbidden(self):
        self.assertEqual(PasswordPolicy().minimum_length, 15)
        with self.assertRaises(ValueError):
            PasswordPolicy(minimum_length=8)

    def test_exact_target_config_and_four_unique_ids(self):
        ids=tuple((purpose,'local:00000000-0000-0000-0000-'+str(i).zfill(12))
                  for i,purpose in enumerate(EXPECTED))
        profile=DemoPasswordProfile(ids)
        engine=create_engine('postgresql+psycopg://nadi_local_dev_01@127.0.0.1:15443/nadi_local_dev_01_test')
        profile.check_target(engine)  # Pure URL/shape check: no database connection.
        for url in ['postgresql+psycopg://nadi_local_dev_01@127.0.0.1:15483/nadi_local_dev_01_test',
                    'postgresql+psycopg://nadi_local_dev_01@127.0.0.1:15443/production',
                    'postgresql+psycopg://other@127.0.0.1:15443/nadi_local_dev_01_test',
                    'postgresql+psycopg://nadi_local_dev_01@source.example.invalid:15443/nadi_local_dev_01_test']:
            wrong=create_engine(url)
            with self.assertRaises(EngineeringError):profile.check_target(wrong)
            wrong.dispose()
        with self.assertRaises(EngineeringError):DemoPasswordProfile(ids[:3]).check_target(engine)
        with self.assertRaises(EngineeringError):DemoPasswordProfile(tuple((k,ids[0][1]) for k,_ in ids)).check_target(engine)
        engine.dispose()


@unittest.skipUnless(os.getenv('NADI_DEMO_ACCOUNT_TEST_DSN'),'disposable native PostgreSQL required')
class DemoAccountTest(unittest.TestCase):
    def setUp(self):
        url=make_url(os.environ['NADI_DEMO_ACCOUNT_TEST_DSN'])
        if (url.host!='127.0.0.1' or url.port!=15483 or url.database!='nadi_local_dev_01_test'
                or url.username!='nadi_local_dev_01'):
            raise RuntimeError('EXCLUSIVE_DISPOSABLE_CLUSTER_15483_REQUIRED')
        self.engine=create_engine(url,hide_parameters=True,connect_args={'connect_timeout':5})
        with self.engine.begin() as c:c.exec_driver_sql('DROP SCHEMA public CASCADE; CREATE SCHEMA public')
        ApplicationMigrator(self.engine,expected_database=url.database,isolated=True).apply()
        self.store=ApplicationStore(self.engine,expected_database=url.database,isolated=True)
        self.provider=LocalIdentityProvider(self.store)
        # Test-only lower Argon cost; production settings are unchanged.
        self.provider.hasher=PasswordHasher(time_cost=1,memory_cost=1024,parallelism=1)
        self.secret=secrets.token_urlsafe(24)
        roles,assets=EXPECTED['admin']
        self.ids={'admin':self.provider.bootstrap(username='local-operator',password=self.secret,
                    assets=set(assets),operator_ref='NADI-LOCAL-DEV-01')}
        self.admin=self.provider.authenticate('local-operator',self.secret)
        for purpose in ['engineer','reviewer','outsider']:
            roles,assets=EXPECTED[purpose]
            self.ids[purpose]=self.provider.create_account(self.admin,username='local-'+purpose,
                password=self.secret,roles=set(roles),assets=set(assets),require_change=False)
        self.profile=DemoPasswordProfile(tuple(sorted(self.ids.items())))
        self.authority=SessionAuthority(self.store,self.provider,origins={'https://nadi.example.invalid'},
                                        idle_seconds=1800,absolute_seconds=28800)

    def tearDown(self):self.engine.dispose()

    def row(self,purpose='engineer'):
        with self.engine.connect() as c:
            return dict(c.execute(select(ACCOUNT).where(ACCOUNT.c.user_id==self.ids[purpose])).mappings().one())

    def enable_demo(self):
        # This cluster is deliberately NOT the live approved port15443.
        with patch.object(DemoPasswordProfile,'check_target'):
            self.provider=LocalIdentityProvider(self.store,demo_profile=self.profile)
        self.provider.hasher=PasswordHasher(time_cost=1,memory_cost=1024,parallelism=1)
        self.admin=self.provider.authenticate('local-operator',self.secret)

    def code(self,expected,operation):
        with self.assertRaises(EngineeringError) as err:operation()
        self.assertEqual(err.exception.code,expected)

    def test_rename_preserves_identity_credentials_scope_and_audit(self):
        before=self.row()
        self.provider.rename_account(self.admin,self.ids['engineer'],expected_username=' LOCAL-ENGINEER ',new_username=' Engineer ')
        after=self.row()
        for key in before:
            if key not in {'username','grant_version','updated_at'}:self.assertEqual(after[key],before[key],key)
        self.assertEqual(after['username'],'engineer');self.assertEqual(after['grant_version'],before['grant_version']+1)
        self.assertEqual(self.provider.authenticate('ENGINEER',self.secret).principal.principal_id,self.ids['engineer'])
        self.code('INVALID_CREDENTIALS',lambda:self.provider.authenticate('local-engineer',self.secret))
        with self.engine.connect() as c:
            audits=c.execute(select(EVENT.c.actor_id,EVENT.c.target_id,EVENT.c.action).where(EVENT.c.action=='ACCOUNT_RENAMED')).all()
        self.assertEqual(audits,[(self.ids['admin'],self.ids['engineer'],'ACCOUNT_RENAMED')])

    def test_rename_revokes_existing_session_and_stale_admin(self):
        grant=self.provider.authenticate('local-engineer',self.secret)
        token,_=self.authority.establish_verified(grant)
        self.provider.rename_account(self.admin,self.ids['engineer'],expected_username='local-engineer',new_username='engineer')
        with self.assertRaises(EngineeringError):
            with self.authority.lease(token):pass
        self.provider.rename_account(self.admin,self.ids['admin'],expected_username='local-operator',new_username='admin')
        self.code('FORBIDDEN',lambda:self.provider.rename_account(self.admin,self.ids['reviewer'],expected_username='local-reviewer',new_username='reviewer'))

    def test_collision_stale_expected_noop_invalid_rollback(self):
        before=self.row()
        for old,new,code in [('local-engineer','LOCAL-REVIEWER','ACCOUNT_CONFLICT'),
                             ('old-engineer','engineer','ACCOUNT_NAME_CHANGED'),
                             ('local-engineer','LOCAL-ENGINEER','ACCOUNT_CONFLICT'),
                             ('local-engineer','bad name','INVALID_ACCOUNT_INPUT')]:
            self.code(code,lambda:self.provider.rename_account(self.admin,self.ids['engineer'],expected_username=old,new_username=new))
            self.assertEqual(self.row(),before)

    def test_nonadmin_and_out_of_scope_cannot_rename(self):
        author=self.provider.authenticate('local-engineer',self.secret)
        self.code('FORBIDDEN',lambda:self.provider.rename_account(author,self.ids['reviewer'],expected_username='local-reviewer',new_username='reviewer'))
        scoped=self.provider.create_account(self.admin,username='scope-admin',password=self.secret,roles={'ADMIN'},assets={'NADI-ASSET-001'},require_change=False)
        actor=self.provider.current_grant(scoped)
        self.code('FORBIDDEN',lambda:self.provider.rename_account(actor,self.ids['outsider'],expected_username='local-outsider',new_username='outsider'))

    def test_concurrent_rename_and_create_share_name_lock(self):
        other_id=self.provider.create_account(self.admin,username='another-admin',password=self.secret,
            roles={'ADMIN'},assets=set(EXPECTED['admin'][1]),require_change=False)
        other=self.provider.current_grant(other_id)
        def rename():
            try:self.provider.rename_account(self.admin,self.ids['engineer'],expected_username='local-engineer',new_username='contended');return 'OK'
            except EngineeringError as e:return e.code
        def create():
            try:self.provider.create_account(other,username='CONTENDED',password=self.secret,roles={'AUTHOR'},assets={'NADI-ASSET-001'});return 'OK'
            except EngineeringError as e:return e.code
        with ThreadPoolExecutor(2) as pool:results=list(pool.map(lambda fn:fn(),[rename,create]))
        self.assertEqual(sorted(results),['ACCOUNT_CONFLICT','OK'])

    def test_login_lookup_cannot_switch_to_concurrently_reused_username(self):
        looked_up,release=threading.Event(),threading.Event()
        def pause(conn,cursor,statement,parameters,context,many):
            if (threading.current_thread().name.startswith('login-race') and not looked_up.is_set()
                    and statement.startswith('SELECT nadi_local_account.user_id')
                    and 'local-engineer' in parameters.values()):
                looked_up.set()
                if not release.wait(10):raise RuntimeError('RACE_TEST_TIMEOUT')
        event.listen(self.engine,'after_cursor_execute',pause)
        def login():
            try:return self.provider.authenticate('local-engineer',self.secret).principal.principal_id
            except EngineeringError as err:return err.code
        try:
            with ThreadPoolExecutor(1,thread_name_prefix='login-race') as pool:
                future=pool.submit(login)
                try:
                    self.assertTrue(looked_up.wait(5))
                    self.provider.rename_account(self.admin,self.ids['engineer'],expected_username='local-engineer',new_username='engineer')
                    replacement=self.provider.create_account(self.admin,username='local-engineer',password=self.secret,
                        roles={'AUTHOR'},assets={'NADI-ASSET-001'},require_change=False)
                finally:release.set()
                self.assertEqual(future.result(timeout=10),'INVALID_CREDENTIALS')
            self.assertNotEqual(replacement,self.ids['engineer'])
        finally:event.remove(self.engine,'after_cursor_execute',pause)

    def test_audit_failure_rolls_back_rename(self):
        before=self.row()
        with patch.object(self.provider,'_audit',side_effect=RuntimeError('SYNTHETIC_AUDIT_FAILURE')):
            with self.assertRaises(RuntimeError):
                self.provider.rename_account(self.admin,self.ids['engineer'],expected_username='local-engineer',new_username='engineer')
        self.assertEqual(self.row(),before)

    def test_demo_seven_rejected_eight_reset_and_final_change(self):
        self.enable_demo()
        self.code('PASSWORD_POLICY_DENIED',lambda:self.provider.change_account(self.admin,self.ids['engineer'],password='s'*7))
        temporary=secrets.token_hex(4);replacement=secrets.token_hex(4)
        self.provider.change_account(self.admin,self.ids['engineer'],password=temporary)
        self.code('PASSWORD_CHANGE_REQUIRED',lambda:self.provider.authenticate('local-engineer',temporary))
        self.code('PASSWORD_POLICY_DENIED',lambda:self.provider.authenticate('local-engineer',temporary,new_password='n'*7))
        grant=self.provider.authenticate('local-engineer',temporary,new_password=replacement)
        self.assertEqual(grant.principal.principal_id,self.ids['engineer']);self.assertFalse(self.row()['password_change_required'])
        self.assertEqual(self.row()['grant_version'],3)

    def test_fifth_account_retains_fifteen_for_reset_and_final_change(self):
        self.enable_demo();other=self.provider.create_account(self.admin,username='non-demo',password=self.secret,
            roles={'AUTHOR'},assets={'NADI-ASSET-001'},require_change=False)
        self.code('PASSWORD_POLICY_DENIED',lambda:self.provider.change_account(self.admin,other,password='z'*14))
        temporary=secrets.token_hex(8);self.provider.change_account(self.admin,other,password=temporary)
        self.code('PASSWORD_POLICY_DENIED',lambda:self.provider.authenticate('non-demo',temporary,new_password='z'*14))
        self.assertEqual(self.provider.authenticate('non-demo',temporary,new_password=secrets.token_hex(8)).principal.principal_id,other)

    def test_creation_and_bootstrap_never_use_demo_exception(self):
        self.enable_demo()
        self.code('PASSWORD_POLICY_DENIED',lambda:self.provider.create_account(self.admin,username='new-short',password='z'*8,roles={'AUTHOR'},assets=set()))
        self.code('PASSWORD_POLICY_DENIED',lambda:self.provider.bootstrap(username='new-admin',password='z'*8,assets=set(),operator_ref='test'))

    def test_profile_survives_rename_not_role_scope_or_provenance_changes(self):
        self.enable_demo()
        self.provider.rename_account(self.admin,self.ids['engineer'],expected_username='local-engineer',new_username='engineer')
        self.provider.change_account(self.admin,self.ids['engineer'],password=secrets.token_hex(4))
        self.code('DEMO_PROFILE_SCOPE_CHANGE_FORBIDDEN',lambda:self.provider.change_account(self.admin,self.ids['reviewer'],assets=set()))
        # Simulate out-of-band fixture corruption: both replacement and login fail closed.
        with self.engine.begin() as c:c.execute(update(ACCOUNT).where(ACCOUNT.c.user_id==self.ids['reviewer']).values(asset_ids=[]))
        self.code('VERIFIED_LOCAL_DEMO_PROFILE_REQUIRED',lambda:self.provider.change_account(self.admin,self.ids['engineer'],password=secrets.token_hex(4)))
        self.code('VERIFIED_LOCAL_DEMO_PROFILE_REQUIRED',lambda:self.provider.authenticate('local-operator',self.secret))

    def test_profile_rejects_missing_or_forged_creation_chain(self):
        with self.engine.begin() as c:c.execute(update(EVENT).where(EVENT.c.target_id==self.ids['engineer'],EVENT.c.action=='ACCOUNT_CREATED').values(actor_id='operator:not-demo'))
        with self.engine.connect() as c:self.code('VERIFIED_LOCAL_DEMO_PROFILE_REQUIRED',lambda:self.profile.verify(c))

    def test_cli_rename_uses_hidden_admin_input_and_stable_target(self):
        from src.qa.users import main
        args=['rename','--expected-database','nadi_local_dev_01_test','--operator-ref','synthetic-test',
              '--acknowledge-private-administration','--admin-username','local-operator',
              '--target-user-id',self.ids['engineer'],'--expected-username','local-engineer','--new-username','engineer']
        with patch.dict(os.environ,{'NADI_APPLICATION_ADMIN_DSN':self.engine.url.render_as_string(hide_password=False)}), \
                patch('src.qa.users.secret',return_value=self.secret) as hidden,patch('sys.stdout',new_callable=io.StringIO) as output:
            self.assertEqual(main(args),0);self.assertEqual(hidden.call_count,1)
            self.assertEqual(json.loads(output.getvalue())['status'],'ACCOUNT_RENAMED')
            self.assertNotIn(self.secret,output.getvalue())
        self.assertEqual(self.row()['username'],'engineer')

    def test_cli_private_input_cannot_be_piped(self):
        from src.qa.users import secret
        with patch('sys.stdin.isatty',return_value=False):
            self.code('PRIVATE_INTERACTIVE_INPUT_REQUIRED',lambda:secret('Synthetic prompt'))

    def test_demo_policy_cannot_be_combined_with_lower_global_minimum(self):
        with patch.object(DemoPasswordProfile,'check_target'):
            self.code('DEMO_PROFILE_STANDARD_POLICY_REQUIRED',lambda:LocalIdentityProvider(
                self.store,policy=PasswordPolicy(minimum_length=12),demo_profile=self.profile))

    def test_private_profile_contract_and_permissions(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'profile.json';value={'contract':'NADI_LOCAL_DEMO_PASSWORD_V1','acknowledgement':ACK,'account_ids':self.ids};path.write_text(json.dumps(value));path.chmod(0o600)
            with patch.object(DemoPasswordProfile,'check_target'):
                self.assertEqual(load_demo_profile(path,self.engine),self.profile)
                path.chmod(0o644);self.code('VERIFIED_LOCAL_DEMO_PROFILE_REQUIRED',lambda:load_demo_profile(path,self.engine))
                path.chmod(0o600);value['acknowledgement']='development';path.write_text(json.dumps(value));self.code('VERIFIED_LOCAL_DEMO_PROFILE_REQUIRED',lambda:load_demo_profile(path,self.engine))
