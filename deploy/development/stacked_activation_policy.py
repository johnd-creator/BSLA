"""Optional, owner-approved LOCAL qualification equivalence. Never deploys or grants.

Production main-only checks remain authoritative for production. This separate
preflight accepts only the reviewed nonprivileged workflow, exact source/dependency,
full zero-skip matrix, fresh metadata and an exact private owner approval/review.
No candidate code executes in this verifier. No token is written into a receipt.
"""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import urllib.parse
import urllib.request
import zipfile

REPOSITORY = "johnd-creator/reliability-knowledge-starter"
TRUST = Path(__file__).with_name("stacked_qualification_trust.json")
PROFILE = ".github/qualification/maximo-stacked-development.json"
REQUEST_FIELDS = {"target_pr", "target_sha", "base_pr", "base_sha", "tooling_pr", "tooling_sha",
                  "run_id", "engineering_run_id"}


def digest(data): return hashlib.sha256(data).hexdigest()


def policy_bundle_digest():
    return digest((digest(Path(__file__).read_bytes())+":"+digest(TRUST.read_bytes())).encode())


def private_json(path, expected):
    path = Path(path)
    if not path.is_absolute() or path.resolve() != path:
        raise ValueError("PRIVATE_OWNER_APPROVAL_REQUIRED")
    parent=path.parent.lstat()
    if not stat.S_ISDIR(parent.st_mode) or parent.st_uid!=os.getuid() or stat.S_IMODE(parent.st_mode)!=0o700:
        raise ValueError("PRIVATE_OWNER_APPROVAL_REQUIRED")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as f:
        s = os.fstat(f.fileno())
        if not stat.S_ISREG(s.st_mode) or s.st_uid != os.getuid() or s.st_nlink != 1 or stat.S_IMODE(s.st_mode) != 0o600 or s.st_size > 128*1024:
            raise ValueError("PRIVATE_OWNER_APPROVAL_REQUIRED")
        data = f.read(128*1024+1)
    if len(data)>128*1024 or digest(data) != expected:
        raise ValueError("OWNER_APPROVAL_DIGEST_MISMATCH")
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError("AMBIGUOUS_OWNER_APPROVAL")
            result[key]=value
        return result
    def nonfinite(value):raise ValueError("NONFINITE_OWNER_APPROVAL")
    return json.loads(data,object_pairs_hook=unique,parse_constant=nonfinite)


def exact_pr(value, number, sha):
    if (value.get("number") != number or value.get("state") != "open" or value.get("merged_at") is not None
            or value.get("head", {}).get("sha") != sha
            or any(value.get(side, {}).get("repo", {}).get("full_name") != REPOSITORY for side in ("head", "base"))):
        raise ValueError("CURRENT_EXACT_SAME_REPOSITORY_PR_REQUIRED")


def exact_run(value, sha, workflow):
    if (value.get("head_sha") != sha or value.get("event") != "pull_request"
            or value.get("path") != workflow or value.get("status") != "completed"
            or value.get("conclusion") != "success"
            or value.get("repository", {}).get("full_name") != REPOSITORY):
        raise ValueError("EXACT_SUCCESSFUL_PR_WORKFLOW_REQUIRED")


def required_jobs(value, names):
    if value.get("total_count") != len(names) or len(value.get("jobs", [])) != len(names):
        raise ValueError("COMPLETE_JOB_SET_REQUIRED")
    jobs = {job["name"]:job for job in value["jobs"]}
    if set(jobs) != names or any(j.get("status") != "completed" or j.get("conclusion") != "success" for j in jobs.values()):
        raise ValueError("ALL_REQUIRED_JOBS_MUST_PASS")
    return jobs


def verify_receipts(api, run, request, workflow_sha):
    artifacts = api.json(f"actions/runs/{run}/artifacts?per_page=100")
    if artifacts.get("total_count") != 2 or len(artifacts.get("artifacts", [])) != 2:
        raise ValueError("COMPLETE_MATRIX_RECEIPTS_REQUIRED")
    seen = set()
    for artifact in artifacts["artifacts"]:
        match = re.fullmatch(r"stacked-development-(3\.11|3\.12)-"+request["target_sha"], artifact.get("name", ""))
        if not match or match[1] in seen or artifact.get("expired") or artifact.get("workflow_run", {}).get("head_sha") != request["tooling_sha"]:
            raise ValueError("EXACT_MATRIX_ARTIFACT_REQUIRED")
        python = match[1]; seen.add(python)
        data = api.artifact(artifact["id"])
        if len(data)>128*1024 or artifact.get("digest") != "sha256:"+digest(data):
            raise ValueError("ARTIFACT_DIGEST_MISMATCH")
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            expected = {f"{kind}-{python}.json" for kind in ("collector", "contracts", "rehearsal")}
            if len(archive.infolist()) != 3 or set(archive.namelist()) != expected or sum(x.file_size for x in archive.infolist())>128*1024:
                raise ValueError("BOUNDED_SYNTHETIC_RECEIPTS_REQUIRED")
            for kind, tests in (("collector",206),("contracts",14),("rehearsal",6)):
                receipt = json.loads(archive.read(f"{kind}-{python}.json"))
                if (receipt.get("tested_sha") != request["target_sha"] or receipt.get("conclusion") != "PASS"
                        or receipt.get("workflow_sha") != workflow_sha
                        or not str(receipt.get("python", "")).startswith(python+".")
                        or receipt.get("run_url") != f"https://github.com/{REPOSITORY}/actions/runs/{run}"
                        or receipt.get("tests") != tests or receipt.get("discovered") != tests
                        or receipt.get("infrastructure_error") is not False
                        or any(type(receipt.get(k)) is not int or receipt[k] != 0 for k in
                            ("failures", "errors", "skips", "expected_failures", "blocked_external_io"))
                        or kind == "rehearsal" and receipt.get("owned_root_removed") is not True):
                    raise ValueError("COMPLETE_ZERO_SKIP_EXACT_HEAD_RECEIPT_REQUIRED")
    if seen != {"3.11", "3.12"}: raise ValueError("COMPLETE_PYTHON_MATRIX_REQUIRED")


def verify_evidence(api, request, trust=None):
    if not isinstance(request, dict) or set(request) != REQUEST_FIELDS:
        raise ValueError("CLOSED_QUALIFICATION_REQUEST_REQUIRED")
    for k in ("target_pr", "base_pr", "tooling_pr", "run_id", "engineering_run_id"):
        if type(request[k]) is not int or request[k] < 1: raise ValueError("POSITIVE_IDENTIFIER_REQUIRED")
    for k in ("target_sha", "base_sha", "tooling_sha"):
        if not isinstance(request[k],str) or not re.fullmatch(r"[a-f0-9]{40}",request[k]): raise ValueError("EXACT_SHA_REQUIRED")
    if request["target_pr"] != 120 or request["base_pr"] != 119 or request["tooling_pr"] != 121:
        raise ValueError("APPROVED_PR120_STACK_REQUIRED")
    trust = trust or json.loads(TRUST.read_text())
    before = [api.json(f"pulls/{request[k+'_pr']}") for k in ("target", "base", "tooling")]
    for key, metadata in zip(("target", "base", "tooling"), before): exact_pr(metadata, request[key+"_pr"], request[key+"_sha"])
    if (before[0]["base"]["sha"] != request["base_sha"] or before[0]["base"]["ref"] != before[1]["head"]["ref"]
            or before[0]["base"]["ref"] == "main" or before[2]["base"]["ref"] != "main"):
        raise ValueError("EXACT_REVIEWED_STACK_REQUIRED")
    # These ten code/policy files are the independently reviewed immutable PR121 tools.
    for name, expected in trust["files"].items():
        blob = api.json("contents/"+name+"?ref="+request["tooling_sha"])
        if blob.get("encoding") != "base64" or digest(base64.b64decode(blob["content"])) != expected:
            raise ValueError("REVIEWED_QUALIFICATION_TOOLS_CHANGED")
    profile_blob = api.json("contents/"+PROFILE+"?ref="+request["tooling_sha"])
    profile = json.loads(base64.b64decode(profile_blob["content"]))
    if profile != {"schema_version":1,"purpose":"stacked-local-development-only","repository":REPOSITORY,
                   "target_pr":120,"target_sha":request["target_sha"],"base_pr":119,"base_sha":request["base_sha"]}:
        raise ValueError("EXACT_REVIEWED_PROFILE_REQUIRED")
    run = api.json(f"actions/runs/{request['run_id']}")
    exact_run(run, request["tooling_sha"], ".github/workflows/nadi-maximo-stacked-development.yml")
    jobs = required_jobs(api.json(f"actions/runs/{request['run_id']}/jobs?per_page=100&filter=latest"),
                         {"select","qualify (3.11)","qualify (3.12)","Maximo stacked development evidence gate"})
    steps = jobs["Maximo stacked development evidence gate"].get("steps", [])
    if not any(s.get("name") == "Fresh metadata recheck without executing candidate code" and s.get("conclusion") == "success" for s in steps):
        raise ValueError("FRESH_FINAL_METADATA_GATE_REQUIRED")
    if not re.fullmatch(r"[a-f0-9]{40}",before[2].get("merge_commit_sha", "")):
        raise ValueError("CURRENT_REVIEWED_WORKFLOW_MERGE_ID_REQUIRED")
    verify_receipts(api, request["run_id"], request, before[2]["merge_commit_sha"])
    engineering = api.json(f"actions/runs/{request['engineering_run_id']}")
    exact_run(engineering, request["target_sha"], ".github/workflows/nadi-engineering-candidate.yml")
    required_jobs(api.json(f"actions/runs/{request['engineering_run_id']}/jobs?per_page=100&filter=latest"), {"backend","frontend"})
    # Refuse moving heads after downloads. The trusted workflow itself checks ancestry twice.
    for key, old in zip(("target", "base", "tooling"), before):
        fresh = api.json(f"pulls/{request[key+'_pr']}"); exact_pr(fresh, request[key+"_pr"], request[key+"_sha"])
        if fresh["head"] != old["head"] or fresh["base"] != old["base"]: raise ValueError("QUALIFICATION_METADATA_CHANGED")
    return {"status":"DEVELOPMENT_EVIDENCE_PASS","request":request,"production_gate_replaced":False,"grant_authorized":False,"activation_authorized":False}


def recognize(evidence, approval, review, *, now, policy_digest, review_digest):
    fields={"schema_version","purpose","request","approval_ref","approved_by","expires_at","policy_sha256","review_sha256"}
    if (not isinstance(approval,dict) or set(approval)!=fields or type(approval["schema_version"]) is not int
            or approval["schema_version"]!=1 or approval["purpose"]!="LOCAL_DEVELOPMENT_ONLY"
            or approval["request"]!=evidence["request"] or evidence["status"]!="DEVELOPMENT_EVIDENCE_PASS"
            or approval["policy_sha256"]!=policy_digest or approval["review_sha256"]!=review_digest
            or not isinstance(approval["approval_ref"],str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,160}",approval["approval_ref"])
            or approval["approved_by"]!="local:c759c2d1-19a4-4291-9b66-9218dbd12dea"):
        raise ValueError("EXPLICIT_EXACT_LOCAL_POLICY_APPROVAL_REQUIRED")
    end=datetime.fromisoformat(approval["expires_at"].replace("Z","+00:00"))
    if end.tzinfo is None or not 0<(end-now).total_seconds()<=86400: raise ValueError("FRESH_LOCAL_POLICY_APPROVAL_REQUIRED")
    if review.get("status")!="PASS" or review.get("target_sha")!=evidence["request"]["target_sha"] or review.get("independent") is not True or review.get("security_review_complete") is not True:
        raise ValueError("INDEPENDENT_EXACT_HEAD_SECURITY_REVIEW_REQUIRED")
    return {**evidence,"status":"LOCAL_DEVELOPMENT_QUALIFICATION_RECOGNIZED","owner_approval_ref":approval["approval_ref"],
            "policy_sha256":policy_digest,"review_sha256":review_digest,"other_activation_gates_required":True}


class GitHub:
    def __init__(self, token): self.token=token

    def read(self, suffix, limit, *, artifact=False):
        url=f"https://api.github.com/repos/{REPOSITORY}/"+suffix
        class Redirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                parsed=urllib.parse.urlsplit(newurl)
                if (not artifact or parsed.scheme!="https" or not parsed.hostname
                        or not parsed.hostname.endswith((".blob.core.windows.net",".githubusercontent.com",".actions.githubusercontent.com"))):
                    raise ValueError("GITHUB_REDIRECT_DENIED")
                # Never forward the metadata token to artifact storage.
                return urllib.request.Request(newurl,headers={"Accept":"application/octet-stream"})
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),Redirect())
        request=urllib.request.Request(url,headers={"Authorization":"Bearer "+self.token,"Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28"})
        with opener.open(request,timeout=20) as response:
            data=response.read(limit+1)
            if len(data)>limit: raise ValueError("BOUNDED_GITHUB_EVIDENCE_REQUIRED")
            return data

    def json(self,suffix): return json.loads(self.read(suffix,1024*1024))
    def artifact(self,identifier):
        if type(identifier) is not int or identifier<1: raise ValueError("ARTIFACT_ID_REQUIRED")
        return self.read(f"actions/artifacts/{identifier}/zip",128*1024,artifact=True)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--approval",required=True);p.add_argument("--approval-sha256",required=True)
    p.add_argument("--review",required=True);p.add_argument("--review-sha256",required=True)
    a=p.parse_args(argv)
    try:
        approval=private_json(a.approval,a.approval_sha256);review=private_json(a.review,a.review_sha256)
        token=os.environ.get("GH_TOKEN")
        if not token: raise ValueError("READ_ONLY_GITHUB_METADATA_TOKEN_REQUIRED")
        evidence=verify_evidence(GitHub(token),approval["request"])
        result=recognize(evidence,approval,review,now=datetime.now(timezone.utc),policy_digest=policy_bundle_digest(),review_digest=a.review_sha256)
        print(json.dumps(result,sort_keys=True));return 0
    except Exception:
        print(json.dumps({"status":"BLOCKED","code":"LOCAL_DEVELOPMENT_QUALIFICATION_NOT_RECOGNIZED"}));return 2


if __name__=="__main__":raise SystemExit(main())
