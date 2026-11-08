import http.client
import json
import threading
import unittest
from historian.core import Coordinator, DemandError, Reading, Tag, iso
from historian.server import BoundedServer


class Source:
    mode = 'simulation'
    def __init__(self, clock):
        self.clock, self.calls, self.history_calls = clock, [], []
        self.rows, self.failure = {}, False
    def snapshot(self, tags, *, deadline):
        self.calls.append(tags)
        if self.failure:
            raise OSError('private error not exposed')
        return {tag: self.rows.get(tag, Reading(0, iso(self.clock.wall()), 'good')) for tag in tags}
    def history(self, tag, start, end, limit, *, deadline):
        self.history_calls.append(tag)
        return [Reading(0, iso(start), 'good'), Reading(None, iso(end), 'bad')][:limit]


class Clock:
    def __init__(self): self.now = 100
    def mono(self): return self.now
    def wall(self): return 1794140000 + self.now
    def advance(self, seconds): self.now += seconds


class DemandTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.source = Source(self.clock)
        self.c = self.coordinator()
        self.owner = 'a' * 64
    def coordinator(self, **kw):
        return Coordinator(self.source, [Tag('A', 'A', 'MW'), Tag('B', 'B', 'bar'), Tag('C', 'C', '°C')],
            {'one': ('A', 'B'), 'two': ('B',)}, clock=self.clock.mono, wall=self.clock.wall, **kw)
    def subscribe(self, page='one', client='tab1', owner=None):
        return self.c.subscribe(owner or self.owner, client, page)['subscription']

    def test_no_viewer_no_read_and_cold_snapshot_does_not_read_source(self):
        self.c.tick()
        result = self.c.subscribe(self.owner, 'tab1', 'one')
        self.assertEqual(self.source.calls, [])
        self.assertEqual(result['status'], 'no_data')
        self.assertIsNone(result['tags'][0]['value'])
        self.assertIsNone(result['tags'][0]['source_at'])

    def test_many_viewers_and_overlapping_pages_read_union_once(self):
        self.subscribe()
        self.subscribe('two', 'tab2')
        self.subscribe('one', 'tab3', 'b' * 64)
        self.c.tick(); self.c.tick()
        self.assertEqual(self.source.calls, [('A', 'B')])
        self.clock.advance(4); self.c.tick()
        self.assertEqual(len(self.source.calls), 2)
        self.assertNotIn('C', self.source.calls[0])

    def test_warm_page_immediately_reuses_cache_without_read(self):
        self.subscribe(); self.c.tick()
        result = self.c.subscribe(self.owner, 'tab2', 'two')
        self.assertEqual(result['tags'][0]['value'], 0)
        self.assertEqual(result['status'], 'current')
        self.assertEqual(len(self.source.calls), 1)

    def test_subscribe_idempotency_and_expiry_capacity(self):
        one = self.subscribe()
        self.assertEqual(one, self.subscribe())
        self.assertEqual(len(self.c.leases), 1)
        for n in range(2, 9): self.subscribe(client=f'tab{n}')
        with self.assertRaises(DemandError): self.subscribe(client='tab9')
        self.clock.advance(21); self.c.tick()
        self.assertEqual(len(self.c.leases), 0)
        self.subscribe(client='tab9')

    def test_reference_counts_grace_stop_and_heartbeat(self):
        one = self.subscribe(); two = self.subscribe('two', 'tab2')
        self.c.tick(); self.c.release(self.owner, one)
        self.clock.advance(11)
        self.c.heartbeat(self.owner, two); self.c.tick()
        self.assertEqual(self.source.calls[-1], ('B',))
        self.c.release(self.owner, two)
        self.clock.advance(11); before = len(self.source.calls); self.c.tick()
        self.assertEqual(len(self.source.calls), before)

    def test_expiry_after_crash_stops_without_sliding_grace(self):
        self.subscribe(); self.c.tick()
        self.clock.advance(100); self.c.tick()
        self.assertEqual(len(self.source.calls), 1)

    def test_minute_context_is_explicit_and_not_all_tags(self):
        self.c = self.coordinator(context_tags=('C',))
        self.c.tick(); self.clock.advance(59); self.c.tick()
        self.assertEqual(self.source.calls, [('C',)])
        self.clock.advance(1); self.c.tick()
        self.assertEqual(self.source.calls, [('C',), ('C',)])
        self.assertEqual(self.c.subscribe(self.owner, 'x', 'one')['context_enabled'], True)

    def test_slow_stale_bad_future_and_missing_never_become_good_zero(self):
        token = self.subscribe(); self.c.tick()
        self.clock.advance(13)
        snapshot = self.c.heartbeat(self.owner, token)
        self.assertEqual(snapshot['tags'][0]['quality'], 'stale')
        self.assertIsNone(snapshot['tags'][0]['value'])
        for reading in [Reading(99, iso(self.clock.wall()), 'bad'), Reading(float('nan'), iso(self.clock.wall()), 'good'), Reading(99, iso(self.clock.wall() + 60), 'good'), Reading(99, None, 'good'), Reading(99, iso(self.clock.wall()), []), Reading(10**1000, iso(self.clock.wall()), 'good')]:
            self.source.rows['A'] = reading; self.clock.advance(4); self.c.tick()
            self.assertIsNone(self.c.heartbeat(self.owner, token)['tags'][0]['value'])

    def test_source_exception_replaces_current_values_and_preserves_error(self):
        token = self.subscribe(); self.c.tick()
        self.source.failure = True; self.clock.advance(4); self.c.tick()
        row = self.c.heartbeat(self.owner, token)['tags'][0]
        self.assertIsNone(row['value'])
        self.assertEqual(row['quality'], 'read_error')

    def test_owner_tag_page_bounds_and_unknown_mapping_fail_closed(self):
        token = self.subscribe()
        for action in [lambda: self.c.heartbeat('b' * 64, token), lambda: self.c.release('b' * 64, token),
                       lambda: self.c.subscribe(self.owner, 'tab2', 'invented'),
                       lambda: self.c.history(self.owner, token, 'C', self.clock.wall()-60, self.clock.wall(), 20)]:
            with self.assertRaises(DemandError): action()
        self.assertEqual(self.source.calls, [])
        self.assertEqual(self.source.history_calls, [])

    def test_history_is_explicit_bounded_rate_limited_and_unpersisted(self):
        token = self.subscribe()
        for start, end, limit in [(self.clock.wall()-3601, self.clock.wall(), 20), (0, self.clock.wall(), 1001), (self.clock.wall(), self.clock.wall()+60, 2)]:
            with self.assertRaises(DemandError): self.c.history(self.owner, token, 'A', start, end, limit)
        result = self.c.history(self.owner, token, 'A', self.clock.wall()-60, self.clock.wall(), 20)
        self.assertEqual(result['coverage'], 'not_asserted')
        self.assertEqual(result['points'][0]['value'], 0)
        self.assertIsNone(result['points'][1]['value'])
        self.assertEqual(self.c.cache, {})
        with self.assertRaises(DemandError): self.c.history(self.owner, token, 'A', self.clock.wall()-60, self.clock.wall(), 20)

    def test_memory_is_bounded_and_restart_is_cold(self):
        token = self.subscribe()
        for _ in range(3000):
            self.c.heartbeat(self.owner, token); self.c.tick(); self.clock.advance(4)
        self.assertEqual(len(self.c.cache), 2)
        self.assertEqual(len(self.c.next_sample), 2)
        self.assertEqual(len(self.c.leases), 1)
        self.assertEqual(self.coordinator().cache, {})

    def test_context_feed_publishes_once_per_minute_and_is_not_running_evidence(self):
        self.assertEqual(self.c.context()['tags'], [])
        self.c = self.coordinator(context_tags=('B',))
        token = self.subscribe()
        self.c.tick()
        first = self.c.context()
        self.clock.advance(4); self.c.tick()
        self.assertEqual(first['published_at'], self.c.context()['published_at'])
        self.assertEqual(first['tags'][0]['source_at'], self.c.context()['tags'][0]['source_at'])
        self.assertNotEqual(self.c.heartbeat(self.owner, token)['tags'][1]['source_at'], first['tags'][0]['source_at'])
        self.assertEqual(self.c.context()['meaning'], 'signal_data_only')
        self.clock.advance(72)
        self.assertEqual(self.c.context()['tags'][0]['quality'], 'stale')
        self.assertIsNone(self.c.context()['tags'][0]['value'])

    def test_timing_and_real_adapters_are_rejected(self):
        for interval in (0.1, 2, 6):
            with self.assertRaises(ValueError): self.coordinator(sample_seconds=interval)
        self.source.mode = 'pi'
        with self.assertRaises(ValueError): self.coordinator()

    def test_concurrent_subscriptions_share_one_lease(self):
        threads = [threading.Thread(target=self.subscribe) for _ in range(20)]
        for t in threads: t.start()
        for t in threads: t.join()
        self.assertEqual(len(self.c.leases), 1)

    def test_http_private_origin_methods_size_and_allowlists(self):
        with BoundedServer(('127.0.0.1', 0), self.c) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
            try:
                def req(path='/v1/historian/subscribe', body=None, headers=None, method='POST'):
                    conn = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=3)
                    conn.request(method, path, json.dumps(body or {'owner': self.owner, 'client': 'tab', 'page': 'one'}), headers or {'Content-Type': 'application/json'})
                    response = conn.getresponse(); result = response.status, json.loads(response.read()); conn.close(); return result
                self.assertEqual(req()[0], 200)
                self.assertEqual(req(headers={'Content-Type': 'application/json', 'Origin': 'http://evil.test'})[0], 403)
                self.assertEqual(req(headers={'Content-Type': 'application/json', 'Host': 'evil.test'})[0], 403)
                self.assertEqual(req(method='GET')[0], 405)
                self.assertEqual(req(body={'data': 'x'*5000})[0], 413)
                self.assertEqual(req(body={'owner': self.owner, 'client': 'tab', 'page': 'unmapped'})[0], 422)
                self.assertEqual(self.source.calls, [])
            finally:
                server.shutdown(); thread.join()


if __name__ == '__main__': unittest.main()
