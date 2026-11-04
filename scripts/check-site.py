"""Validate public discovery files and static-page SEO without external dependencies."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import json
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://ducknap.games'

class Page(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.tags = []
        self.ids = []
        self.h1s = 0
        self.feed(text)
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.tags.append((tag, a))
        if 'id' in a: self.ids.append(a['id'])
        if tag == 'h1': self.h1s += 1

pages = {p: Page(p.read_text(encoding='utf-8')) for p in ROOT.rglob('*.html') if '.git' not in p.parts and 'i18n' not in p.relative_to(ROOT).parts}
canonicals = []
for p, page in pages.items():
    text = p.read_text(encoding='utf-8')
    assert len(page.ids) == len(set(page.ids)), f'Duplicate element IDs: {p}'
    assert page.h1s == 1 or p.name == 'privacy.html', f'Expected one H1: {p}'
    canon = [a['href'] for t, a in page.tags if t == 'link' and a.get('rel') == 'canonical']
    assert len(canon) == 1, f'Canonical missing or repeated: {p}'
    if p.name != 'privacy.html':
        expected = BASE + ('/' if p == ROOT / 'index.html' else '/' + p.relative_to(ROOT).as_posix().removesuffix('index.html'))
        assert canon[0] == expected, f'Wrong canonical: {p}'
        canonicals.extend(canon)
        assert len(re.findall(r'<title>.*?</title>', text, re.S)) == 1
        for key in ['description', 'robots', 'twitter:card']:
            assert len([a for t,a in page.tags if t=='meta' and a.get('name')==key and a.get('content')]) == 1, (p,key)
        for key in ['og:title', 'og:description', 'og:url', 'og:image']:
            assert len([a for t,a in page.tags if t=='meta' and a.get('property')==key and a.get('content')]) == 1, (p,key)
        schemas = re.findall(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)
        assert len(schemas) == 1, f'Schema missing: {p}'
        graph = json.loads(schemas[0])['@graph']
        ids = [x['@id'] for x in graph]
        assert len(ids) == len(set(ids)), f'Duplicate schema IDs: {p}'
    for tag, attrs in page.tags:
        for key in ['src', 'href']:
            url = urlsplit(attrs.get(key, ''))
            if url.scheme and url.netloc != 'ducknap.games': continue
            if url.netloc and url.netloc != 'ducknap.games': continue
            if not attrs.get(key) or url.scheme in ['mailto', 'tel']: continue
            target = ROOT / unquote(url.path).lstrip('/') if url.path.startswith('/') else p.parent / unquote(url.path) if url.path else p
            if target.is_dir(): target = target / 'index.html'
            assert target.exists(), f'Missing local destination {attrs[key]} in {p}'
            if url.fragment and target.suffix == '.html':
                assert unquote(url.fragment) in pages[target.resolve()].ids, f'Missing anchor {attrs[key]} in {p}'
assert len(canonicals) == len(set(canonicals))
sitemap = ET.parse(ROOT / 'sitemap.xml')
listed = [e.text for e in sitemap.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
assert set(listed) == set(canonicals) and len(listed) == len(set(listed))
assert BASE + '/sitemap.xml' in (ROOT/'robots.txt').read_text()
catalog = json.loads((ROOT/'games.json').read_text(encoding='utf-8'))
assert len(catalog['games']) == 3
for game in catalog['games']:
    text = (ROOT / 'games' / game['id'] / 'index.html').read_text(encoding='utf-8')
    schema = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S).group(1))
    entry = next(x for x in schema['@graph'] if x['@type']=='VideoGame')
    assert entry['name'] == game['name'] and entry['description'] == game['description']
    assert (ROOT/'games'/game['id']/'index.md').exists()
assert 'art-star' not in (ROOT/'index.html').read_text(encoding='utf-8')
print(f'PASS: {len(canonicals)} canonical pages; metadata, JSON-LD, sitemap, internal links/anchors, game catalog and Markdown verified.')
