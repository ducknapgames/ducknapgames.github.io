"""The privacy boundary and persistence must survive future deployment edits."""
import importlib.util
import json
from pathlib import Path
from datetime import date, timedelta
import tempfile
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer

spec = importlib.util.spec_from_file_location('statistics_server', Path(__file__).parents[1]/'deploy/statistics/server.py')
stats = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stats)


class StatisticsTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.now = date(2026, 11, 4)
        self.counters = stats.Counters(Path(self.directory.name), ['/', '/pl/'], lambda: self.now)

    def tearDown(self):
        self.counters.db.close()
        self.directory.cleanup()

    def send(self, **record):
        return self.counters.accept(b'<190>Nov 4 nginx: '+json.dumps(record).encode())

    def test_only_known_pages_and_source_categories_are_stored(self):
        self.assertTrue(self.send(page='/', source='Instagram'))
        for row in [dict(page='/alice@example.com/', source='Instagram'),
                    dict(page='/?email=alice@example.com', source='Google'),
                    dict(page='/', source='https://example.com/private'),
                    dict(page='/', source='Google', ip='192.0.2.1'),
                    dict(page=['/'], source='Google'), dict(page='/', source=['Google'])]:
            self.assertFalse(self.send(**row))
        for raw in [b'not json', b'[]', b'{"page":', b'{"page":"\xff"}']:
            self.assertFalse(self.counters.accept(raw))
        self.assertEqual(self.counters.report(30)[0], [('2026-11-04', '/', 'Instagram', 1)])

    def test_aggregates_persist_without_individual_records(self):
        for _ in range(5):
            self.send(page='/', source='Google')
        self.assertEqual(self.counters.db.execute('SELECT count(*) FROM views').fetchone()[0], 1)
        self.counters.db.close()
        self.counters = stats.Counters(Path(self.directory.name), ['/'], lambda: self.now)
        self.assertEqual(self.counters.report(7)[0][0][3], 5)
        self.assertEqual([r[1] for r in self.counters.db.execute('PRAGMA table_info(views)')], ['day', 'page', 'source', 'count'])

    def test_ninety_day_retention_and_period_filter(self):
        self.send(page='/', source='Google')
        self.now += timedelta(days=89)
        self.send(page='/', source='Direct / unknown')
        self.assertEqual(len(self.counters.report(90)[0]), 2)
        self.assertEqual(len(self.counters.report(7)[0]), 1)
        self.now += timedelta(days=1)
        self.assertEqual(len(self.counters.report(90)[0]), 1)
        self.assertEqual(self.counters.db.execute('SELECT count(*) FROM views').fetchone()[0], 1)

    def test_report_is_explicit_about_measurement_and_escapes_values(self):
        html = stats.dashboard([('2026-11-04','/<script>','Google',10)], '2026-11-04', 7)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn('not unique visitors or sessions', html)
        self.assertNotIn('<script>', html)

    def test_http_report_is_private_no_store_and_csv_is_aggregate_only(self):
        self.send(page='/', source='YouTube')
        server = ThreadingHTTPServer(('127.0.0.1',0), stats.handler(self.counters))
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        base = 'http://127.0.0.1:'+str(server.server_address[1])
        try:
            with urllib.request.urlopen(base+stats.BASE+'?days=garbage') as response:
                self.assertEqual(response.headers['Cache-Control'], 'no-store')
                self.assertIn('noindex', response.headers['X-Robots-Tag'])
                self.assertIn("frame-ancestors 'none'", response.headers['Content-Security-Policy'])
                self.assertIsNone(response.headers['Set-Cookie'])
            with urllib.request.urlopen(base+stats.BASE+'?days=7&format=csv') as response:
                self.assertEqual(response.read().decode().splitlines(),
                                 ['day_utc,page,source,page_views','2026-11-04,/,YouTube,1'])
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(base+'/counters.sqlite3')
            self.assertEqual(error.exception.code,404)
            error.exception.close()
        finally:
            server.shutdown()
            server.server_close()


if __name__ == '__main__':
    unittest.main()
