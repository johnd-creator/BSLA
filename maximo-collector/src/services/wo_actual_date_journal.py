"""Private, presence-aware recovery journal. No database or source access.

Only the date write set is restorable. Whole-row snapshots remain diagnostic;
independent normal-worker changes are never copied from an old snapshot.
"""
from __future__ import annotations

import copy
from datetime import datetime, timezone
import hashlib
import json

from src.adapters.maximo.actual_dates import retained_values, version

FORMAT = "wo-actual-dates-journal/2"
PROOF = ("sources", "maximo", "actual_dates")
DATE_PATHS = {
    "legacy": (PROOF,),
    "mart": (("actual_start",), ("actual_finish",),
             ("sources", "maximo", "actstart"), ("sources", "maximo", "actfinish"), PROOF),
}


def digest(value):
    def encode(v):
        if isinstance(v, datetime):
            return version(v).astimezone(timezone.utc).isoformat()
        raise TypeError("unsupported journal value")
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=encode).encode()).hexdigest()


def signed(journal):
    result = copy.deepcopy(journal)
    result.pop("journal_sha256", None)
    result["journal_sha256"] = digest(result)
    return result


def validate(journal):
    core = {k: v for k, v in journal.items() if k != "journal_sha256"}
    if journal.get("format") != FORMAT or journal.get("journal_sha256") != digest(core):
        raise ValueError("unsupported or damaged recovery journal")
    if journal.get("state") not in ("PREPARED", "APPLIED", "ROLLBACK_PREPARED", "ROLLED_BACK"):
        raise ValueError("invalid recovery journal state")


def slot(document, path):
    current = document
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return {"present": False}
        current = current[key]
    return {"present": True, "value": copy.deepcopy(current)}


def same(a, b):
    return digest(a) == digest(b)


def date_guard(snapshot):
    return {side: [{"path": list(path), "slot": slot(snapshot[side], path)} for path in paths]
            for side, paths in DATE_PATHS.items()}


def _allowed(side, path):
    if side == "mart" and path in (("actual_start",), ("actual_finish",),
                                    ("sources", "maximo", "actstart"), ("sources", "maximo", "actfinish")):
        return True
    # Independently journal every known provenance leaf, including presence.
    if path[:3] != PROOF:
        return False
    tail = path[3:]
    return (tail == ("schema_version",)
            or len(tail) == 2 and tail[0] == "identity" and tail[1] in ("wonum", "assetnum", "siteid", "orgid")
            or len(tail) == 3 and tail[0] == "fields" and tail[1] in ("actstart", "actfinish")
            and tail[2] in ("state", "original", "normalized", "source_changed_at"))


def changes(before, after):
    """Derive and audit the *complete* write set, including new containers."""
    result, containers = [], []
    def walk(side, path, a, b):
        if same(a, b):
            return
        av, bv = a.get("value"), b.get("value")
        if isinstance(bv, dict) and (not a["present"] or av is None or isinstance(av, dict)):
            if not isinstance(av, dict):
                containers.append({"side": side, "path": list(path), "before": a})
            for key in sorted(set(av or {}) | set(bv)):
                walk(side, path + (key,), slot(av, (key,)), slot(bv, (key,)))
            return
        if side == "mart" and path == ("mart_updated_at",):
            return  # transaction metadata, advanced afresh on rollback
        if not _allowed(side, path):
            raise ValueError("recovery changed a field outside its date write set")
        result.append({"side": side, "path": list(path), "before": a, "after": b})
    for side in ("legacy", "mart"):
        walk(side, (), {"present": True, "value": before[side]}, {"present": True, "value": after[side]})
    return {"fields": result, "containers": containers}


def verify_entry(entry):
    # Recompute from sealed diagnostic snapshots. Never trust arbitrary paths.
    if not same(entry["write_set"], changes(entry["before"], entry["after"])):
        raise ValueError("journal write-set mismatch")
    if not same(entry["date_guard"], date_guard(entry["after"])):
        raise ValueError("journal date guard mismatch")


def authoritative_dates(snapshot, item):
    """An advanced row version alone never proves unchanged field evidence."""
    for side in ("legacy", "mart"):
        row = snapshot[side]
        proof = slot(row, PROOF).get("value")
        retained = retained_values(proof, item["wonum"], item["assetnum"], row["source_changed_at"])
        if set(retained) != {"actstart", "actfinish"}:
            return False
        if side == "mart":
            for key, field in (("actstart", "actual_start"), ("actfinish", "actual_finish")):
                if version(retained[key]) != version(row[field]):
                    return False
    return same(slot(snapshot["legacy"], PROOF), slot(snapshot["mart"], PROOF))


def _put(document, path, value):
    current = document
    for key in path[:-1]:
        if not isinstance(current.get(key), dict):
            raise ValueError("rollback container conflict")
        current = current[key]
    if value["present"]:
        current[path[-1]] = copy.deepcopy(value["value"])
    else:
        current.pop(path[-1], None)


def restored(snapshot, entry):
    result = copy.deepcopy(snapshot)
    for change in entry["write_set"]["fields"]:
        _put(result[change["side"]], change["path"], change["before"])
    for container in reversed(entry["write_set"]["containers"]):
        side, path = container["side"], container["path"]
        # A worker may have added independent siblings. Keep that container.
        if slot(result[side], path).get("value") == {}:
            _put(result[side], path, container["before"])
    return result
