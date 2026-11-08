"""Single, serial pilot poller. No discovery, probe, source write or persistence."""
from __future__ import annotations

import inspect
import math
import socket
import threading
import time
from contextlib import nullcontext

from src.adapters.modbus.decoding import decode_registers, normalize_register_type, register_count, resolve_register_address
from src.domain.models import ParameterSpec, Stack
from src.services.normalize import Normalizer
from src.live.cache import POLL_SECONDS, RollingCache, Sample, utc_now

CYCLE_BUDGET_SECONDS = 4.0
REQUEST_TIMEOUT_SECONDS = 0.5
REQUEST_GAP_SECONDS = 0.05


class SingleOwner:
    """Linux abstract socket lock, no persistent lock file or payload.

    This prevents competing PILOT processes only. Legacy workers do not honour
    it, which is why the shipped launcher refuses PLC activation.
    """
    def __init__(self, identity: str):
        import hashlib
        self._name = '\0nadi-cems-' + hashlib.sha256(identity.encode()).hexdigest()[:32]
        self._socket = None

    def __enter__(self):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        try:
            sock.bind(self._name)
        except BaseException:
            sock.close()
            raise RuntimeError('CEMS pilot source already owned') from None
        self._socket = sock
        return self

    def __exit__(self, *_args):
        if self._socket:
            self._socket.close()
            self._socket = None


class ReadOnlyPlcSource:
    """Exact registry reads only; tested but deliberately not launchable yet.

    pymodbus and application retries are disabled; failed reads become null.
    No learned/guessed register probing. Same-register signals share one read.
    """
    source_mode = 'plc'

    def __init__(self, host: str, port=502, unit_id=1, *, delegate=None,
                 clock=time.monotonic, sleep=time.sleep):
        if not host or not 1 <= port <= 65535 or not 0 <= unit_id <= 247:
            raise ValueError('invalid PLC identity')
        self.identity = f'plc:{host}:{port}:{unit_id}'
        self._host, self._port, self._unit = host, port, unit_id
        self._delegate = delegate
        self._clock, self._sleep = clock, sleep
        self._last_request = None
        self.observed_at = {}

    def read(self, parameters: list[ParameterSpec], deadline: float):
        from pymodbus.client import ModbusTcpClient
        if self._delegate is None:
            self._delegate = ModbusTcpClient(self._host, port=self._port,
                                            timeout=REQUEST_TIMEOUT_SECONDS, retries=0)
        raw = {}
        self.observed_at = {}
        timestamps = {}
        results = {}
        for spec in parameters:
            cfg = spec.modbus
            count = register_count(cfg.data_type)
            if not 1 <= count <= 125:
                raise ValueError('register count outside protocol bound')
            address = resolve_register_address(cfg.register, cfg.address_base, cfg.zero_based)
            register_type = normalize_register_type(cfg.register_type)
            function_name = 'read_input_registers' if register_type == 'input' else 'read_holding_registers'
            if function_name not in {'read_holding_registers', 'read_input_registers'} or not 0 <= address <= 65535 or address + count > 65536:
                raise ValueError('read-only register specification required')
            key = (function_name, address, count)
            if key not in results:
                if self._last_request is not None:
                    delay = max(0, REQUEST_GAP_SECONDS - (self._clock() - self._last_request))
                    if self._clock() + delay + REQUEST_TIMEOUT_SECONDS > deadline:
                        continue
                    self._sleep(delay)
                if self._clock() + REQUEST_TIMEOUT_SECONDS > deadline:
                    continue
                self._last_request = self._clock()
                function = getattr(self._delegate, function_name)
                names = inspect.signature(function).parameters
                unit = {'device_id': self._unit} if 'device_id' in names else {'slave': self._unit} if 'slave' in names else {}
                try:
                    response = function(address, count=count, **unit)
                    if response.isError() or len(response.registers) != count:
                        results[key] = None
                    else:
                        results[key] = tuple(response.registers)
                        timestamps[key] = utc_now()
                except Exception:
                    results[key] = None
                    # No exception/payload logging and no same-cycle retry.
            registers = results.get(key)
            if registers is not None:
                try:
                    value = decode_registers(list(registers), cfg.data_type, cfg.word_order, cfg.byte_order)
                    if math.isfinite(value):
                        raw[spec.code] = value
                        self.observed_at[spec.code] = timestamps[key]
                except Exception:
                    pass
        return raw

    def close(self):
        if self._delegate is not None:
            self._delegate.close()
            self._delegate = None


class SimulatedSource:
    source_mode = 'simulation'
    identity = 'cems-simulation'

    def read(self, parameters, deadline):
        # Fixed, conspicuously labeled development fixtures, never PLC evidence.
        return {p.code: (10.0 if p.code == 'O2' else 1.25) for p in parameters}

    def close(self):
        pass


class LiveCollector:
    def __init__(self, cache: RollingCache, source, stack: Stack, *,
                 clock=time.monotonic, wall_clock=utc_now):
        if cache.source_mode != source.source_mode:
            raise ValueError('source mode mismatch')
        self.cache, self.source, self.stack = cache, source, stack
        self._clock, self._wall = clock, wall_clock
        self._cycle_lock = threading.Lock()
        self._last_started = None

    def collect_once(self):
        if not self._cycle_lock.acquire(blocking=False):
            return False
        try:
            start = self._clock()
            if self._last_started is not None and start - self._last_started < POLL_SECONDS:
                return False
            self._last_started = start
            specs = list(self.cache.parameters.values())
            try:
                raw = self.source.read(specs, start + CYCLE_BUDGET_SECONDS)
            except Exception:
                raw = {}
            # Read-only PLC has no source timestamp. Acquisition time is explicit.
            stamp = self._wall()
            finite = {p.code: raw[p.code] for p in specs
                      if p.code in raw and isinstance(raw[p.code], (int, float))
                      and not isinstance(raw[p.code], bool) and math.isfinite(raw[p.code])}
            # Never use legacy O2=0 fallback when this cycle lacks oxygen.
            oxygen_ok = 'O2' in finite
            transformable = {p.code: finite[p.code] for p in specs if p.code in finite
                             and (p.o2_reference is None or oxygen_ok)}
            normalizer = Normalizer({p.code: p for p in specs}, self.stack, at=stamp)
            try:
                readings = {r.parameter_code: r for r in normalizer.transform_batch(transformable, stamp)}
            except (ValueError, OverflowError, TypeError):
                # Fail closed on an unexpected arithmetic edge, never log payloads
                # or leave the loop stuck displaying a previous good batch.
                readings = {}
            samples = []
            for p in specs:
                reading = readings.get(p.code)
                quality = ('invalid' if p.code in raw and p.code not in finite else
                           'read_error' if p.code not in finite else
                           'dependency_missing' if p.o2_reference is not None and not oxygen_ok else
                           'good' if reading and reading.transformation_status == 'ok'
                           and reading.value_final is not None and math.isfinite(reading.value_final) else 'invalid')
                observed_at = getattr(self.source, 'observed_at', {}).get(p.code, stamp)
                samples.append(Sample(p.code, observed_at, finite.get(p.code),
                                      reading.value_final if quality == 'good' else None, quality))
            return self.cache.publish(samples, cycle_started=start)
        finally:
            self._cycle_lock.release()

    def run(self, stop: threading.Event, *, acquire_owner=True):
        try:
            with SingleOwner(self.source.identity) if acquire_owner else nullcontext():
                while not stop.is_set():
                    start = self._clock()
                    try:
                        self.collect_once()
                    except Exception:
                        # Retain only bounded history; age/quality expose failure.
                        # Never log a source exception or start catch-up work.
                        pass
                    # Drop missed cycles, never queue or catch up in a burst.
                    stop.wait(max(0.1, POLL_SECONDS - (self._clock() - start)))
        finally:
            self.source.close()
