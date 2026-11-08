"""Bounded process-memory CEMS window. No DB, file, payload log or write API."""
from __future__ import annotations

import math
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone

from src.domain.models import ParameterSpec

POLL_SECONDS = 5
RETENTION_SECONDS = 6 * 60 * 60
MAX_PARAMETERS = 32
MAX_SAMPLES_PER_PARAMETER = int(RETENTION_SECONDS / POLL_SECONDS)
MAX_HISTORY_POINTS = 1000
STALE_SECONDS = 15.0
OFFLINE_SECONDS = 60.0
QUALITIES = frozenset({'good', 'read_error', 'invalid', 'dependency_missing'})


def utc_now():
    return datetime.now(timezone.utc)


def iso(value):
    return value.isoformat() if value is not None else None


@dataclass(frozen=True, slots=True)
class Sample:
    parameter_code: str
    observed_at: datetime
    value_raw: float | None
    value_final: float | None
    quality: str


@dataclass(frozen=True, slots=True)
class Entry:
    sample: Sample
    accepted_at: float


class RollingCache:
    def __init__(self, parameters: list[ParameterSpec], *, source_mode: str,
                 clock=time.monotonic, wall_clock=utc_now):
        if source_mode not in {'plc', 'simulation'}:
            raise ValueError('unknown source mode')
        if not 1 <= len(parameters) <= MAX_PARAMETERS:
            raise ValueError('parameter count outside pilot bound')
        if len({p.stack_id for p in parameters}) != 1:
            raise ValueError('pilot supports exactly one stack')
        self.parameters = {p.code: p for p in parameters}
        if len(self.parameters) != len(parameters):
            raise ValueError('duplicate parameter code')
        self.stack_id = parameters[0].stack_id
        self.source_mode = source_mode
        self._clock, self._wall = clock, wall_clock
        self._started = wall_clock()
        self._rows = {code: deque(maxlen=MAX_SAMPLES_PER_PARAMETER) for code in self.parameters}
        self._lock = threading.RLock()
        self._last_cycle = None
        self._last_accepted = None
        self._clock_highwater = float('-inf')
        self._signal_feed = None
        self._signal_updated = None

    def _now(self):
        # A monotonic regression must not retain expired rows indefinitely.
        now = self._clock()
        if not math.isfinite(now) or now < self._clock_highwater:
            for rows in self._rows.values():
                rows.clear()
            self._last_accepted = None
            self._last_cycle = None
            self._signal_feed = self._signal_updated = None
            raise RuntimeError('monotonic clock moved backwards')
        self._clock_highwater = now
        return now

    def _evict(self, now):
        for rows in self._rows.values():
            while rows and now - rows[0].accepted_at >= RETENTION_SECONDS:
                rows.popleft()
        if self._signal_updated is not None and now - self._signal_updated >= RETENTION_SECONDS:
            self._signal_feed = self._signal_updated = None

    def expire(self):
        with self._lock:
            self._evict(self._now())

    def publish(self, samples: list[Sample], *, cycle_started=None) -> bool:
        """One complete batch per five seconds; reject backlog/unknown/future data."""
        if len(samples) != len(self.parameters) or {s.parameter_code for s in samples} != set(self.parameters):
            raise ValueError('batch must contain each configured parameter exactly once')
        wall = self._wall()
        for sample in samples:
            if sample.quality not in QUALITIES:
                raise ValueError('unknown quality')
            if sample.observed_at.tzinfo is None or sample.observed_at.utcoffset() is None:
                raise ValueError('aware acquisition timestamp required')
            age = (wall - sample.observed_at).total_seconds()
            if age < -1 or age > POLL_SECONDS:
                raise ValueError('sample timestamp outside current acquisition cycle')
            for value in (sample.value_raw, sample.value_final):
                if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)):
                    raise ValueError('sample value must be finite numeric or null')
            if sample.quality == 'good' and sample.value_final is None:
                raise ValueError('good sample requires final value')
            if sample.quality != 'good' and sample.value_final is not None:
                raise ValueError('failed sample cannot expose a final value')
        with self._lock:
            now = self._now()
            self._evict(now)
            cycle = now if cycle_started is None else cycle_started
            if not math.isfinite(cycle) or cycle > now or now - cycle > POLL_SECONDS:
                raise ValueError('cycle start outside acquisition budget')
            if self._last_accepted is not None and cycle - self._last_accepted < POLL_SECONDS:
                return False
            for sample in samples:
                self._rows[sample.parameter_code].append(Entry(sample, now - max(0.0, (wall - sample.observed_at).total_seconds())))
            self._last_cycle, self._last_accepted = wall, cycle
            if self._signal_updated is None or now - self._signal_updated >= 60:
                signals = []
                for code, rows in self._rows.items():
                    recent = [row for row in rows if now - row.accepted_at < 60]
                    good = [row for row in recent if row.sample.quality == 'good']
                    signals.append({
                        'parameter_code': code,
                        'last_received_at': iso(good[-1].sample.observed_at) if good else None,
                        'good_samples_last_minute': len(good),
                        'expected_samples_per_minute': 12,
                        'signal_state': 'receiving' if good else 'no_recent_good_data',
                    })
                self._signal_feed = {'generated_at': iso(wall), 'signals': signals}
                self._signal_updated = now
            return True

    def snapshot(self):
        with self._lock:
            now = self._now()
            self._evict(now)
            parameters = []
            for code, spec in self.parameters.items():
                rows = self._rows[code]
                last = rows[-1] if rows else None
                age = now - last.accepted_at if last else None
                quality = last.sample.quality if last else 'unknown'
                if age is not None and age >= OFFLINE_SECONDS:
                    quality = 'offline'
                elif age is not None and age >= STALE_SECONDS:
                    quality = 'stale'
                good = next((row for row in reversed(rows) if row.sample.quality == 'good'), None)
                parameters.append({
                    'parameter_code': code, 'name': spec.name, 'unit': spec.unit,
                    'value_raw': last.sample.value_raw if last else None,
                    'value_final': last.sample.value_final if last and quality == 'good' else None,
                    'observed_at': iso(last.sample.observed_at) if last else None,
                    'last_good_at': iso(good.sample.observed_at) if good else None,
                    'quality': quality, 'age_seconds': round(age, 3) if age is not None else None,
                })
            qualities = {p['quality'] for p in parameters}
            status = ('warming_up' if self._last_accepted is None else
                      'offline' if qualities <= {'offline', 'unknown', 'read_error'} else
                      'live' if qualities == {'good'} else 'degraded')
            return {
                'stack_id': self.stack_id, 'source_mode': self.source_mode,
                'poll_interval_seconds': POLL_SECONDS, 'retention_seconds': RETENTION_SECONDS,
                'stale_after_seconds': STALE_SECONDS, 'offline_after_seconds': OFFLINE_SECONDS,
                'timestamp_origin': 'collector_acquisition_utc',
                'status': status, 'generated_at': iso(self._wall()),
                'last_cycle_at': iso(self._last_cycle), 'cache_started_at': iso(self._started),
                'samples_retained': sum(len(rows) for rows in self._rows.values()),
                'parameters': parameters,
            }

    def history(self, parameter: str, limit: int = 360):
        if parameter not in self.parameters:
            raise KeyError(parameter)
        if isinstance(limit, bool) or not 1 <= limit <= MAX_HISTORY_POINTS:
            raise ValueError('history limit outside bound')
        with self._lock:
            now = self._now()
            self._evict(now)
            rows = list(self._rows[parameter])
            # Uniformly select actual samples across the whole retained window;
            # never invent interpolation, averages or contiguous coverage.
            truncated = len(rows) > limit
            if truncated:
                indices = ([len(rows) - 1] if limit == 1 else
                           [round(i * (len(rows) - 1) / (limit - 1)) for i in range(limit)])
                rows = [rows[i] for i in indices]
            return {'parameter_code': parameter, 'retention_seconds': RETENTION_SECONDS,
                    'truncated': truncated, 'sampling': 'actual_points',
                    'points': [{'observed_at': iso(row.sample.observed_at),
                                'value_final': row.sample.value_final,
                                'quality': row.sample.quality} for row in rows]}

    def signals(self):
        """One minute shared feed: communication evidence, never asset state."""
        with self._lock:
            now = self._now()
            self._evict(now)
            age = now - self._signal_updated if self._signal_updated is not None else None
            if age is not None and age >= RETENTION_SECONDS:
                self._signal_feed = self._signal_updated = None
                age = None
            feed = self._signal_feed
            return {
                'source_mode': self.source_mode, 'feed_interval_seconds': 60,
                'window_seconds': 60, 'meaning': 'signal_data_only',
                'generated_at': feed['generated_at'] if feed else None,
                'feed_age_seconds': round(age, 3) if age is not None else None,
                'status': 'warming_up' if feed is None else 'stale' if age >= 75 else 'current',
                'signals': [dict(row) for row in feed['signals']] if feed else [],
            }

    def clear(self):
        with self._lock:
            for rows in self._rows.values():
                rows.clear()
            self._last_cycle = self._last_accepted = None
            self._signal_feed = self._signal_updated = None
