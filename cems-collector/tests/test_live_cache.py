"""Hermetic volatile pilot checks; never touch production/PLC or a database."""
import asyncio
import json
import math
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from src.domain.models import ModbusReadConfig, ParameterSpec, Stack
from src.live.cache import RollingCache, Sample, RETENTION_SECONDS, MAX_SAMPLES_PER_PARAMETER
from src.live.collector import LiveCollector, ReadOnlyPlcSource, SimulatedSource, SingleOwner
from src.live.api import create_app


class Clock:
    def __init__(self): self.seconds = 0.0
    def __call__(self): return self.seconds
    def wall(self): return datetime(2026, 11, 8, tzinfo=timezone.utc) + timedelta(seconds=self.seconds)
    def advance(self, seconds): self.seconds += seconds


def spec(code='CO', *, register=10, oxygen=None):
    return ParameterSpec(code=code, stack_id='1', name=code, unit='mg/Nm3',
                         status='documented', normalization_enabled=False,
                         o2_reference=oxygen, modbus=ModbusReadConfig(register))


def setup(specs=None, mode='simulation'):
    clock = Clock()
    cache = RollingCache(specs or [spec()], source_mode=mode, clock=clock, wall_clock=clock.wall)
    return clock, cache


def sample(clock, code='CO', value=1.25, quality='good'):
    return Sample(code, clock.wall(), value, value if quality == 'good' else None, quality)


async def request(app, path, method='GET', query='', host='testserver'):
    messages = []
    received = False
    done = asyncio.Event()
    async def receive():
        nonlocal received
        if not received:
            received = True
            return {'type': 'http.request', 'body': b'', 'more_body': False}
        await done.wait()
        return {'type': 'http.disconnect'}
    async def send(message):
        messages.append(message)
        if message['type'] == 'http.response.body' and not message.get('more_body', False): done.set()
    scope = {'type': 'http', 'asgi': {'version': '3.0'}, 'http_version': '1.1',
             'scheme': 'http', 'method': method, 'path': path, 'raw_path': path.encode(),
             'query_string': query.encode(), 'headers': [(b'host', host.encode())],
             'client': ('127.0.0.1', 10), 'server': ('127.0.0.1', 8013), 'root_path': ''}
    await app(scope, receive, send)
    start = next(m for m in messages if m['type'] == 'http.response.start')
    body = b''.join(m.get('body', b'') for m in messages if m['type'] == 'http.response.body')
    return start['status'], dict(start['headers']), body


class CacheTest(unittest.TestCase):
    def test_retention_exact_boundary_even_without_new_writes(self):
        clock, cache = setup()
        cache.publish([sample(clock)])
        clock.advance(RETENTION_SECONDS - .1)
        self.assertEqual(len(cache.history('CO')['points']), 1)
        clock.advance(.1)
        self.assertEqual(cache.history('CO')['points'], [])
        self.assertEqual(cache.snapshot()['samples_retained'], 0)
        self.assertIsNone(cache.snapshot()['parameters'][0]['last_good_at'])

    def test_retention_uses_acquisition_time_not_late_publication(self):
        clock, cache = setup()
        reading = sample(clock)
        clock.advance(4)
        cache.publish([reading])
        clock.advance(RETENTION_SECONDS - 4)
        self.assertEqual(cache.snapshot()['samples_retained'], 0)

    def test_stale_and_offline_never_look_live(self):
        clock, cache = setup()
        cache.publish([sample(clock)])
        self.assertEqual(cache.snapshot()['status'], 'live')
        clock.advance(15)
        self.assertEqual(cache.snapshot()['parameters'][0]['quality'], 'stale')
        self.assertIsNone(cache.snapshot()['parameters'][0]['value_final'])
        clock.advance(45)
        self.assertEqual(cache.snapshot()['status'], 'offline')

    def test_error_null_keeps_last_good_timestamp_until_evicted(self):
        clock, cache = setup()
        cache.publish([sample(clock)])
        old = clock.wall().isoformat()
        clock.advance(5)
        cache.publish([sample(clock, value=None, quality='read_error')])
        current = cache.snapshot()['parameters'][0]
        self.assertEqual(current['quality'], 'read_error')
        self.assertEqual(current['last_good_at'], old)
        self.assertIsNone(current['value_final'])

    def test_bounded_window_and_history_spans_whole_window(self):
        clock, cache = setup()
        for _ in range(5000):
            cache.publish([sample(clock)])
            clock.advance(5)
        self.assertLessEqual(cache.snapshot()['samples_retained'], MAX_SAMPLES_PER_PARAMETER)
        history = cache.history('CO', 10)
        self.assertEqual(len(history['points']), 10)
        self.assertTrue(history['truncated'])
        a, b = [datetime.fromisoformat(history['points'][i]['observed_at']) for i in (0, -1)]
        self.assertGreater((b-a).total_seconds(), 21500)

    def test_restart_empty_and_clear(self):
        clock, cache = setup()
        cache.publish([sample(clock)])
        self.assertEqual(setup()[1].snapshot()['status'], 'warming_up')
        cache.clear()
        self.assertEqual(cache.snapshot()['samples_retained'], 0)

    def test_admission_blocks_fast_duplicates_and_invalid_batch(self):
        clock, cache = setup()
        cache.publish([sample(clock)])
        self.assertFalse(cache.publish([sample(clock)]))
        self.assertEqual(cache.snapshot()['samples_retained'], 1)
        with self.assertRaises(ValueError): cache.publish([sample(clock, 'unknown')])
        with self.assertRaises(ValueError): cache.publish([sample(clock, value=math.nan)])
        with self.assertRaises(ValueError): cache.publish([Sample('CO', datetime.now(), 1, 1, 'good')])
        with self.assertRaises(ValueError): cache.history('CO', 1001)
        with self.assertRaises(KeyError): cache.history('unknown')
        clock.advance(-1)
        with self.assertRaises(RuntimeError): cache.snapshot()
        clock.advance(1)
        self.assertEqual(cache.snapshot()['samples_retained'], 0)

    def test_minute_feed_shared_decoupled_and_not_equipment_state(self):
        clock, cache = setup()
        self.assertEqual(cache.signals()['status'], 'warming_up')
        cache.publish([sample(clock)])
        first = cache.signals()['generated_at']
        for _ in range(11):
            clock.advance(5)
            cache.publish([sample(clock)])
            self.assertEqual(cache.signals()['generated_at'], first)
        clock.advance(5)
        cache.publish([sample(clock)])
        feed = cache.signals()
        self.assertNotEqual(feed['generated_at'], first)
        self.assertEqual(feed['signals'][0]['good_samples_last_minute'], 12)
        self.assertEqual(feed['meaning'], 'signal_data_only')
        self.assertNotIn('asset_running', feed)
        feed['signals'][0]['signal_state'] = 'tampered'
        self.assertEqual(cache.signals()['signals'][0]['signal_state'], 'receiving')
        clock.advance(75)
        self.assertEqual(cache.signals()['status'], 'stale')
        clock.advance(RETENTION_SECONDS)
        self.assertEqual(cache.signals()['signals'], [])

    def test_variable_read_duration_does_not_drop_five_second_cycles(self):
        clock, cache = setup()
        clock.advance(3)
        cache.publish([sample(clock)], cycle_started=0)
        clock.advance(4)  # Second cycle began at 5, read took 2 seconds.
        self.assertTrue(cache.publish([sample(clock)], cycle_started=5))
        self.assertEqual(cache.snapshot()['samples_retained'], 2)

    def test_concurrent_readers_do_not_poll_or_duplicate(self):
        clock, cache = setup()
        cache.publish([sample(clock)])
        with ThreadPoolExecutor(max_workers=8) as pool:
            result = list(pool.map(lambda _: cache.snapshot(), range(100)))
        self.assertTrue(all(x['samples_retained'] == 1 for x in result))


class SourceTest(unittest.TestCase):
    def test_collector_preserves_missing_o2_and_no_invented_zero(self):
        clock, cache = setup([spec('SO2', oxygen=7), spec('O2')])
        source = SimulatedSource()
        source.read = lambda *args: {'SO2': 10}
        collector = LiveCollector(cache, source, Stack('1','CB001','Test'), clock=clock, wall_clock=clock.wall)
        collector.collect_once()
        values = cache.snapshot()['parameters']
        self.assertEqual(values[0]['quality'], 'dependency_missing')
        self.assertIsNone(values[0]['value_final'])
        self.assertEqual(values[1]['quality'], 'read_error')

    def test_normalization_and_operator_raw_override_are_preserved(self):
        from src.config import CemsConfig
        from src.services.registry import load_registry
        registry = load_registry(CemsConfig())
        specs = [p for p in registry.parameters if p.collect_enabled]
        clock, cache = setup(specs)
        source = SimulatedSource()
        source.read = lambda *args: {p.code: (10.0 if p.code == 'O2' else 20.0) for p in specs}
        collector = LiveCollector(cache, source, registry.stacks[0], clock=clock, wall_clock=clock.wall)
        collector.collect_once()
        rows = {r['parameter_code']: r for r in cache.snapshot()['parameters']}
        for code in ('NO','NO2','CO2','Flow'):
            self.assertEqual(rows[code]['value_raw'], rows[code]['value_final'])
        self.assertEqual(rows['Laju_alir']['value_final'], 883.125)

    def test_deadline_rate_limit_deduplication_and_read_only(self):
        clock = Clock()
        class Reply:
            registers = [0x3f80, 0]
            def isError(self): return False
        class Delegate:
            def __init__(self): self.calls = []
            def read_holding_registers(self, address, count, device_id):
                self.calls.append((address, count, device_id, clock()))
                return Reply()
            def close(self): pass
        delegate = Delegate()
        source = ReadOnlyPlcSource('unused', delegate=delegate, clock=clock, sleep=clock.advance)
        rows = source.read([spec('A'), spec('B'), spec('C', register=12)], deadline=4)
        self.assertEqual(rows, {'A': 1., 'B': 1., 'C': 1.})
        self.assertEqual(len(delegate.calls), 2)
        self.assertGreaterEqual(delegate.calls[1][3] - delegate.calls[0][3], .05)
        self.assertEqual(source.read([spec()], deadline=clock()), {})
        bad = spec()
        from dataclasses import replace
        bad = replace(bad, modbus=replace(bad.modbus, register_type='write_registers'))
        with self.assertRaises(ValueError): source.read([bad], deadline=4)

    def test_failures_no_retry_and_recovery(self):
        clock, cache = setup()
        source = SimulatedSource()
        source.read = lambda *args: (_ for _ in ()).throw(RuntimeError('private payload'))
        collector = LiveCollector(cache, source, Stack('1','CB001','Test'), clock=clock, wall_clock=clock.wall)
        with patch('logging.Logger._log') as log:
            collector.collect_once()
            log.assert_not_called()
        self.assertEqual(cache.snapshot()['status'], 'offline')
        self.assertFalse(collector.collect_once())
        clock.advance(5)
        source.read = lambda *args: {'CO': 2.5}
        self.assertTrue(collector.collect_once())
        self.assertEqual(cache.snapshot()['status'], 'live')

    def test_bad_normalization_cannot_kill_shared_collector(self):
        clock, cache = setup()
        source = SimulatedSource()
        collector = LiveCollector(cache, source, Stack('1','CB001','Test'), clock=clock, wall_clock=clock.wall)
        with patch('src.live.collector.Normalizer.transform_batch', side_effect=OverflowError):
            self.assertTrue(collector.collect_once())
        self.assertEqual(cache.snapshot()['parameters'][0]['quality'], 'invalid')
        clock.advance(5)
        self.assertTrue(collector.collect_once())
        self.assertEqual(cache.snapshot()['status'], 'live')

    def test_single_owner(self):
        with SingleOwner('hermetic-cems-test'):
            with self.assertRaises(RuntimeError):
                with SingleOwner('hermetic-cems-test'): pass
        with SingleOwner('hermetic-cems-test'): pass


class ApiTest(unittest.IsolatedAsyncioTestCase):
    async def test_read_api_bounded_and_no_store_without_polling(self):
        clock, cache = setup()
        cache.publish([sample(clock)])
        app = create_app(cache=cache, start_collector=False)
        for _ in range(3):
            status, headers, body = await request(app, '/v1/cems/snapshot')
            self.assertEqual(status, 200)
            self.assertEqual(headers[b'cache-control'], b'no-store, private')
            self.assertEqual(json.loads(body)['samples_retained'], 1)
        self.assertEqual((await request(app, '/v1/cems/snapshot', method='POST'))[0], 405)
        self.assertEqual((await request(app, '/v1/cems/history', query='parameter=CO&limit=1001'))[0], 422)
        self.assertEqual((await request(app, '/v1/cems/history', query='parameter=UNKNOWN'))[0], 404)
        self.assertEqual((await request(app, '/v1/cems/snapshot', host='evil.example'))[0], 400)
        status, _, body = await request(app, '/v1/cems/history', query='parameter=CO')
        self.assertEqual(status, 200)
        self.assertEqual(len(json.loads(body)['points']), 1)
        self.assertNotIn(b'sources', body)
        self.assertNotIn(b'raw_registers', body)

    async def test_idle_janitor_evicts_when_collector_has_no_new_samples(self):
        clock, cache = setup()
        cache.publish([sample(clock)])
        app = create_app(cache=cache, start_collector=False)
        async with app.router.lifespan_context(app):
            clock.advance(RETENTION_SECONDS)
            await asyncio.sleep(1.1)
            self.assertEqual(sum(map(len, cache._rows.values())), 0)
            self.assertIsNone(cache._signal_feed)

    async def test_shutdown_clears_cache(self):
        clock, cache = setup()
        cache.publish([sample(clock)])
        app = create_app(cache=cache, start_collector=False)
        async with app.router.lifespan_context(app): pass
        self.assertEqual(cache.snapshot()['samples_retained'], 0)
