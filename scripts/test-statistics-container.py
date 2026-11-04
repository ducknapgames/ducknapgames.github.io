"""Run against a fresh, loopback-only QA Docker container (never production)."""
import csv
import io
import time
import urllib.request
import urllib.error

SITE = 'http://127.0.0.1:9484'
REPORT = 'http://127.0.0.1:9485/website-statistics/?days=7&format=csv'
UA = 'Mozilla/5.0 DuckNap-QA-browser'


def request(path, headers=None, method='GET', status=200):
    merged = {'Host':'ducknap.games', 'User-Agent':UA}
    merged.update(headers or {})
    req = urllib.request.Request(SITE+path, headers=merged, method=method)
    try:
        response = urllib.request.urlopen(req, timeout=5)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        assert response.code == status, (path, response.code)
        response.read()


with urllib.request.urlopen(REPORT, timeout=5) as response:
    assert len(list(csv.reader(io.StringIO(response.read().decode())))) == 1, 'Use a fresh QA volume'

request('/')
request('/?utm_source=instagram&secret=DO_NOT_STORE_SENTINEL')
request('/pl/', {'Referer':'https://youtu.be/DO_NOT_STORE_SENTINEL'})
request('/?utm_source=unknown-personal-value', {'Referer':'https://private.example/DO_NOT_STORE_SENTINEL'})
request('/', {'Referer':'https://ducknap.games/privacy/website/'})
request('/robots.txt')
request('/not-a-real-page/', status=404)
request('/', {'User-Agent':'Googlebot'})
request('/', {'DNT':'1'})
request('/', {'Sec-GPC':'1'})
request('/', method='HEAD')
request('/', method='POST', status=405)
request('/website-statistics/', status=404)
request('/var/lib/ducknap-statistics/counters.sqlite3', status=404)

for _ in range(30):
    with urllib.request.urlopen(REPORT, timeout=5) as response:
        text = response.read().decode()
    rows = list(csv.DictReader(io.StringIO(text)))
    if sum(int(row['page_views']) for row in rows) == 5:
        break
    time.sleep(.1)
assert sum(int(row['page_views']) for row in rows) == 5, rows
assert {row['source'] for row in rows} == {'Direct / unknown','Instagram','YouTube','Other referral','Internal navigation'}, rows
assert {row['page'] for row in rows} == {'/','/pl/'}
assert 'DO_NOT_STORE_SENTINEL' not in text
assert 'unknown-personal-value' not in text
print('PASS: real nginx page/source counts, bots, DNT/GPC, assets, errors, methods, private-path isolation and aggregate-only export.')
