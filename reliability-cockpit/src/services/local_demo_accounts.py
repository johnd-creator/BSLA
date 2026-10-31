"""Explicit four-account fixture exception; never inferred from a username/host.

Only existing verified fixture identities may use an eight-character replacement
password. Creation/bootstrap and every other account retain their normal policy.
"""
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from src.domain.engineering import EngineeringError

ACK = 'eight-character-passwords-for-verified-local-demo-only'
DATABASE = 'nadi_local_dev_01_test'
EXPECTED = {
    'admin': (('ADMIN',), ('NADI-ASSET-001', 'asset:SYNTHETIC:FOREIGN')),
    'engineer': (('AUTHOR',), ('NADI-ASSET-001',)),
    'reviewer': (('REVIEWER',), ('NADI-ASSET-001',)),
    'outsider': (('AUTHOR',), ('asset:SYNTHETIC:FOREIGN',)),
}


def denied():
    raise EngineeringError('VERIFIED_LOCAL_DEMO_PROFILE_REQUIRED', 503)


@dataclass(frozen=True)
class DemoPasswordProfile:
    # Immutable binding, deliberately independent of mutable names/grant versions.
    identities: tuple

    def check_target(self, engine):
        u = engine.url
        if (engine.dialect.name != 'postgresql' or u.get_backend_name() != 'postgresql'
                or (u.host, u.port, u.database, u.username) !=
                ('127.0.0.1', 15443, DATABASE, 'nadi_local_dev_01') or u.query):
            denied()
        if (len(self.identities) != 4 or {k for k, _ in self.identities} != set(EXPECTED)
                or len({v for _, v in self.identities}) != 4
                or any(not isinstance(v, str) or not re.fullmatch(
                    r'local:[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', v)
                       for _, v in self.identities)):
            denied()

    def verify(self, c):
        from src.services.local_authentication import ACCOUNT, EVENT
        # Real database identity, not just a configured loopback URL.
        from sqlalchemy import text
        if tuple(c.execute(text('SELECT current_database(), current_user')).one()) != (DATABASE, 'nadi_local_dev_01'):
            denied()
        ids = dict(self.identities)
        rows = {r['user_id']: r for r in c.execute(select(
            ACCOUNT.c.user_id, ACCOUNT.c.roles, ACCOUNT.c.asset_ids
        ).where(ACCOUNT.c.user_id.in_(ids.values()))).mappings()}
        for purpose, identity in ids.items():
            row = rows.get(identity)
            roles, assets = EXPECTED[purpose]
            if (not row or tuple(sorted(row['roles'])) != roles
                    or tuple(sorted(row['asset_ids'])) != assets):
                denied()
            audit = c.execute(select(EVENT.c.actor_id, EVENT.c.outcome).where(
                EVENT.c.target_id == identity, EVENT.c.action == 'ACCOUNT_CREATED'
            )).all()
            actor = 'operator:NADI-LOCAL-DEV-01' if purpose == 'admin' else ids['admin']
            if audit != [(actor, 'PASS')]:
                denied()

    def applies(self, c, row):
        if row['user_id'] not in dict(self.identities).values():
            return False
        self.verify(c)
        return True


def load_demo_profile(path, engine):
    """An explicit private operator-owned file; no env/dotenv/default lookup."""
    p = Path(path)
    st = p.lstat()
    if (not p.is_absolute() or p.is_symlink() or not p.is_file()
            or st.st_uid != os.getuid() or st.st_mode & 0o077 or st.st_size > 8192):
        denied()
    value = json.loads(p.read_text())
    if (not isinstance(value, dict) or set(value) != {'contract', 'acknowledgement', 'account_ids'}
            or value['contract'] != 'NADI_LOCAL_DEMO_PASSWORD_V1'
            or value['acknowledgement'] != ACK or not isinstance(value['account_ids'], dict)):
        denied()
    profile = DemoPasswordProfile(tuple(sorted(value['account_ids'].items())))
    profile.check_target(engine)
    with engine.connect() as c:
        profile.verify(c)
    return profile
