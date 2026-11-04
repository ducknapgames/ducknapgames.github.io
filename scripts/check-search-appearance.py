"""Check consistent homepage search hints and the public PNG favicon."""
from pathlib import Path
from html import unescape
import json
import re
import struct

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://ducknap.games'
source = {item['key']: item['en'] for item in json.loads((ROOT / 'i18n/source.json').read_text(encoding='utf-8'))}
catalogs = {'en': source}
catalogs.update({p.stem: json.loads(p.read_text(encoding='utf-8')) for p in (ROOT / 'i18n/translations').glob('*.json')})
favicon = (ROOT / 'assets/studio/favicon.png').read_bytes()
assert favicon[:8] == b'\x89PNG\r\n\x1a\n'
assert struct.unpack('>II', favicon[16:24]) == (192, 192)
assert (ROOT / 'assets/studio/favicon.ico').read_bytes()[:4] == b'\0\0\1\0'
for code, catalog in catalogs.items():
    page = ROOT / ('index.html' if code == 'en' else code + '/index.html')
    text = page.read_text(encoding='utf-8')
    title = unescape(re.search(r'<title>(.*?)</title>', text)[1])
    assert title == catalog['s002'], (code, 'title')
    description = unescape(re.search(r'<meta name="description" content="([^"]+)"', text)[1])
    assert description == catalog['s001'], (code, 'description')
    for key, value in [('og:title', title), ('og:description', description)]:
        match = re.search(r'<meta property="' + key + r'" content="([^"]+)"', text)
        assert match and unescape(match[1]) == value, (code, key)
    assert '/assets/studio/favicon.png' in text, code
    assert BASE + '/assets/studio/search-preview-v2.jpg' in text, code
    graph = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)[1])['@graph']
    website = next(node for node in graph if node['@type'] == 'WebSite')
    assert website['name'] == 'Duck Nap Games', code
    collection = next(node for node in graph if node['@type'] == 'CollectionPage')
    assert collection['name'] == title and collection['description'] == description, code
    image = next(node for node in graph if node['@id'] == collection['primaryImageOfPage']['@id'])
    assert image['url'] == BASE + '/assets/studio/search-square-v2.jpg', code
    assert (image['width'], image['height']) == (800, 800), code
print(f'PASS: {len(catalogs)} homepage titles/descriptions, stable site name, square/wide image hints and 192px PNG favicon.')
