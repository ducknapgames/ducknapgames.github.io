"""Check localization coverage, crawlable alternates and translated dynamic UI."""
from pathlib import Path
from html.parser import HTMLParser
from html import unescape
from urllib.parse import urlsplit
import json,re,importlib.util
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('builder',ROOT/'scripts'/'build-locales.py')
build=importlib.util.module_from_spec(spec);spec.loader.exec_module(build)
class Page(HTMLParser):
    def __init__(self,text):
        super().__init__();self.tags=[];self.main=False;self.skip=0;self.text=[];self.feed(text)
    def handle_starttag(self,tag,attrs):
        self.tags.append((tag,dict(attrs)))
        if tag=='main':self.main=True
        if tag in {'svg','script','style'}:self.skip+=1
    def handle_endtag(self,tag):
        if tag=='main':self.main=False
        if tag in {'svg','script','style'}:self.skip=max(0,self.skip-1)
    def handle_data(self,s):
        if self.main and not self.skip and s.strip():self.text.append(build.norm(s))
codes=[x[0] for x in build.LANGUAGES];keys={x['key'] for x in build.CATALOG}
for code in codes:
    data={x['key']:x['en'] for x in build.CATALOG} if code=='en' else json.loads((ROOT/'i18n'/'translations'/f'{code}.json').read_text(encoding='utf-8-sig'))
    assert set(data)==keys, f'{code}: catalog key mismatch'
    assert all(isinstance(v,str) and v.strip() for v in data.values()),code
    assert all('{name}' in data[x['key']] for x in build.CATALOG if '{name}' in x['en']),code
    assert not any(re.search('[\u202a-\u202e\u2066-\u2069]',v) for v in data.values()),f'{code}: hidden bidi controls'
    for page,route in zip(build.PAGES,build.ROUTES):
        path=ROOT/(page if code=='en' else code+'/'+page)
        text=path.read_text(encoding='utf-8'); parsed=Page(text)
        # Translated postpositions can replace source punctuation after a link.
        # Languages that separate words must retain that boundary in the HTML.
        if code in {'en','de','fr','es','pt-BR','it','nl','pl','tr','id','vi','ar'}:
            for tail in re.findall(r'</a>([^<]+)',text):
                tail=unescape(tail)
                assert not tail[0].isalpha(),f'{path}: missing word separator after link: {tail[:50]}'
        html=next(a for tag,a in parsed.tags if tag=='html')
        assert html['lang']==code and html['dir']==('rtl' if code=='ar' else 'ltr'),path
        alternates={a['hreflang']:a['href'] for tag,a in parsed.tags if tag=='link' and 'hreflang' in a}
        assert set(alternates)==set(codes)|{'x-default'},path
        for lc,target in alternates.items():
            assert target==build.BASE+build.localized(route,'en' if lc=='x-default' else lc),(path,lc)
        options=[a for tag,a in parsed.tags if tag=='a' and 'data-language' in a]
        assert len(options)==16 and sum(a.get('aria-current')=='true' for a in options)==1,path
        assert all(a['href']==build.localized(route,a['data-language']) for a in options),path
        footer=re.search(r'<div class="footer-links">(.*?)</div>',text,re.S)
        assert footer and f'href="{build.localized("/privacy/website/",code)}"' in footer[1],f'{path}: footer must link to website privacy'
        if page=='privacy/website/index.html':
            assert path.with_suffix('.md').exists(),f'{path}: missing readable policy alternate'
        if page in {'games/whose-stuff/privacy/index.html','games/farm-pals-forever/privacy/index.html'}:
            assert data[build.KEYS['Read the website privacy policy']] in parsed.text,f'{path}: missing website-policy reference'
        dictionary=json.loads(re.search(r'<script type="application/json" id="site-translations">(.*?)</script>',text,re.S)[1])
        assert dictionary['That’s {name}! You know your stuff.']==data[build.KEYS['That’s {name}! You know your stuff.']],path
        assert dictionary['Switch to light mode']==data[build.KEYS['Switch to light mode']],path
        for name in ['Thor','Mario','Luigi','Loki','Aquaman','Elsa','Belle','Ariel']:
            assert dictionary[name]==data[build.KEYS[name]],(path,name)
        if page=='index.html':
            answers=re.findall(r'<button[^>]+data-answer="([^"]+)"[^>]*>(.*?)</button',text,re.S)
            assert [name for name,_ in answers]==['Thor','Mario','Luigi'],path
            assert all(build.norm(label)==data[build.KEYS[name]] for name,label in answers),path
        for s in parsed.text:
            key=build.KEYS.get(s)
            if code!='en' and key:
                assert data[key]==s,f'{path}: untranslated main text {s[:90]}'
        if code!='en':assert path.with_suffix('.md').exists(),path
print(f'PASS: 16 complete catalogs; {len(codes)*len(build.PAGES)} pages; RTL, localized routes, reciprocal alternates, quiz/theme copy and plain-text pages.')
