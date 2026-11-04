"""Aggregate nginx page requests. No individual request records or visitor IDs."""
from datetime import date, datetime, timedelta, timezone
import csv
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import socket
import sqlite3
import threading
from urllib.parse import parse_qs, urlsplit

BASE = '/website-statistics/'
SOURCES = ('Direct / unknown', 'Internal navigation', 'Google', 'Bing', 'Instagram',
           'Facebook', 'TikTok', 'YouTube', 'X', 'LinkedIn', 'GitHub', 'Other referral')
DATA = Path(os.environ.get('STATISTICS_DATA', '/var/lib/ducknap-statistics'))
ROUTES = Path(os.environ.get('STATISTICS_ROUTES', '/opt/ducknap-statistics/routes.json'))


class Counters:
    def __init__(self, directory, routes, today=None):
        directory.mkdir(parents=True, exist_ok=True)
        self.today = today or (lambda: datetime.now(timezone.utc).date())
        self.routes = set(routes)
        self.lock = threading.Lock()
        self.db = sqlite3.connect(directory / 'counters.sqlite3', check_same_thread=False)
        self.db.execute('PRAGMA secure_delete=ON')
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS views (
                day TEXT NOT NULL, page TEXT NOT NULL, source TEXT NOT NULL,
                count INTEGER NOT NULL, PRIMARY KEY(day,page,source));
            CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        ''')
        self.db.execute("INSERT OR IGNORE INTO metadata VALUES ('started',?)", (str(self.today()),))
        self.last_pruned = None
        self._prune()
        self.db.commit()

    def _prune(self):
        today = self.today()
        if self.last_pruned != today:
            self.db.execute('DELETE FROM views WHERE day < ?', (str(today - timedelta(days=89)),))
            self.last_pruned = today

    def accept(self, data):
        # nginx syslog adds a header before the JSON. Never save that header.
        try:
            record = json.loads(data[data.index(b'{'):].decode('utf-8'))
        except (ValueError, UnicodeError, AttributeError):
            return False
        if (not isinstance(record, dict) or set(record) != {'page', 'source'}
                or not isinstance(record['page'], str) or record['page'] not in self.routes
                or record['source'] not in SOURCES):
            return False
        with self.lock:
            self._prune()
            self.db.execute('''INSERT INTO views VALUES (?,?,?,1)
                ON CONFLICT(day,page,source) DO UPDATE SET count=count+1''',
                (str(self.today()), record['page'], record['source']))
            self.db.commit()
        return True

    def report(self, days):
        with self.lock:
            self._prune()
            self.db.commit()
            rows = self.db.execute('SELECT day,page,source,count FROM views WHERE day >= ? ORDER BY day,page,source',
                                   (str(self.today() - timedelta(days=days-1)),)).fetchall()
            started = self.db.execute("SELECT value FROM metadata WHERE key='started'").fetchone()[0]
        return rows, started


def dashboard(rows, started, days):
    total = sum(row[3] for row in rows)
    entries = sum(row[3] for row in rows if row[2] != 'Internal navigation')
    daily, sources, pages = {}, {}, {}
    for day, page, source, count in rows:
        daily[day] = daily.get(day, 0) + count
        sources[source] = sources.get(source, 0) + count
        pages[page] = pages.get(page, 0) + count

    def table(values, heading):
        ordered = sorted(values.items(), key=lambda pair: (-pair[1], pair[0]))
        if not ordered:
            return '<p class="muted">No page views recorded in this period.</p>'
        return '<table><thead><tr><th>'+heading+'</th><th>Page views</th></tr></thead><tbody>' + ''.join(
            '<tr><td>'+escape(label)+'</td><td>'+format(count, ',')+'</td></tr>'
            for label, count in ordered[:160]) + '</tbody></table>'

    today = datetime.now(timezone.utc).date()
    dates = [today - timedelta(days=i) for i in reversed(range(days))]
    maximum = max(daily.values(), default=1)
    bars = ''.join('<div class="day"><div class="bar" style="--height:'+str(round(100*daily.get(str(day),0)/maximum,2))+
                   '%" title="'+str(day)+': '+str(daily.get(str(day),0))+' page views"></div></div>' for day in dates)
    daily_rows = ''.join('<tr><td>'+str(day)+'</td><td>'+format(daily.get(str(day), 0), ',')+'</td></tr>' for day in reversed(dates))
    options = ''.join('<option value="'+str(n)+'"'+(' selected' if n==days else '')+'>'+str(n)+' days</option>' for n in (7,30,90))
    return '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <meta name="robots" content="noindex,nofollow,noarchive"><title>Website statistics · Duck Nap Games</title>
    <style>
    :root{color-scheme:light dark;--bg:#19171d;--panel:#25212b;--text:#f5f1e9;--muted:#c7bdcc;--line:#514857;--accent:#f5bd79}
    @media(prefers-color-scheme:light){:root{--bg:#faf7f1;--panel:#fff;--text:#29252e;--muted:#665b6e;--line:#c4b7c7;--accent:#9d5620}}
    *{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:16px/1.6 system-ui,sans-serif}
    main{max-width:1120px;margin:auto;padding:40px 24px}header{display:flex;align-items:flex-start;justify-content:space-between;gap:24px;flex-wrap:wrap}
    h1{font-size:clamp(28px,5vw,42px);line-height:1.15;margin:8px 0 14px}h2{font-size:20px;margin:0 0 18px}p{margin:8px 0}.eyebrow{color:var(--accent);font-size:12px;font-weight:750;letter-spacing:.1em}
    .muted,small{color:var(--muted)}a{color:var(--accent);text-underline-offset:4px}select,button{font:inherit;background:var(--panel);color:var(--text);border:1px solid var(--line);border-radius:8px;padding:9px 14px}
    button{cursor:pointer}label{display:block;font-size:13px;margin-bottom:6px}.metrics,.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin:28px 0}.card{padding:26px;background:var(--panel);border:1px solid var(--line);border-radius:18px}
    .value{display:block;font-size:38px;font-weight:750;line-height:1.3}.chart{height:190px;display:flex;gap:3px;align-items:flex-end;border-bottom:1px solid var(--line);margin-top:24px}.day{height:100%;flex:1;display:flex;align-items:flex-end}.bar{width:100%;height:var(--height);background:var(--accent);border-radius:4px 4px 0 0}.dates{display:flex;justify-content:space-between;font-size:12px;margin-top:8px;color:var(--muted)}
    table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}th,td{padding:12px 0;border-bottom:1px solid var(--line);text-align:left;overflow-wrap:anywhere}td:first-child{padding-right:18px}th{font-size:12px;color:var(--muted)}th:last-child,td:last-child{text-align:right;white-space:nowrap}summary{cursor:pointer;margin-top:20px;color:var(--accent)}.foot{border-top:1px solid var(--line);padding-top:24px;margin-top:28px}details table{margin-top:12px}
    @media(max-width:680px){main{padding:24px 16px}.grid,.metrics{grid-template-columns:1fr;gap:14px;margin:20px 0}.card{padding:20px}.chart{height:145px}}
    </style></head><body><main><header><div><p class="eyebrow">DUCK NAP GAMES · PRIVATE</p><h1>Website statistics</h1><p class="muted">ducknap.games · Daily totals in UTC · Started '''+escape(started)+'''</p></div>
    <form method="get"><label for="days">Reporting period</label><select name="days" id="days">'''+options+'''</select> <button>Apply</button></form></header>
    <div class="metrics"><section class="card"><span class="muted">Page views</span><strong class="value">'''+format(total,',')+'''</strong><small>Successful page loads, including repeat views.</small></section>
    <section class="card"><span class="muted">Views without an internal referrer</span><strong class="value">'''+format(entries,',')+'''</strong><small>External referrals and direct / unknown source. These are not unique visitors or sessions.</small></section></div>
    <section class="card"><h2>Daily page views</h2><p class="muted">Known bots, assets, errors and privacy opt-out headers are excluded.</p><div class="chart" aria-hidden="true">'''+bars+'''</div><div class="dates"><span>'''+str(dates[0])+'''</span><span>'''+str(today)+'''</span></div>
    <details><summary>Exact daily counts</summary><table><thead><tr><th>Date (UTC)</th><th>Page views</th></tr></thead><tbody>'''+daily_rows+'''</tbody></table></details></section>
    <div class="grid"><section class="card"><h2>Traffic sources</h2>'''+table(sources,'Source')+'''<p class="muted">Sources are broad groups from the referrer or a recognised utm_source. Apps may hide referrers; unrecognised campaign values are ignored.</p></section>
    <section class="card"><h2>Pages viewed</h2>'''+table(pages,'Page')+'''</section></div>
    <p><a href="?days='''+str(days)+'''&amp;format=csv">Download daily totals (CSV)</a></p><div class="foot"><p>No cookies, visitor IDs, IP addresses, full referrers, raw browser strings or individual browsing histories are stored in these statistics.</p>
    <p class="muted">Daily aggregates are kept for 90 days. Page views are not people. Reloads count again, and bot filtering is approximate. Collection is best effort and excludes the GitHub Pages mirror. Refresh this page for current totals.</p></div></main></body></html>'''


def handler(counters):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_GET(self):
            url = urlsplit(self.path)
            if url.path == '/health':
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'ok')
                return
            if url.path != BASE:
                self.send_response(404)
                self.end_headers()
                return
            query = parse_qs(url.query)
            try:
                days = int(query.get('days', ['30'])[0])
            except ValueError:
                days = 30
            if days not in (7, 30, 90):
                days = 30
            rows, started = counters.report(days)
            is_csv = query.get('format') == ['csv']
            if is_csv:
                text = io.StringIO(newline='')
                writer = csv.writer(text)
                writer.writerow(['day_utc','page','source','page_views'])
                writer.writerows(rows)
                body = text.getvalue().encode()
            else:
                body = dashboard(rows, started, days).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/csv; charset=utf-8' if is_csv else 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Robots-Tag','noindex, nofollow, noarchive')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Referrer-Policy','no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'")
            if is_csv:
                self.send_header('Content-Disposition','attachment; filename="website-statistics.csv"')
            self.end_headers()
            self.wfile.write(body)
    return Handler


def collect(counters, sock):
    while True:
        data = sock.recv(2048)
        try:
            counters.accept(data)
        except sqlite3.Error:
            # Metrics are best effort. Do not log the packet or interrupt nginx.
            print('Could not update statistics counters', flush=True)


if __name__ == '__main__':
    os.umask(0o077)
    counters = Counters(DATA, json.loads(ROUTES.read_text()))
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('127.0.0.1', int(os.environ.get('STATISTICS_UDP_PORT', '9514'))))
    threading.Thread(target=collect, args=(counters, sock), daemon=True).start()
    server = ThreadingHTTPServer((os.environ.get('STATISTICS_BIND', '0.0.0.0'),
                                int(os.environ.get('STATISTICS_PORT', '8081'))), handler(counters))
    server.serve_forever()
