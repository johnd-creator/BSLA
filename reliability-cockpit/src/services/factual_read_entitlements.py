"""Private application READ policy. Never modifies directory/Engineering/Mart grants.

The OS custodian is trusted. Hash chains detect corruption, not rollback by that
custodian: never restore this ledger from source/data backups. Revoke in place.
Canonical NDJSON rejects duplicate keys, non-finite numbers and ambiguous encodings.
"""
from datetime import datetime, timezone
from hashlib import sha256
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import tempfile

CAPABILITIES = {"FACTUAL_DASHBOARD_READ", "FACTUAL_ASSET_READ", "FACTUAL_MAINTENANCE_READ"}
ISSUER = "local:c759c2d1-19a4-4291-9b66-9218dbd12dea"
ZERO = "0" * 64
MAX_BYTES = 4 * 1024 * 1024
MAX_ISSUES = 200
FIELDS = {"action", "version", "previous_sha256", "grant_id", "subject", "assets",
          "capabilities", "not_before", "expires_at", "actor", "approval_ref",
          "operator_ref", "at", "sha256"}


class PolicyCommitUncertain(RuntimeError):
    def __init__(self, event):
        super().__init__("FACTUAL_POLICY_COMMIT_REQUIRES_RECONCILIATION")
        self.event = event


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def timestamp(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", value):
        raise ValueError("FACTUAL_POLICY_TIME_INVALID")
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def instant(value):
    return value.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def validate_event(e):
    if not isinstance(e, dict) or set(e) != FIELDS:
        raise ValueError("FACTUAL_POLICY_FIELDS_INVALID")
    if e["action"] not in {"ISSUE", "REVOKE"} or type(e["version"]) is not int or e["version"] < 1:
        raise ValueError("FACTUAL_POLICY_EVENT_INVALID")
    for key in ("previous_sha256", "sha256"):
        if not isinstance(e[key], str) or not re.fullmatch(r"[a-f0-9]{64}", e[key]):
            raise ValueError("FACTUAL_POLICY_DIGEST_INVALID")
    for key in ("subject", "actor"):
        if not isinstance(e[key], str) or not re.fullmatch(r"local:[A-Za-z0-9-]{1,150}", e[key]):
            raise ValueError("FACTUAL_POLICY_SUBJECT_INVALID")
    if e["actor"] != ISSUER or e["subject"] == e["actor"]:
        raise ValueError("FACTUAL_ISSUER_DENIED")
    for key in ("grant_id", "approval_ref", "operator_ref"):
        if not isinstance(e[key], str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,160}", e[key]):
            raise ValueError("FACTUAL_POLICY_REFERENCE_INVALID")
    assets, caps = e["assets"], e["capabilities"]
    if (not isinstance(assets, list) or not 1 <= len(assets) <= 20
            or any(not isinstance(a, str) or not re.fullmatch(r"asset:MAXIMO:MXASSET:BSR:IP:[A-Za-z0-9_.-]{1,120}", a) for a in assets)
            or assets != sorted(set(assets))):
        raise ValueError("FACTUAL_POLICY_ASSETS_INVALID")
    if (not isinstance(caps, list) or not caps or any(not isinstance(c, str) or c not in CAPABILITIES for c in caps)
            or caps != sorted(set(caps))):
        raise ValueError("FACTUAL_POLICY_CAPABILITIES_INVALID")
    start, end, at = (timestamp(e[k]) for k in ("not_before", "expires_at", "at"))
    if not 0 < (end-start).total_seconds() <= 86400:
        raise ValueError("FACTUAL_POLICY_EXPIRY_INVALID")
    if e["action"] == "ISSUE" and not 0 <= (at-start).total_seconds() <= 3600:
        raise ValueError("FACTUAL_POLICY_ISSUANCE_TIME_INVALID")
    unsigned = {k: v for k, v in e.items() if k != "sha256"}
    if sha256(canonical(unsigned).encode()).hexdigest() != e["sha256"]:
        raise ValueError("FACTUAL_POLICY_HASH_INVALID")


def decode(data):
    if not isinstance(data, bytes) or len(data) > MAX_BYTES or not data.endswith(b"\n"):
        raise ValueError("FACTUAL_POLICY_SIZE_INVALID")
    lines = data.decode("ascii").splitlines()
    if ("\n".join(lines)+"\n").encode("ascii") != data:
        raise ValueError("FACTUAL_POLICY_CANONICAL_LF_REQUIRED")
    if not lines or lines[0] != '{"schema_version":1}' or len(lines) > 1 + MAX_ISSUES * 2:
        raise ValueError("FACTUAL_POLICY_FORMAT_INVALID")
    events, states, previous = [], {}, ZERO
    for line in lines[1:]:
        e = json.loads(line)
        if canonical(e) != line:
            raise ValueError("FACTUAL_POLICY_NONCANONICAL")
        validate_event(e)
        if e["version"] != len(events)+1 or e["previous_sha256"] != previous:
            raise ValueError("FACTUAL_POLICY_CHAIN_INVALID")
        old = states.get(e["grant_id"])
        if e["action"] == "ISSUE":
            if old or sum(x["action"] == "ISSUE" for x in events) >= MAX_ISSUES:
                raise ValueError("FACTUAL_POLICY_ISSUE_DENIED")
        elif not old or old["action"] != "ISSUE" or any(e[k] != old[k] for k in
                ("subject", "assets", "capabilities", "not_before", "expires_at")):
            raise ValueError("FACTUAL_POLICY_REVOKE_DENIED")
        if events and timestamp(e["at"]) < timestamp(events[-1]["at"]):
            raise ValueError("FACTUAL_POLICY_CLOCK_REGRESSION")
        states[e["grant_id"]] = e
        events.append(e)
        previous = e["sha256"]
    return events


def private_parent(path):
    path = Path(path)
    parent = path.parent
    s = parent.lstat()
    if (not path.is_absolute() or path.resolve() != path or parent.resolve() != parent
            or not stat.S_ISDIR(s.st_mode) or s.st_uid != os.getuid() or stat.S_IMODE(s.st_mode) != 0o700):
        raise ValueError("PRIVATE_FACTUAL_POLICY_DIRECTORY_REQUIRED")
    return path


def private_read(path, *, missing=False):
    path = private_parent(path)
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        if missing:
            return b'{"schema_version":1}\n'
        raise
    with os.fdopen(fd, "rb") as f:
        s = os.fstat(f.fileno())
        if not stat.S_ISREG(s.st_mode) or s.st_nlink != 1 or s.st_uid != os.getuid() or stat.S_IMODE(s.st_mode) != 0o600 or s.st_size > MAX_BYTES:
            raise ValueError("PRIVATE_FACTUAL_POLICY_FILE_REQUIRED")
        return f.read(MAX_BYTES+1)


def append_event(path, event, *, expected_head):
    """CAS + stable flock + same-directory atomic replace; reserves all revocations."""
    path = private_parent(path)
    lock_fd = os.open(str(path)+".lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    with os.fdopen(lock_fd, "rb") as lock:
        s = os.fstat(lock.fileno())
        if not stat.S_ISREG(s.st_mode) or s.st_nlink != 1 or s.st_uid != os.getuid() or stat.S_IMODE(s.st_mode) != 0o600:
            raise ValueError("PRIVATE_FACTUAL_LOCK_REQUIRED")
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        data = private_read(path, missing=True)
        events = decode(data)
        head = events[-1]["sha256"] if events else ZERO
        if expected_head != head:
            raise ValueError("FACTUAL_POLICY_HEAD_CONFLICT")
        event = {**event, "version":len(events)+1, "previous_sha256":head}
        event["sha256"] = sha256(canonical(event).encode()).hexdigest()
        result = data + canonical(event).encode() + b"\n"
        decode(result)
        # Compact limit is deliberately chosen so every issued grant has revoke capacity.
        fd, temp = tempfile.mkstemp(prefix=".factual-policy-", dir=path.parent)
        replaced = False
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(result); f.flush(); os.fsync(f.fileno())
            os.replace(temp, path)
            replaced = True
            directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try: os.fsync(directory)
            finally: os.close(directory)
        except Exception:
            if replaced:
                raise PolicyCommitUncertain(event) from None
            raise
        finally:
            if os.path.exists(temp): os.unlink(temp)
        return event
