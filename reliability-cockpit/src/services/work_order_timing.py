"""Conservative execution interval for the public read-only WO view."""
from datetime import datetime


def execution_interval(status, start, finish):
    if status != "CLOSE":
        return {"actual_timing_state": "NOT_CLOSED", "duration_hours": None}
    for name, value in (("START", start), ("FINISH", finish)):
        if value is None:
            return {"actual_timing_state": "MISSING_ACTUAL_" + name, "duration_hours": None}
        if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
            return {"actual_timing_state": "INVALID_OR_NAIVE_ACTUAL_" + name, "duration_hours": None}
    seconds = (finish - start).total_seconds()
    if seconds < 0:
        return {"actual_timing_state": "INVALID_ACTUAL_ORDER", "duration_hours": None}
    return {"actual_timing_state": "AVAILABLE", "duration_hours": seconds / 3600}
