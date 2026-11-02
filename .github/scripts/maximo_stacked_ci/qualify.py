"""Separate development evidence; never replaces the main qualification gate.

Metadata jobs use a read-only token. Candidate test jobs never receive that token.
The qualification request is reviewed source, not an arbitrary ref/dispatch input.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parents[3]
PROFILE = ROOT / '.github/qualification/maximo-stacked-development.json'
spec = importlib.util.spec_from_file_location('unchanged_main_qualification',
    ROOT / '.github/scripts/maximo_ci/qualify.py')
main_policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main_policy)
REPOSITORY = main_policy.REPOSITORY
FIELDS = {'schema_version', 'purpose', 'repository', 'target_pr', 'target_sha', 'base_pr', 'base_sha'}


def validate_profile(value):
    if (not isinstance(value, dict) or set(value) != FIELDS
            or type(value['schema_version']) is not int or value['schema_version'] != 1
            or value['purpose'] != 'stacked-local-development-only'
            or type(value['target_pr']) is not int or type(value['base_pr']) is not int
            or not isinstance(value['target_sha'], str) or not isinstance(value['base_sha'], str)
            or value['target_pr'] == value['base_pr']):
        raise ValueError('INVALID_REVIEWED_DEVELOPMENT_REQUEST')
    for number, sha in [(value['target_pr'], value['target_sha']), (value['base_pr'], value['base_sha'])]:
        main_policy.validate_request(value['repository'], number, sha)
    return value


def validate_open(payload, number, sha):
    main_policy.validate_request(REPOSITORY, number, sha)
    if not isinstance(payload, dict):
        raise ValueError('PR_METADATA_INVALID')
    if (payload.get('number') != number or payload.get('state') != 'open'
            or payload.get('merged_at') is not None):
        raise ValueError('PR_NOT_OPEN_UNMERGED')
    for side in ('head', 'base'):
        if payload.get(side, {}).get('repo', {}).get('full_name') != REPOSITORY:
            raise ValueError('UNEXPECTED_PR_REPOSITORY')
    if payload.get('head', {}).get('sha') != sha:
        raise ValueError('STALE_PR_HEAD')


def validate_stack(request, candidate, parent):
    validate_profile(request)
    validate_open(candidate, request['target_pr'], request['target_sha'])
    validate_open(parent, request['base_pr'], request['base_sha'])
    base = candidate.get('base', {})
    if (base.get('ref') in (None, '', 'main')
            or base.get('ref') != parent.get('head', {}).get('ref')
            or base.get('sha') != request['base_sha']):
        raise ValueError('STACK_BASE_MISMATCH')
    return request


def fetch_pr(number):
    main_policy.validate_request(REPOSITORY, number, '0' * 40)
    req = urllib.request.Request(f'https://api.github.com/repos/{REPOSITORY}/pulls/{number}',
        headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
                 'Accept': 'application/vnd.github+json',
                 'X-GitHub-Api-Version': '2022-11-28'})
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            value = json.load(response)
    except Exception:
        raise ValueError('PR_METADATA_UNAVAILABLE') from None
    return value


def verify_policy_pins():
    pins = json.loads((Path(__file__).with_name('main-policy-pins.json')).read_text())
    for name, expected in pins.items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise ValueError('MAIN_POLICY_OR_REQUIRED_RUNNER_CHANGED')


def current():
    if (os.environ.get('GITHUB_REPOSITORY') != REPOSITORY
            or os.environ.get('GITHUB_EVENT_NAME') != 'pull_request'):
        raise ValueError('SAME_REPOSITORY_TOOLING_PR_REQUIRED')
    tools_sha = os.environ['TOOLS_SHA']
    requester = os.environ['REQUESTER_PR']
    # Tooling itself remains a main-target PR under the unchanged production rule.
    main_policy.current_pr(REPOSITORY, requester, tools_sha)
    main_policy.verify_checkout(ROOT, tools_sha)
    verify_policy_pins()
    request = validate_profile(json.loads(PROFILE.read_text()))
    return validate_stack(request, fetch_pr(request['target_pr']), fetch_pr(request['base_pr']))


def verify_source(source, sha, base):
    main_policy.validate_request(REPOSITORY, 1, base)
    main_policy.verify_checkout(source, sha)
    subprocess.run(['git', '-C', str(source), 'merge-base', '--is-ancestor', base, sha],
                   check=True, capture_output=True, timeout=20)


def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['select', 'recheck', 'checkout'])
    parser.add_argument('--source', type=Path)
    args = parser.parse_args()
    if args.mode == 'checkout':
        verify_source(args.source, os.environ['TESTED_SHA'], os.environ['BASE_SHA'])
        print('EXACT_CHECKOUT_AND_ANCESTRY_PASS')
        return
    request = current()
    digest = hashlib.sha256(PROFILE.read_bytes()).hexdigest()
    if args.mode == 'select':
        with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
            output.write(f"sha={request['target_sha']}\nbase_sha={request['base_sha']}\nprofile_sha256={digest}\n")
    elif (os.environ['TESTED_SHA'] != request['target_sha']
          or os.environ['BASE_SHA'] != request['base_sha']
          or os.environ['PROFILE_SHA256'] != digest):
        raise ValueError('DEVELOPMENT_SELECTION_CHANGED')
    print(json.dumps({'scope': request['purpose'], 'target_pr': request['target_pr'],
        'tested_sha': request['target_sha'], 'base_pr': request['base_pr'],
        'base_sha': request['base_sha'], 'tools_sha': os.environ['TOOLS_SHA'],
        'profile_sha256': digest, 'main_gate_replaced': False, 'deployment_authorized': False}))


if __name__ == '__main__':
    cli()
