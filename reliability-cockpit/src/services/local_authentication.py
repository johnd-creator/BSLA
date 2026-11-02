"""Application-owned local directory. No defaults, registration, source access or mount.

All account/grant changes and session leases share PostgreSQL advisory locks.
Passwords/hashes never belong in views or audits. Operator CLI is separate.
"""
from contextlib import contextmanager, ExitStack
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import re
import secrets
from threading import BoundedSemaphore
from uuid import uuid4

from argon2 import PasswordHasher, Type
from argon2.exceptions import VerificationError, InvalidHashError
from sqlalchemy import (MetaData, Table, Column, String, Text, Boolean, Integer,
                        DateTime, JSON, select, update, text)
from sqlalchemy.exc import IntegrityError
from src.domain.engineering import Principal, Role, EngineeringError
from src.services.application_identity import IdentityGrant

metadata = MetaData()
ACCOUNT = Table("nadi_local_account", metadata,
    Column("user_id", String(160), primary_key=True), Column("username", String(64), unique=True),
    Column("password_hash", Text), Column("active", Boolean), Column("password_change_required", Boolean),
    Column("grant_version", Integer), Column("roles", JSON), Column("asset_ids", JSON),
    Column("failed_attempts", Integer), Column("locked_until", DateTime(timezone=True)),
    Column("created_at", DateTime(timezone=True)), Column("updated_at", DateTime(timezone=True)))
BUDGET = Table("nadi_local_login_budget", metadata,
    Column("budget_id", String(40), primary_key=True), Column("window_start", DateTime(timezone=True)),
    Column("attempts", Integer))
EVENT = Table("nadi_local_security_event", metadata,
    Column("event_id", String(100), primary_key=True), Column("actor_id", String(160)),
    Column("target_id", String(160)), Column("action", String(40)), Column("outcome", String(40)),
    Column("occurred_at", DateTime(timezone=True)))
FOREVER = datetime.max.replace(tzinfo=timezone.utc)


@dataclass(frozen=True)
class PasswordPolicy:
    minimum_length: int = 15
    maximum_length: int = 256
    attempts_per_window: int = 100
    window_seconds: int = 60
    account_failures: int = 5
    lock_seconds: int = 300
    hashing_capacity: int = 4

    def __post_init__(self):
        bounds = ((self.minimum_length, 12, 128), (self.maximum_length, self.minimum_length, 256),
                  (self.attempts_per_window, 1, 1000), (self.window_seconds, 1, 3600),
                  (self.account_failures, 1, 20), (self.lock_seconds, 1, 3600),
                  (self.hashing_capacity, 1, 8))
        if any(type(v) is not int or not lo <= v <= hi for v, lo, hi in bounds):
            raise ValueError("EXPLICIT_BOUNDED_PASSWORD_POLICY_REQUIRED")

    def password(self, value):
        if (not isinstance(value, str) or not self.minimum_length <= len(value) <= self.maximum_length
                or len(value.encode("utf-8")) > 1024 or not value.strip()):
            raise EngineeringError("PASSWORD_POLICY_DENIED", 400)
        return value


def normalize_username(value):
    if not isinstance(value, str) or len(value) > 64:
        raise EngineeringError("INVALID_ACCOUNT_INPUT", 400)
    name = value.strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{2,63}", name, flags=re.ASCII):
        raise EngineeringError("INVALID_ACCOUNT_INPUT", 400)
    return name


def lock_key(subject):
    return int.from_bytes(sha256(("nadi-local:" + subject).encode()).digest()[:8], "big", signed=True)


class LocalIdentityProvider:
    def __init__(self, store, *, policy=None, clock=None, demo_profile=None):
        if store.engine.dialect.name != "postgresql":
            raise EngineeringError("POSTGRESQL_REQUIRED", 503)
        self.engine = store.engine
        self.policy = policy or PasswordPolicy()
        self.demo_profile = demo_profile
        if demo_profile is not None:
            from src.services.local_demo_accounts import DemoPasswordProfile
            if not isinstance(demo_profile, DemoPasswordProfile):
                raise EngineeringError('VERIFIED_LOCAL_DEMO_PROFILE_REQUIRED', 503)
            if self.policy.minimum_length != 15:
                raise EngineeringError('DEMO_PROFILE_STANDARD_POLICY_REQUIRED', 503)
            demo_profile.check_target(self.engine)
            with self.engine.connect() as c:
                demo_profile.verify(c)
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4, type=Type.ID)
        self._dummy = self.hasher.hash(secrets.token_urlsafe(32))
        self._hashing = BoundedSemaphore(self.policy.hashing_capacity)

    def verify_assertion(self, assertion):
        # Local credentials never travel through the legacy opaque-proof endpoint.
        raise EngineeringError("AUTHENTICATION_REQUIRED", 401)

    def _grant(self, row):
        if row is None or not row["active"] or row["password_change_required"] or not row["roles"]:
            return None
        return IdentityGrant(principal=Principal(principal_id=row["user_id"],
            roles=frozenset(row["roles"]), asset_ids=frozenset(row["asset_ids"])),
            version=row["grant_version"], valid_until=FOREVER)

    def current_grant(self, subject):
        with self.engine.connect() as c:
            return self._grant(c.execute(select(ACCOUNT).where(ACCOUNT.c.user_id == subject)).mappings().first())

    def self_username(self, subject):
        """Bounded display metadata, called only for the actor inside a valid session lease.

        Does not create an identity/grant and never returns password/security fields.
        """
        if not isinstance(subject, str) or len(subject) > 160:
            return None
        with self.engine.connect() as c:
            return c.scalar(select(ACCOUNT.c.username).where(ACCOUNT.c.user_id == subject))

    @contextmanager
    def _locks(self, *subjects):
        with self.engine.begin() as c:
            for subject in sorted(set(subjects)):
                c.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_key(subject)})
            yield c

    @contextmanager
    def guard(self, subject, version):
        with self._locks(subject) as c:
            row = c.execute(select(ACCOUNT).where(ACCOUNT.c.user_id == subject)).mappings().first()
            grant = self._grant(row)
            if not grant or grant.version != version:
                raise EngineeringError("IDENTITY_REVOKED", 401)
            yield

    def _audit(self, c, actor, target, action, outcome="PASS"):
        c.execute(EVENT.insert().values(event_id="security:" + str(uuid4()), actor_id=actor,
            target_id=target, action=action, outcome=outcome, occurred_at=self.clock()))

    def _verify(self, hashed, password):
        try:
            return self.hasher.verify(hashed, password)
        except (VerificationError, InvalidHashError):
            return False

    def _replacement_password(self, c, row, value):
        if self.demo_profile is not None and self.demo_profile.applies(c, row):
            if (not isinstance(value, str) or not 8 <= len(value) <= self.policy.maximum_length
                    or len(value.encode('utf-8')) > 1024 or not value.strip()):
                raise EngineeringError('PASSWORD_POLICY_DENIED', 400)
            return value
        return self.policy.password(value)

    def authenticate(self, username, password, *, new_password=None):
        # Generic failure for malformed, absent, disabled and locked accounts.
        try:
            name = normalize_username(username)
        except EngineeringError:
            name = ""
        bounded = isinstance(password, str) and 1 <= len(password) <= 256 and len(password.encode()) <= 1024
        if not self._hashing.acquire(blocking=False):
            raise EngineeringError("LOGIN_RATE_LIMITED", 429)
        try:
            failure, grant = None, None
            with self.engine.begin() as c:
                if not c.scalar(text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": lock_key("login-budget")}):
                    raise EngineeringError("LOGIN_RATE_LIMITED", 429)
                now = self.clock()
                budget = c.execute(select(BUDGET).where(BUDGET.c.budget_id == "global")).mappings().first()
                count = budget["attempts"] if budget and budget["window_start"] + timedelta(seconds=self.policy.window_seconds) > now else 0
                start = budget["window_start"] if count else now
                if count >= self.policy.attempts_per_window:
                    self._audit(c, None, None, "LOGIN", "RATE_LIMITED")
                    failure = EngineeringError("LOGIN_RATE_LIMITED", 429)
                else:
                    if budget:
                        c.execute(update(BUDGET).values(attempts=count+1, window_start=start))
                    else:
                        c.execute(BUDGET.insert().values(budget_id="global", attempts=1, window_start=now))
                    identity = c.scalar(select(ACCOUNT.c.user_id).where(ACCOUNT.c.username == name))
                    # Coordinate rename/create without locking a newly reused name
                    # under the old identity. All directory locks share one order.
                    for subject in sorted({'username:'+name, *([identity] if identity else [])}):
                        c.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_key(subject)})
                    row = c.execute(select(ACCOUNT).where(ACCOUNT.c.username == name).with_for_update()).mappings().first()
                    eligible = bool(row and row['user_id'] == identity and row["active"]
                                    and (not row["locked_until"] or row["locked_until"] <= now))
                    verified = self._verify(row["password_hash"] if eligible else self._dummy,
                                            password if bounded else secrets.token_urlsafe(32))
                    if eligible and verified and self.demo_profile is not None:
                        if row['user_id'] in dict(self.demo_profile.identities).values():
                            self.demo_profile.verify(c)
                    if not bounded or not eligible or not verified:
                        if eligible:
                            attempts = row["failed_attempts"] + 1
                            c.execute(update(ACCOUNT).where(ACCOUNT.c.user_id == identity).values(
                                failed_attempts=attempts, updated_at=now,
                                locked_until=now+timedelta(seconds=self.policy.lock_seconds) if attempts >= self.policy.account_failures else None))
                        self._audit(c, None, identity, "LOGIN", "DENIED")
                        failure = EngineeringError("INVALID_CREDENTIALS", 401)
                    elif new_password is not None:
                        try:
                            self._replacement_password(c, row, new_password)
                        except EngineeringError as error:
                            failure = error
                        if not failure:
                            if new_password == password:
                                failure = EngineeringError("PASSWORD_POLICY_DENIED", 400)
                            else:
                                c.execute(update(ACCOUNT).where(ACCOUNT.c.user_id == identity).values(
                                    password_hash=self.hasher.hash(new_password), password_change_required=False,
                                    grant_version=row["grant_version"]+1, failed_attempts=0, locked_until=None, updated_at=now))
                                self._audit(c, identity, identity, "PASSWORD_CHANGED")
                                row = c.execute(select(ACCOUNT).where(ACCOUNT.c.user_id == identity)).mappings().one()
                    elif row["password_change_required"]:
                        failure = EngineeringError("PASSWORD_CHANGE_REQUIRED", 403)
                    if eligible and verified and not failure:
                        c.execute(update(ACCOUNT).where(ACCOUNT.c.user_id == identity).values(failed_attempts=0, locked_until=None, updated_at=now))
                        grant = self._grant(row)
                        if not grant:
                            failure = EngineeringError("INVALID_CREDENTIALS", 401)
                        self._audit(c, identity, identity, "LOGIN", "PASS" if grant else "DENIED")
            if failure:
                raise failure
            return grant
        finally:
            self._hashing.release()

    def _authorize(self, c, actor, assets):
        if not isinstance(actor, IdentityGrant):
            raise EngineeringError("FORBIDDEN", 403)
        current = self._grant(c.execute(select(ACCOUNT).where(ACCOUNT.c.user_id == actor.principal.principal_id)).mappings().first())
        if not current or current != actor or Role.ADMIN not in actor.principal.roles or not assets <= actor.principal.asset_ids:
            raise EngineeringError("FORBIDDEN", 403)

    def _scope(self, roles, assets):
        if not isinstance(roles, (set, frozenset, list, tuple)) or not isinstance(assets, (set, frozenset, list, tuple)):
            raise EngineeringError("INVALID_ACCOUNT_INPUT", 400)
        try:
            result = frozenset(Role(v) for v in roles)
        except (ValueError, TypeError):
            raise EngineeringError("INVALID_ACCOUNT_INPUT", 400) from None
        if (len(assets) > 1000 or any(not isinstance(v, str) or not re.fullmatch(r"[a-zA-Z0-9_.:-]{1,200}", v) for v in assets)):
            raise EngineeringError("INVALID_ACCOUNT_INPUT", 400)
        return sorted(result), sorted(set(assets))

    def _insert(self, c, username, password, roles, assets, actor, change):
        if c.scalar(select(ACCOUNT.c.user_id).where(ACCOUNT.c.username == username)):
            raise EngineeringError("ACCOUNT_CONFLICT", 409)
        user = "local:" + str(uuid4())
        now = self.clock()
        c.execute(ACCOUNT.insert().values(user_id=user, username=username, password_hash=self.hasher.hash(password),
            active=True, password_change_required=change, grant_version=1, roles=roles, asset_ids=assets,
            failed_attempts=0, locked_until=None, created_at=now, updated_at=now))
        self._audit(c, actor, user, "ACCOUNT_CREATED")
        return user

    def bootstrap(self, *, username, password, assets, operator_ref):
        if not isinstance(operator_ref, str) or not re.fullmatch(r"[a-zA-Z0-9_.:@-]{1,100}", operator_ref):
            raise EngineeringError("OPERATOR_REFERENCE_REQUIRED", 400)
        roles, scope = self._scope([Role.ADMIN], assets)
        name = normalize_username(username)
        self.policy.password(password)
        with self._locks("bootstrap") as c:
            if c.scalar(select(ACCOUNT.c.user_id).limit(1)):
                raise EngineeringError("EXPLICIT_ADMIN_RECOVERY_REQUIRED", 409)
            return self._insert(c, name, password, roles, scope, "operator:"+operator_ref, False)

    def create_account(self, actor, *, username, password, roles, assets, require_change=True):
        name = normalize_username(username)
        self.policy.password(password)
        roles, scope = self._scope(roles, assets)
        if type(require_change) is not bool:
            raise EngineeringError("INVALID_ACCOUNT_INPUT", 400)
        # Username lock makes normalized uniqueness deterministic before insert.
        with self._locks(actor.principal.principal_id if isinstance(actor, IdentityGrant) else "", "username:"+name) as c:
            self._authorize(c, actor, frozenset(scope))
            return self._insert(c, name, password, roles, scope, actor.principal.principal_id, require_change)

    def change_account(self, actor, target, *, active=None, password=None, roles=None, assets=None, revoke=False):
        if not isinstance(target, str) or len(target) > 160 or type(revoke) is not bool:
            raise EngineeringError("INVALID_ACCOUNT_INPUT", 400)
        if active is not None and type(active) is not bool:
            raise EngineeringError("INVALID_ACCOUNT_INPUT", 400)
        with self._locks(actor.principal.principal_id if isinstance(actor, IdentityGrant) else "", target) as c:
            row = c.execute(select(ACCOUNT).where(ACCOUNT.c.user_id == target).with_for_update()).mappings().first()
            if not row:
                raise EngineeringError("NOT_FOUND", 404)
            new_roles, new_assets = self._scope(roles if roles is not None else row["roles"], assets if assets is not None else row["asset_ids"])
            self._authorize(c, actor, frozenset(row["asset_ids"]) | frozenset(new_assets))
            if (self.demo_profile is not None and target in dict(self.demo_profile.identities).values()
                    and (new_roles != sorted(row['roles']) or new_assets != sorted(row['asset_ids']))):
                raise EngineeringError('DEMO_PROFILE_SCOPE_CHANGE_FORBIDDEN', 409)
            if password is not None:
                self._replacement_password(c, row, password)
            changes = {"grant_version":row["grant_version"]+1, "updated_at":self.clock()}
            if active is not None:
                changes["active"] = active
            if roles is not None:
                changes["roles"] = new_roles
            if assets is not None:
                changes["asset_ids"] = new_assets
            if password is not None:
                changes.update(password_hash=self.hasher.hash(password), password_change_required=True, failed_attempts=0, locked_until=None)
            # Don't remove/disable the last admin through the user-facing capability.
            if Role.ADMIN in row["roles"] and (active is False or Role.ADMIN not in new_roles):
                c.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key":lock_key("admin-safety")})
                others = c.execute(select(ACCOUNT.c.roles).where(ACCOUNT.c.user_id != target, ACCOUNT.c.active.is_(True))).scalars()
                if not any(Role.ADMIN in r for r in others):
                    raise EngineeringError("LAST_ADMIN_REQUIRED", 409)
            c.execute(update(ACCOUNT).where(ACCOUNT.c.user_id == target).values(**changes))
            for action, used in (("ACCOUNT_STATUS", active is not None), ("PASSWORD_RESET", password is not None),
                                 ("GRANTS_CHANGED", roles is not None or assets is not None), ("SESSIONS_REVOKED", revoke)):
                if used:
                    self._audit(c, actor.principal.principal_id, target, action)
            if not any((active is not None, password is not None, roles is not None, assets is not None, revoke)):
                raise EngineeringError("INVALID_ACCOUNT_INPUT", 400)

    def rename_account(self, actor, target, *, expected_username, new_username):
        """Private ADMIN CAS; ownership and credentials stay on the same UUID."""
        if not isinstance(target, str) or not target or len(target) > 160:
            raise EngineeringError('INVALID_ACCOUNT_INPUT', 400)
        old, new = normalize_username(expected_username), normalize_username(new_username)
        try:
            with self._locks(actor.principal.principal_id if isinstance(actor, IdentityGrant) else '',
                             target, 'username:'+old, 'username:'+new) as c:
                row = c.execute(select(ACCOUNT).where(ACCOUNT.c.user_id == target).with_for_update()).mappings().first()
                if not row:
                    raise EngineeringError('NOT_FOUND', 404)
                self._authorize(c, actor, frozenset(row['asset_ids']))
                if row['username'] != old:
                    raise EngineeringError('ACCOUNT_NAME_CHANGED', 409)
                if old == new or c.scalar(select(ACCOUNT.c.user_id).where(ACCOUNT.c.username == new)):
                    raise EngineeringError('ACCOUNT_CONFLICT', 409)
                c.execute(update(ACCOUNT).where(ACCOUNT.c.user_id == target).values(
                    username=new, grant_version=row['grant_version']+1, updated_at=self.clock()))
                self._audit(c, actor.principal.principal_id, target, 'ACCOUNT_RENAMED')
        except IntegrityError:
            raise EngineeringError('ACCOUNT_CONFLICT', 409) from None

    def security_events(self, actor, *, limit=50, offset=0):
        if type(limit) is not int or type(offset) is not int or not 1 <= limit <= 100 or not 0 <= offset <= 10000:
            raise EngineeringError("INVALID_ACCOUNT_INPUT", 400)
        with self._locks(actor.principal.principal_id if isinstance(actor, IdentityGrant) else "") as c:
            self._authorize(c, actor, frozenset())
            # Operator/global security custodian must use private local SQL audit;
            # scoped admins see only own/authorized accounts, never unknown usernames.
            scoped = text("SELECT user_id FROM nadi_local_account a WHERE NOT EXISTS "
                "(SELECT 1 FROM json_array_elements_text(a.asset_ids) i(value) "
                "WHERE NOT (i.value = ANY(:assets)))")
            rows = c.execute(text("SELECT * FROM nadi_local_security_event WHERE target_id IN (" + scoped.text + ") "
                "ORDER BY occurred_at,event_id LIMIT :limit OFFSET :offset"),
                {"assets":sorted(actor.principal.asset_ids),"limit":limit,"offset":offset}).mappings()
            return [dict(row) for row in rows]
