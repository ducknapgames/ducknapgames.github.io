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
from urllib.parse import parse_qs, urlsplit, unquote

BASE = '/website-statistics/'
UI_ROOT = Path(__file__).resolve().parent
ASSETS = Path(os.environ.get('STATISTICS_ASSETS', '/usr/share/nginx/html/assets'))
LANGUAGES = ('en','ja','ko','de','zh-Hant','fr','es','pt-BR','it','ar','th','tr','id','pl','nl','vi')
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


def dashboard(rows, started, days, language='en'):
    language = language if language in LANGUAGES else 'en'
    copy = json.loads((UI_ROOT/'translations'/f'{language}.json').read_text(encoding='utf-8'))
    t = lambda key: escape(copy[key])
    number = lambda count: f'<span data-count="{count}">{count:,}</span>'
    date_text = lambda value: f'<time datetime="{value}">{value}</time>'
    total = sum(row[3] for row in rows)
    entries = sum(row[3] for row in rows if row[2] != 'Internal navigation')
    daily, sources, pages = {}, {}, {}
    labels = {'Direct / unknown': copy['direct'], 'Internal navigation': copy['internal'], 'Other referral': copy['other']}
    for day, page, source, count in rows:
        daily[day] = daily.get(day, 0) + count
        source = labels.get(source, source)
        sources[source] = sources.get(source, 0) + count
        pages[page] = pages.get(page, 0) + count

    def table(values, heading, paths=False):
        ordered = sorted(values.items(), key=lambda pair: (-pair[1], pair[0]))
        if not ordered:
            return '<p>'+t('empty')+'</p>'
        cells = []
        for label, count in ordered[:160]:
            label = '<bdi dir="ltr">'+escape(label)+'</bdi>' if paths else escape(label)
            cells.append('<tr><td>'+label+'</td><td>'+number(count)+'</td></tr>')
        return '<table><thead><tr><th scope="col">'+t(heading)+'</th><th scope="col">'+t('page_views')+'</th></tr></thead><tbody>'+''.join(cells)+'</tbody></table>'

    today = datetime.now(timezone.utc).date()
    dates = [today - timedelta(days=i) for i in reversed(range(days))]
    maximum = max(daily.values(), default=1)
    bars = ''.join('<div class="statistics-day"><div class="statistics-bar" style="--height:'+str(round(100*daily.get(str(day),0)/maximum,2))+
                   '%" title="'+str(day)+': '+str(daily.get(str(day),0))+' '+t('page_views')+'"></div></div>' for day in dates)
    daily_rows = ''.join('<tr><td>'+date_text(str(day))+'</td><td>'+number(daily.get(str(day), 0))+'</td></tr>' for day in reversed(dates))
    options = ''.join('<option value="'+str(n)+'"'+(' selected' if n==days else '')+'>'+t('days').replace('{n}',str(n))+'</option>' for n in (7,30,90))
    content = f'''<main class="statistics-main wrap" id="main">
      <div class="statistics-heading"><div><p class="eyebrow"><svg class="feather-icon" viewBox="0 0 64 64" aria-hidden="true"><use href="{BASE}assets/studio/feather-symbol.svg#feather"></use></svg>{t('private')}</p>
      <h1>{t('title')}</h1><p class="lead">{t('intro')}</p></div>
      <form class="statistics-period" method="get"><input type="hidden" name="lang" value="{language}"><label for="days">{t('period')}</label><span class="statistics-select"><select name="days" id="days">{options}</select><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" aria-hidden="true"><path d="m4 6 4 4 4-4"/></svg></span><button>{t('apply')}</button></form></div>
      <div class="statistics-meta"><span>ducknap.games</span><span>{t('timezone')}</span><span>{t('started').replace('{date}',date_text(started))}</span></div>
      <div class="statistics-metrics"><section class="statistics-card"><span class="statistics-label">{t('page_views')}</span><strong class="statistics-value">{number(total)}</strong><p>{t('page_views_note')}</p></section>
      <section class="statistics-card"><span class="statistics-label">{t('entry_views')}</span><strong class="statistics-value">{number(entries)}</strong><p>{t('entry_views_note')}</p></section></div>
      <section class="statistics-card"><h2>{t('daily_title')}</h2><p>{t('daily_note')}</p><div class="statistics-chart" aria-hidden="true">{bars}</div><div class="statistics-dates"><span>{date_text(str(dates[0]))}</span><span>{date_text(str(today))}</span></div>
      <details><summary>{t('daily_details')}</summary><table><thead><tr><th scope="col">{t('date')}</th><th scope="col">{t('page_views')}</th></tr></thead><tbody>{daily_rows}</tbody></table></details></section>
      <div class="statistics-grid"><section class="statistics-card"><h2>{t('sources_title')}</h2>{table(sources,'source')}<p>{t('sources_note')}</p></section>
      <section class="statistics-card"><h2>{t('pages_title')}</h2>{table(pages,'page',True)}</section></div>
      <a class="statistics-download" href="?days={days}&amp;lang={language}&amp;format=csv"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3v12m-4-4 4 4 4-4M4 16v5h16v-5"/></svg>{t('download')}</a>
      <section class="statistics-privacy"><h2>{t('privacy_title')}</h2><p>{t('privacy_note')}</p><p>{t('limitations')}</p></section></main>'''
    shell = (UI_ROOT/'shells'/f'{language}.html.template').read_text(encoding='utf-8')
    return shell.replace('<!--STATISTICS_TITLE-->',t('title')+' · Duck Nap Games').replace('<!--STATISTICS_CONTENT-->',content).replace('<!--STATISTICS_DAYS-->',str(days))


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
            if url.path.startswith(BASE+'assets/'):
                self.asset(url.path.removeprefix(BASE+'assets/'))
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
                language = query.get('lang', ['en'])[0]
                body = dashboard(rows, started, days, language).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/csv; charset=utf-8' if is_csv else 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Robots-Tag','noindex, nofollow, noarchive')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Referrer-Policy','no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'")
            if is_csv:
                self.send_header('Content-Disposition','attachment; filename="website-statistics.csv"')
            self.end_headers()
            self.wfile.write(body)
        def asset(self, name):
            types = {'.css':'text/css; charset=utf-8','.js':'text/javascript; charset=utf-8',
                     '.svg':'image/svg+xml','.ttf':'font/ttf','.woff2':'font/woff2',
                     '.png':'image/png','.webp':'image/webp','.jpg':'image/jpeg'}
            name = unquote(name)
            root = UI_ROOT if name in {'statistics.css','statistics.js'} else ASSETS
            path = (root/name).resolve()
            try:
                if not path.is_relative_to(root.resolve()) or path.suffix not in types:
                    raise FileNotFoundError
                body = path.read_bytes()
            except (OSError, ValueError):
                self.send_response(404)
                self.end_headers()
                return
            if path.suffix == '.css':
                body = body.replace(b'/assets/', (BASE+'assets/').encode())
            self.send_response(200)
            self.send_header('Content-Type',types[path.suffix])
            self.send_header('Content-Length',str(len(body)))
            self.send_header('Cache-Control','private, max-age=300')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('X-Robots-Tag','noindex, nofollow, noarchive')
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
