"""Owner-approved private Factual READ administration; no public endpoint/startup grant.

Plan never writes. Issue/revoke require an exact private approval digest, a fresh
authorized ADMIN, existing application DB/ledger identity and explicit --apply.
Passwords use the existing private TTY input. Never reads session proof files.
"""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import urllib.request
from urllib.parse import quote

from src.services.factual_read_entitlements import (
    ISSUER, ZERO, canonical, decode, instant, private_read, timestamp, append_event, PolicyCommitUncertain)

APPROVAL_FIELDS = {"schema_version", "expected_head", "action", "grant_id", "subject", "assets",
                   "capabilities", "not_before", "expires_at", "actor", "approval_ref", "operator_ref"}
LOCAL_DATABASE = "nadi_local_dev_01_test"
LOCAL_ROLE = "nadi_local_dev_01"


def bind_directory(dsn, expected_database):
    from sqlalchemy.engine import make_url
    url = make_url(dsn)
    if (expected_database != LOCAL_DATABASE or url.drivername != "postgresql+psycopg"
            or url.database != LOCAL_DATABASE or url.username != LOCAL_ROLE
            or url.host != "127.0.0.1" or url.port != 15443 or url.query):
        raise ValueError("OFFICIAL_LOCAL_SESSION_DIRECTORY_REQUIRED")


def load_approval(path, digest):
    data = private_read(Path(path))
    if sha256(data).hexdigest() != digest:
        raise ValueError("OWNER_APPROVAL_DIGEST_MISMATCH")
    approval = json.loads(data)
    if (not isinstance(approval, dict) or set(approval) not in (APPROVAL_FIELDS, APPROVAL_FIELDS | {"scope_kind"})
            or type(approval["schema_version"]) is not int or approval["schema_version"] != 1):
        raise ValueError("OWNER_APPROVAL_REQUIRED")
    # The reviewed bytes must be canonical; duplicate keys/non-finite values cannot hide.
    if data != (canonical(approval)+"\n").encode():
        raise ValueError("OWNER_APPROVAL_NONCANONICAL")
    return approval


def registry_asset(asset_id):
    # None validates the fixed Registry service, never enumerates assets or grants '*'.
    url = "http://127.0.0.1:8000/v1/reliability/" + ("registry" if asset_id is None else "assets/" + quote(asset_id, safe=""))
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args):
            raise ValueError("REGISTRY_REDIRECT_DENIED")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with opener.open(urllib.request.Request(url, headers={"Accept":"application/json"}), timeout=5) as response:
        if response.status != 200 or response.headers.get_content_type() != "application/json":
            raise ValueError("REGISTRY_IDENTITY_REQUIRED")
        data = response.read(256*1024+1)
        if len(data) > 256*1024:
            raise ValueError("REGISTRY_RESPONSE_TOO_LARGE")
        return json.loads(data)


def plan_only(approval, ledger, *, now):
    if set(approval) not in (APPROVAL_FIELDS, APPROVAL_FIELDS | {"scope_kind"}) or type(approval["schema_version"]) is not int or approval["schema_version"] != 1:
        raise ValueError("OWNER_APPROVAL_REQUIRED")
    events = decode(private_read(Path(ledger), missing=True))
    event = {k:v for k,v in approval.items() if k not in {"schema_version", "expected_head"}}
    event["at"] = instant(now)
    # Validate complete prospective ledger even for plan; append_event repeats under lock.
    prospective = {**event, "version":len(events)+1,
                   "previous_sha256":events[-1]["sha256"] if events else ZERO}
    prospective["sha256"] = sha256(canonical(prospective).encode()).hexdigest()
    data = b'{"schema_version":1}\n' + b"".join((canonical(e)+"\n").encode() for e in events+[prospective])
    decode(data)
    if prospective["previous_sha256"] != approval["expected_head"]:
        raise ValueError("FACTUAL_POLICY_HEAD_CONFLICT")
    if event["action"] == "ISSUE":
        if not timestamp(event["not_before"]) <= now < timestamp(event["expires_at"]):
            raise ValueError("OWNER_APPROVAL_OUTSIDE_VALIDITY")
    return event, prospective, events


def administer(provider, actor, approval, ledger, *, now, lookup=registry_asset, apply=False):
    if (actor.principal.principal_id != ISSUER or "ADMIN" not in actor.principal.roles
            or approval.get("actor") != ISSUER):
        raise ValueError("FACTUAL_ISSUER_DENIED")
    event, prospective, events = plan_only(approval, ledger, now=now)
    if event["action"] == "ISSUE":
        target = provider.current_grant(event["subject"])
        if not target or "AUTHOR" not in target.principal.roles:
            raise ValueError("ACTIVE_ENGINEER_IDENTITY_REQUIRED")
        states = {entry["grant_id"]:entry for entry in events}
        active_assets = set(event["assets"])
        for old in states.values():
            if (old["action"] == "ISSUE" and old["subject"] == event["subject"]
                    and timestamp(old["not_before"]) <= now < timestamp(old["expires_at"])):
                active_assets.update(old["assets"])
        if len(active_assets) > 20:
            raise ValueError("FACTUAL_ASSET_ALLOWLIST_BOUND_EXCEEDED")
        if event.get("scope_kind") == "REGISTERED_BSR_IP":
            registry = lookup(None)
            if (registry.get("source") != "MAXIMO_LIST_OF_ASSETS"
                    or type(registry.get("registered_asset_count")) is not int
                    or registry["registered_asset_count"] < 1):
                raise ValueError("REGISTERED_BSR_IP_POPULATION_REQUIRED")
        for asset_id in event["assets"]:
            asset = lookup(asset_id)
            if asset.get("canonical_id") != asset_id or asset.get("site_code") != "BSR" or asset.get("organization_code") != "IP":
                raise ValueError("REGISTERED_BSR_IP_ASSET_REQUIRED")
    if not apply:
        return {"status":"PLAN_ONLY", "action":event["action"], "next_version":prospective["version"]}
    # A current authenticated issuer is independent from Engineering asset write scope.
    # The fixed issuer and reviewed owner envelope authorize only this separate READ operation.
    written = None
    try:
        with provider.guard(actor.principal.principal_id, actor.version):
            current = provider.current_grant(actor.principal.principal_id)
            if current != actor:
                raise ValueError("FACTUAL_ISSUER_REVOKED")
            written = append_event(Path(ledger), event, expected_head=approval["expected_head"])
    except PolicyCommitUncertain:
        raise
    except Exception:
        if written is not None: raise PolicyCommitUncertain(written) from None
        raise
    return {"status":"APPLIED", "action":written["action"], "grant_id":written["grant_id"],
            "version":written["version"], "head_sha256":written["sha256"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approval-file", required=True)
    parser.add_argument("--approval-sha256", required=True)
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--expected-database", required=True)
    parser.add_argument("--admin-username", required=True)
    parser.add_argument("--operator-ref", required=True)
    parser.add_argument("--acknowledge-private-administration", action="store_true", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--status-only", action="store_true", help="Private read-back; never reconciles uncertain durability or reapplies")
    args = parser.parse_args(argv)
    engine = None
    try:
        approval = load_approval(args.approval_file, args.approval_sha256)
        if args.operator_ref != approval["operator_ref"]:
            raise ValueError("APPROVED_OPERATOR_REFERENCE_REQUIRED")
        if args.expected_database != LOCAL_DATABASE:
            raise ValueError("OFFICIAL_LOCAL_SESSION_DIRECTORY_REQUIRED")
        if args.status_only:
            if args.apply: raise ValueError("READ_BACK_ONLY_REQUIRED")
            events=decode(private_read(Path(args.ledger), missing=True))
            last=next((e for e in reversed(events) if e['grant_id']==approval['grant_id']),None)
            print(json.dumps({'status':'READ_BACK_ONLY','head_sha256':events[-1]['sha256'] if events else ZERO,
                              'grant_state':last['action'] if last else 'ABSENT','durability_reconciled':False}))
            return 0
        if not args.apply:
            event, prospective, _ = plan_only(approval, args.ledger, now=datetime.now(timezone.utc))
            print(json.dumps({"status":"PLAN_ONLY", "action":event["action"], "next_version":prospective["version"],
                              "issuer_authentication":"NOT_RUN", "registry_verification":"NOT_RUN", "grant_issued":False}))
            return 0
        from sqlalchemy import create_engine
        from src.qa.users import secret
        from src.repositories.application_boundary import ApplicationStore
        from src.repositories.application_migrations import ApplicationMigrator
        from src.services.local_authentication import LocalIdentityProvider
        dsn = os.environ.get("NADI_APPLICATION_ADMIN_DSN")
        if not dsn:
            raise ValueError("APPLICATION_ADMIN_DSN_REQUIRED")
        bind_directory(dsn, args.expected_database)
        engine = create_engine(dsn, echo=False, hide_parameters=True,
            connect_args={"connect_timeout":5,"options":"-c statement_timeout=15000 -c lock_timeout=5000"})
        store = ApplicationStore(engine, expected_database=args.expected_database, dedicated=True)
        from sqlalchemy import text
        with engine.connect() as c:
            identity = c.execute(text("SELECT current_database(), current_user")).one()
            if tuple(identity) != (LOCAL_DATABASE, LOCAL_ROLE):
                raise ValueError("OFFICIAL_LOCAL_SESSION_DIRECTORY_REQUIRED")
        if any(x["status"] != "APPLIED" for x in ApplicationMigrator(engine, expected_database=args.expected_database, dedicated=True).status()):
            raise ValueError("APPLICATION_SCHEMA_NOT_READY")
        provider = LocalIdentityProvider(store)
        actor = provider.authenticate(args.admin_username, secret("Administrator password: "))
        result = administer(provider, actor, approval, args.ledger,
                            now=datetime.now(timezone.utc), apply=args.apply)
        print(json.dumps(result))
        return 0
    except PolicyCommitUncertain as error:
        print(json.dumps({"status":"APPLY_STATE_REQUIRES_RECONCILIATION", "grant_may_be_live":True,
                          "version":error.event["version"], "head_sha256":error.event["sha256"],
                          "activation_permitted":False}))
        return 3
    except Exception:
        # Never expose DSNs, SQL exceptions, passwords, principal or plant data.
        print(json.dumps({"status":"DENIED", "code":"PRIVATE_FACTUAL_ADMINISTRATION_FAILED"}))
        return 2
    finally:
        if engine is not None: engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
