"""Read-only source selection; never execute a ref supplied by the caller."""
import argparse
import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

# GitHub repository id 1339119929, renamed in place; retain an exact-name gate.
REPOSITORY = "johnd-creator/BSLA"
SHA = re.compile(r"[0-9a-f]{40}\Z")


def validate_request(repository, number, expected):
    if repository != REPOSITORY:
        raise ValueError("UNEXPECTED_REPOSITORY")
    if not re.fullmatch(r"[1-9][0-9]{0,8}", str(number)):
        raise ValueError("INVALID_PR_NUMBER")
    if not SHA.fullmatch(expected):
        raise ValueError("EXPECTED_FULL_COMMIT_SHA_REQUIRED")


def validate_pr(payload, repository, number, expected):
    validate_request(repository, number, expected)
    if payload.get("number") != int(number):
        raise ValueError("WRONG_PR")
    if payload.get("state") != "open" or payload.get("merged_at") is not None:
        raise ValueError("PR_NOT_OPEN_UNMERGED")
    for side in ("head", "base"):
        if payload.get(side, {}).get("repo", {}).get("full_name") != repository:
            raise ValueError("UNEXPECTED_PR_REPOSITORY")
    if payload.get("base", {}).get("ref") != "main":
        raise ValueError("UNSUPPORTED_PR_BASE")
    if payload.get("head", {}).get("sha") != expected:
        raise ValueError("STALE_PR_HEAD")
    return expected


def current_pr(repository, number, expected):
    validate_request(repository, number, expected)
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repository}/pulls/{number}",
        headers={"Authorization": "Bearer " + os.environ["GH_TOKEN"],
                 "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.load(response)
    except (urllib.error.URLError, ValueError):
        raise ValueError("PR_METADATA_UNAVAILABLE") from None
    return validate_pr(payload, repository, number, expected)


def select(event, payload, repository, ref, event_sha, number="", expected=""):
    if repository != REPOSITORY:
        raise ValueError("UNEXPECTED_REPOSITORY")
    if event == "workflow_dispatch":
        if ref != "refs/heads/main":
            raise ValueError("DISPATCH_REQUIRES_DEFAULT_BRANCH_WORKFLOW")
        validate_request(repository, number, expected)
        return number, expected
    if event == "pull_request":
        number = str(payload["number"])
        expected = payload["pull_request"]["head"]["sha"]
        validate_pr(payload["pull_request"], repository, number, expected)
        return number, expected
    if event == "push" and ref == "refs/heads/main" and SHA.fullmatch(event_sha):
        return "", event_sha
    raise ValueError("UNSUPPORTED_EVENT_OR_REF")


def verify_checkout(path, expected):
    if not SHA.fullmatch(expected):
        raise ValueError("EXPECTED_FULL_COMMIT_SHA_REQUIRED")
    def git(*args):
        return subprocess.check_output(["git", "-C", str(path), *args], text=True).strip()
    if git("rev-parse", "HEAD") != expected:
        raise ValueError("CHECKOUT_SHA_MISMATCH")
    if git("remote", "get-url", "origin") != f"https://github.com/{REPOSITORY}":
        raise ValueError("CHECKOUT_REPOSITORY_MISMATCH")
    if git("status", "--porcelain", "--untracked-files=no"):
        raise ValueError("DIRTY_TRACKED_SOURCE")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("select", "recheck", "checkout"))
    parser.add_argument("--source", type=Path)
    args = parser.parse_args()
    repository = os.environ["GITHUB_REPOSITORY"]
    if args.mode == "select":
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
        number, expected = select(
            os.environ["GITHUB_EVENT_NAME"], event, repository,
            os.environ["GITHUB_REF"], os.environ["GITHUB_SHA"],
            os.environ.get("REQUEST_PR", ""), os.environ.get("REQUEST_SHA", ""),
        )
        if number:
            current_pr(repository, number, expected)
        with open(os.environ["GITHUB_OUTPUT"], "a") as output:
            output.write(f"sha={expected}\npr={number}\n")
        print(json.dumps({"selected_sha": expected, "pr": number or None}))
    elif args.mode == "recheck":
        number, expected = os.environ.get("SELECTED_PR", ""), os.environ["TESTED_SHA"]
        if number:
            current_pr(repository, number, expected)
        print("PR_HEAD_RECHECK_PASS" if number else "MAIN_PUSH_SOURCE")
    else:
        verify_checkout(args.source, os.environ["TESTED_SHA"])
        print("EXACT_CHECKOUT_PASS")


if __name__ == "__main__":
    main()
