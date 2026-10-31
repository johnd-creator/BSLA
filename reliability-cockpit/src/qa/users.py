"""Explicit operator CLI. No startup bootstrap, dotenv, default account or passwords in argv.

Uses a separately approved application administrative DSN, never Mart or source keys.
Real provisioning requires separate operator authorization (see runbook).
"""
import argparse
import getpass
import json
import os
import sys
from sqlalchemy import create_engine
from src.repositories.application_boundary import ApplicationStore
from src.repositories.application_migrations import ApplicationMigrator
from src.services.local_authentication import LocalIdentityProvider, PasswordPolicy
from src.domain.engineering import EngineeringError


def secret(prompt):
    if not sys.stdin.isatty():
        raise EngineeringError("PRIVATE_INTERACTIVE_INPUT_REQUIRED", 400)
    return getpass.getpass(prompt)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-database", required=True)
    parser.add_argument("--operator-ref", required=True)
    parser.add_argument("--acknowledge-private-administration", action="store_true", required=True)
    parser.add_argument("--minimum-password-length", type=int, default=15)
    parser.add_argument("--admin-username")
    parser.add_argument("--username")
    parser.add_argument("--target-user-id")
    parser.add_argument("--expected-username")
    parser.add_argument("--new-username")
    parser.add_argument("--demo-password-profile", help="Explicit private verified four-account demo profile; replacement passwords only")
    parser.add_argument("--roles", nargs="*", choices=["ADMIN","AUTHOR","REVIEWER"])
    parser.add_argument("--assets", nargs="*")
    parser.add_argument("action", choices=["bootstrap","create","disable","reactivate","reset-password","rename","grants","revoke-sessions","audit"])
    args = parser.parse_args(argv)
    engine = None
    try:
        if not args.acknowledge_private_administration or not args.operator_ref.strip():
            raise EngineeringError("OPERATOR_REFERENCE_REQUIRED", 400)
        # No fallback, no embedded default DSN, never output URL/DB exceptions.
        dsn = os.environ.get("NADI_APPLICATION_ADMIN_DSN", "")
        if not dsn:
            raise EngineeringError("APPLICATION_ADMIN_DSN_REQUIRED", 503)
        engine = create_engine(dsn, echo=False, hide_parameters=True,
            connect_args={"connect_timeout":5,"options":"-c statement_timeout=15000 -c lock_timeout=5000"})
        store = ApplicationStore(engine, expected_database=args.expected_database, dedicated=True)
        if any(s["status"] != "APPLIED" for s in ApplicationMigrator(engine,expected_database=args.expected_database,dedicated=True).status()):
            raise EngineeringError("APPLICATION_SCHEMA_NOT_READY", 503)
        demo_profile = None
        if args.demo_password_profile:
            if args.action != 'reset-password':
                raise EngineeringError('DEMO_PROFILE_REPLACEMENT_ONLY', 400)
            from src.services.local_demo_accounts import load_demo_profile
            demo_profile = load_demo_profile(args.demo_password_profile, engine)
        provider = LocalIdentityProvider(store,policy=PasswordPolicy(minimum_length=args.minimum_password_length),
                                         demo_profile=demo_profile)
        if args.action == "bootstrap":
            password = secret("New administrator password: ")
            if password != secret("Confirm password: "):
                raise EngineeringError("PASSWORD_CONFIRMATION_FAILED",400)
            user = provider.bootstrap(username=args.username,password=password,assets=args.assets or [],operator_ref=args.operator_ref)
            result = {"status":"ACCOUNT_CREATED","user_id":user}
        else:
            grant = provider.authenticate(args.admin_username, secret("Administrator password: "))
            actor = grant
            if args.action == "audit":
                result = {"events":provider.security_events(actor)}
            elif args.action == 'rename':
                provider.rename_account(actor,args.target_user_id,
                    expected_username=args.expected_username,new_username=args.new_username)
                result = {'status':'ACCOUNT_RENAMED','user_id':args.target_user_id}
            elif args.action == "create":
                password = secret("New account temporary password: ")
                if password != secret("Confirm password: "):
                    raise EngineeringError("PASSWORD_CONFIRMATION_FAILED",400)
                result = {"status":"ACCOUNT_CREATED","user_id":provider.create_account(actor,username=args.username,
                    password=password,roles=args.roles or [],assets=args.assets or [])}
            else:
                kwargs = {}
                if args.action in {"disable","reactivate"}:
                    kwargs["active"] = args.action == "reactivate"
                elif args.action == "reset-password":
                    password = secret("New temporary password: ")
                    if password != secret("Confirm password: "):
                        raise EngineeringError("PASSWORD_CONFIRMATION_FAILED",400)
                    kwargs["password"] = password
                elif args.action == "grants":
                    kwargs.update(roles=args.roles,assets=args.assets)
                elif args.action == "revoke-sessions":
                    kwargs["revoke"] = True
                provider.change_account(actor,args.target_user_id,**kwargs)
                result = {"status":"ACCOUNT_UPDATED"}
        print(json.dumps(result,default=str))
        return 0
    except EngineeringError as error:
        print(json.dumps({"status":"DENIED","code":error.code}))
        return 2
    except Exception:
        print(json.dumps({"status":"DENIED","code":"PRIVATE_ADMINISTRATION_FAILED"}))
        return 2
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
