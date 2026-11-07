"""Rolling WO report/creation-age eligibility; never use modification/activity dates.

The verified MXWODETAIL reportdate maps to reported_at. Four calendar years
are measured in Asia/Jakarta; Feb 29 clamps to Feb 28 in a non-leap target.
Unknown/naive/future source dates fail closed without rewriting retained data.
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from calendar import monthrange
from src.adapters.maximo.actual_dates import clock

ZONE = ZoneInfo("Asia/Jakarta")
YEARS = 4

def window(now=None):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("age window requires a timezone-aware clock")
    local = now.astimezone(ZONE)
    year = local.year - YEARS
    cutoff = local.replace(year=year, day=min(local.day, monthrange(year, local.month)[1]))
    return cutoff.astimezone(timezone.utc), now.astimezone(timezone.utc)

def eligibility(raw, bounds=None):
    cutoff, now = bounds or window()
    proof = clock(raw.get("reportdate"), present="reportdate" in raw)
    if proof["state"] != "VALID":
        return "AGE_UNKNOWN"
    value = datetime.fromisoformat(proof["normalized"])
    if value > now:
        return "AGE_UNKNOWN"
    return "AGE_EXCLUDED" if value < cutoff else "AGE_ELIGIBLE"
