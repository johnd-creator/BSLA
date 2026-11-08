"""One shared page-demand coordinator. No database, registry discovery or DCS writes."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import math
import re
import secrets
import threading
import time
from typing import Protocol

IDENTIFIER = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
OWNER = re.compile(r"^[a-f0-9]{64}$")
QUALITY = {"good", "bad", "uncertain", "no_data", "invalid", "read_error"}


def iso(value: float) -> str:
    return datetime.fromtimestamp(value, timezone.utc).isoformat().replace("+00:00", "Z")


def epoch(value):
    if not isinstance(value, str) or len(value) > 40:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.timestamp() if dt.tzinfo else None
    except (ValueError, OverflowError):
        return None


@dataclass(frozen=True)
class Tag:
    key: str
    label: str
    unit: str


@dataclass(frozen=True)
class Reading:
    value: float | None
    source_at: str | None
    quality: str


class HistorianSource(Protocol):
    """Adapters MUST be read-only, allowlisted, size/rate limited and honor deadline.

    Production adapters require separate verified source/mapping/credential approval.
    Source timestamps are never replaced with retrieval time. No fallback/discovery.
    """
    mode: str

    def snapshot(self, tags: tuple[str, ...], *, deadline: float) -> dict[str, Reading]: ...

    def history(self, tag: str, start: float, end: float, limit: int,
                *, deadline: float) -> list[Reading]: ...


class SimulatedSource:
    mode = "simulation"

    def snapshot(self, tags, *, deadline):
        now = time.time()
        return {tag: Reading(round(10 + sum(map(ord, tag)) % 7 + math.sin(now / 30), 3), iso(now), "good")
                for tag in tags}

    def history(self, tag, start, end, limit, *, deadline):
        count = min(limit, max(1, int((end - start) / 5) + 1))
        return [Reading(round(10 + sum(map(ord, tag)) % 7 + math.sin((start + (end - start) * i / max(1, count - 1)) / 30), 3),
                        iso(start + (end - start) * i / max(1, count - 1)), "good")
                for i in range(count)]


class DemandError(Exception):
    def __init__(self, code: str, status: int = 422):
        self.code, self.status = code, status
        super().__init__(code)


@dataclass
class Lease:
    owner: str
    client: str
    page: str
    expires: float


class Coordinator:
    """Singleton per gateway process; one sampler handles all browser viewers.

    tick() is called by one background loop, never by subscribe/heartbeat.
    Locks protect refcounts/cache; source I/O runs outside the cache lock.
    """
    def __init__(self, source: HistorianSource, tags: list[Tag], pages: dict[str, tuple[str, ...]],
                 *, sample_seconds=4, context_tags=(), lease_seconds=20, grace_seconds=10,
                 max_leases=256, clock=time.monotonic, wall=time.time):
        if source.mode != "simulation":
            raise ValueError("Only the explicit simulation adapter is permitted in this foundation")
        if not 3 <= sample_seconds <= 5 or not 15 <= lease_seconds <= 60 or not 0 <= grace_seconds <= 30:
            raise ValueError("Invalid timing bounds")
        if not 1 <= len(tags) <= 128 or not 1 <= len(pages) <= 32 or not 1 <= max_leases <= 256:
            raise ValueError("Invalid capacity")
        self.tags = {t.key: t for t in tags}
        if len(self.tags) != len(tags) or any(not IDENTIFIER.fullmatch(t.key) or not 1 <= len(t.label) <= 160 or len(t.unit) > 40 for t in tags):
            raise ValueError("Invalid tag catalog")
        for page, keys in pages.items():
            if not IDENTIFIER.fullmatch(page) or not 1 <= len(keys) <= 32 or len(set(keys)) != len(keys) or not set(keys) <= self.tags.keys():
                raise ValueError("Invalid page allowlist")
        if len(context_tags) > 32 or len(set(context_tags)) != len(context_tags) or not set(context_tags) <= self.tags.keys():
            raise ValueError("Invalid context allowlist")
        self.source, self.pages, self.context_tags = source, dict(pages), tuple(context_tags)
        self.sample_seconds, self.lease_seconds, self.grace_seconds = sample_seconds, lease_seconds, grace_seconds
        self.max_leases, self.clock, self.wall = max_leases, clock, wall
        self.lock, self.io_lock = threading.RLock(), threading.Lock()
        self.leases: dict[str, Lease] = {}
        self.cache: dict[str, dict] = {}
        self.active: set[str] = set()
        self.grace: dict[str, float] = {}
        self.next_sample: dict[str, float] = {}
        self.history_due: dict[str, float] = {}
        self.next_context = 0.0
        self.context_cache: dict[str, dict] = {}
        self.context_published_at = None

    def _sync(self, now):
        expired_at = {}
        for token, lease in list(self.leases.items()):
            if lease.expires <= now:
                for tag in self.pages[lease.page]:
                    expired_at[tag] = max(expired_at.get(tag, 0), lease.expires)
                del self.leases[token]
                self.history_due.pop(token, None)
        active = {tag for lease in self.leases.values() for tag in self.pages[lease.page]}
        for tag in self.active - active:
            self.grace[tag] = expired_at.get(tag, now) + self.grace_seconds
        for tag in active:
            self.grace.pop(tag, None)
        self.active = active
        self.grace = {tag: until for tag, until in self.grace.items() if until > now}
        return active | self.grace.keys()

    def _lease(self, owner, token):
        self._sync(self.clock())
        lease = self.leases.get(token)
        if lease is None or lease.owner != owner:
            raise DemandError("subscription_missing", 404)
        return lease

    def subscribe(self, owner, client, page):
        if not isinstance(owner, str) or not OWNER.fullmatch(owner) or not isinstance(client, str) or not IDENTIFIER.fullmatch(client) or page not in self.pages:
            raise DemandError("unknown_page_or_client")
        with self.lock:
            now = self.clock()
            self._sync(now)
            for token, lease in self.leases.items():
                if lease.owner == owner and lease.client == client:
                    if lease.page != page:
                        raise DemandError("client_page_conflict", 409)
                    lease.expires = now + self.lease_seconds
                    return self._response(token, lease)
            if len(self.leases) >= self.max_leases or sum(l.owner == owner for l in self.leases.values()) >= 8:
                raise DemandError("subscription_capacity", 429)
            token = secrets.token_hex(24)
            lease = self.leases[token] = Lease(owner, client, page, now + self.lease_seconds)
            self._sync(now)
            return self._response(token, lease)

    def heartbeat(self, owner, token):
        with self.lock:
            lease = self._lease(owner, token)
            lease.expires = self.clock() + self.lease_seconds
            return self._response(token, lease)

    def release(self, owner, token):
        with self.lock:
            self._lease(owner, token)
            del self.leases[token]
            self.history_due.pop(token, None)
            self._sync(self.clock())
        return {"released": True}

    def _point(self, reading, received):
        if not isinstance(reading, Reading):
            reading = Reading(None, None, "no_data")
        stamp = epoch(reading.source_at)
        quality = reading.quality if isinstance(reading.quality, str) and reading.quality in QUALITY else "invalid"
        value = reading.value
        try:
            valid_number = not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)
        except OverflowError:
            valid_number = False
        if value is not None and not valid_number:
            value, quality = None, "invalid"
        if stamp is None or stamp > received + 1:
            value, quality, stamp = None, ("invalid" if reading.source_at is not None else (quality if quality != "good" else "no_data")), None
        if quality != "good" or value is None:
            value = None
            if quality == "good":
                quality = "no_data"
        return {"value": value, "source_at": iso(stamp) if stamp is not None else None,
                "received_at": iso(received), "source_quality": quality}

    def _row(self, tag, now, *, cache=None, freshness_seconds=None):
        spec = self.tags[tag]
        raw = (self.cache if cache is None else cache).get(tag, {"value": None, "source_at": None, "received_at": None, "source_quality": "no_data"})
        stamp = epoch(raw["source_at"])
        age = max(0, now - stamp) if stamp is not None else None
        quality = raw["source_quality"]
        freshness = "no_data" if stamp is None else ("fresh" if age < (freshness_seconds or self.sample_seconds * 3) else "stale")
        if quality == "good" and freshness == "stale":
            quality = "stale"
        return {"tag": tag, "label": spec.label, "unit": spec.unit, **raw,
                "value": raw["value"] if quality == "good" and freshness == "fresh" else None,
                "quality": quality, "freshness": freshness, "age_seconds": round(age, 3) if age is not None else None}

    def _response(self, token, lease):
        now = self.wall()
        rows = [self._row(tag, now) for tag in self.pages[lease.page]]
        good = sum(row["quality"] == "good" for row in rows)
        status = "current" if good == len(rows) else ("partial" if good else ("no_data" if all(row["source_at"] is None for row in rows) else "degraded"))
        return {"subscription": token, "page": lease.page, "source_mode": self.source.mode,
                "generated_at": iso(now), "sample_seconds": self.sample_seconds,
                "lease_seconds": self.lease_seconds, "grace_seconds": self.grace_seconds,
                "context_enabled": bool(self.context_tags), "status": status, "tags": rows}

    def tick(self):
        with self.lock:
            now = self.clock()
            wanted = self._sync(now)
            due = {tag for tag in wanted if self.next_sample.get(tag, 0) <= now}
            context_due = bool(self.context_tags) and self.next_context <= now
            if context_due:
                due.update(tag for tag in self.context_tags if self.next_sample.get(tag, 0) <= now)
                self.next_context = now + 60
            if not due:
                if context_due:
                    self._publish_context()
                return
            for tag in due:
                self.next_sample[tag] = now + self.sample_seconds
        if not self.io_lock.acquire(blocking=False):
            return  # One source operation at a time; skip rather than queue a burst.
        try:
            try:
                readings = self.source.snapshot(tuple(sorted(due)), deadline=self.clock() + 2)
                if not isinstance(readings, dict) or len(readings) > 128:
                    raise ValueError("invalid adapter response")
            except Exception:
                readings = {tag: Reading(None, None, "read_error") for tag in due}
            with self.lock:
                received = self.wall()
                for tag in due:
                    self.cache[tag] = self._point(readings.get(tag), received)
                if context_due:
                    self._publish_context()
        finally:
            self.io_lock.release()

    def _publish_context(self):
        self.context_cache = {tag: dict(self.cache[tag]) for tag in self.context_tags if tag in self.cache}
        self.context_published_at = iso(self.wall())

    def context(self):
        """Read only a minute-published, explicit tag set. Never starts collection."""
        with self.lock:
            now = self.wall()
            rows = [self._row(tag, now, cache=self.context_cache, freshness_seconds=75) for tag in self.context_tags]
            return {"source_mode": self.source.mode, "enabled": bool(self.context_tags),
                    "feed_interval_seconds": 60, "meaning": "signal_data_only",
                    "published_at": self.context_published_at, "generated_at": iso(now), "tags": rows}

    def history(self, owner, token, tag, start, end, limit):
        now = self.wall()
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1000:
            raise DemandError("history_limit")
        if not all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in (start, end)) or not 0 <= start < end <= now + 1 or end - start > 3600:
            raise DemandError("history_range")
        with self.lock:
            lease = self._lease(owner, token)
            if tag not in self.pages[lease.page]:
                raise DemandError("unknown_page_tag", 404)
            if self.history_due.get(token, 0) > self.clock():
                raise DemandError("history_rate_limit", 429)
            self.history_due[token] = self.clock() + 5
        if not self.io_lock.acquire(blocking=False):
            raise DemandError("source_busy", 503)
        try:
            try:
                readings = self.source.history(tag, start, end, limit, deadline=self.clock() + 2)
                if not isinstance(readings, list) or len(readings) > limit:
                    raise ValueError("history capacity")
                points, previous = [], None
                for reading in readings:
                    point = self._point(reading, self.wall())
                    stamp = epoch(point["source_at"])
                    if stamp is None or not start <= stamp <= end or (previous is not None and stamp <= previous):
                        raise ValueError("history timestamps")
                    previous = stamp
                    points.append({"value": point["value"], "source_at": point["source_at"], "quality": point["source_quality"]})
                return {"source_mode": self.source.mode, "tag": tag, "start": iso(start), "end": iso(end), "points": points,
                        "limit": limit, "coverage": "not_asserted", "generated_at": iso(self.wall())}
            except Exception:
                raise DemandError("history_unavailable", 503) from None
        finally:
            self.io_lock.release()
