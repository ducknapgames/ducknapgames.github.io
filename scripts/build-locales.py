"""Build crawlable, complete translated pages from contextual translation catalogs.

English originals stay at their existing URLs. Every alternate has real server-rendered
copy and reciprocal hreflang links; JavaScript is only for the picker and quiz.
"""
from pathlib import Path
from html.parser import HTMLParser
from html import escape, unescape
from urllib.parse import urlsplit
import json, re, argparse
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://ducknap.games'
LANGUAGES = [
 ('en','English','English','en_US'),('ja','日本語','Japanese','ja_JP'),
 ('ko','한국어','Korean','ko_KR'),('de','Deutsch','German','de_DE'),
 ('zh-Hant','繁體中文','Traditional Chinese','zh_TW'),('fr','Français','French','fr_FR'),
 ('es','Español','Spanish','es_ES'),('pt-BR','Português (Brasil)','Portuguese (Brazil)','pt_BR'),
 ('it','Italiano','Italian','it_IT'),('ar','العربية','Arabic','ar_AR'),
 ('th','ไทย','Thai','th_TH'),('tr','Türkçe','Turkish','tr_TR'),
 ('id','Bahasa Indonesia','Indonesian','id_ID'),('pl','Polski','Polish','pl_PL'),
 ('nl','Nederlands','Dutch','nl_NL'),('vi','Tiếng Việt','Vietnamese','vi_VN')]
FLAGS = dict(zip([x[0] for x in LANGUAGES], ['gb','jp','kr','de','tw','fr','es','br','it','sa','th','tr','id','pl','nl','vn']))
SOURCES = ROOT/'i18n'/'templates'
CATALOG = json.loads((ROOT/'i18n'/'source.json').read_text(encoding='utf-8'))
KEYS = {x['en']:x['key'] for x in CATALOG}
PAGES = sorted(p.relative_to(SOURCES).as_posix() for p in SOURCES.rglob('*.html'))
ROUTES = ['/' if p=='index.html' else '/'+p.removesuffix('index.html') for p in PAGES]
def norm(s): return re.sub(r'\s+',' ',unescape(s)).strip()
def localized(route, code): return route if code=='en' else '/'+code+route
def translate_text(s, translations):
    key=KEYS.get(norm(s))
    if not key: return s
    result=translations[key]
    return re.sub(r'\S(?:[\s\S]*\S)?',lambda _:escape(result,quote=False),s,count=1)
def translate_attr(s,translations):
    key=KEYS.get(norm(s))
    return escape(translations[key],quote=True) if key else s
def page_link(value, code):
    raw=unescape(value); u=urlsplit(raw)
    if u.scheme or u.netloc or not raw.startswith('/'): return value
    if u.path in ROUTES:
        return escape(localized(u.path,code)+('?' + u.query if u.query else '')+('#'+u.fragment if u.fragment else ''),quote=True)
    return value
def schema_translate(value,code,translations):
    if isinstance(value,list): return [schema_translate(x,code,translations) for x in value]
    if isinstance(value,dict):
        output={}
        for k,v in value.items():
            if k=='inLanguage': output[k]=[x[0] for x in LANGUAGES] if value.get('@type')=='WebSite' else code
            elif k in {'name','description','genre','gamePlatform'} and isinstance(v,str): output[k]=translations.get(KEYS.get(norm(v)),v)
            elif k in {'@id','url','item'} and isinstance(v,str) and v.startswith(BASE):
                u=urlsplit(v)
                # Organization and site entity IDs remain stable across languages.
                if u.fragment in {'studio','website'}: output[k]=v
                elif u.path in ROUTES: output[k]=BASE+localized(u.path,code)+('#'+u.fragment if u.fragment else '')
                else: output[k]=v
            else: output[k]=schema_translate(v,code,translations)
        return output
    if isinstance(value,str): return translations.get(KEYS.get(norm(value)),value)
    return value
def picker(code,route,t):
    tr=lambda s:escape(t[KEYS[s]])
    current=next(x[1] for x in LANGUAGES if x[0]==code)
    globe=f'<img class="language-current-flag" src="/assets/language-flags/{FLAGS[code]}.svg" width="30" height="22" alt="" aria-hidden="true">'
    button=f'<button class="language-toggle preferences-language" type="button" aria-haspopup="dialog" aria-controls="language-dialog" aria-label="{tr("Language")}: {escape(current)}"><span class="preferences-copy"><span class="preferences-label">{tr("Language")}</span><span class="preferences-value">{globe}<span lang="{code}">{escape(current)}</span></span></span><svg class="preferences-chevron" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="m6 4 4 4-4 4"/></svg></button>'
    items=[]
    for lc,native,label,_ in LANGUAGES:
        selected=lc==code
        flag=f'<span class="language-flag" aria-hidden="true"><img src="/assets/language-flags/{FLAGS[lc]}.svg" width="30" height="22" alt=""></span>'
        items.append(f'<a class="language-option" href="{localized(route,lc)}" hreflang="{lc}" lang="{lc}" data-language="{lc}" data-search="{escape(native+" "+label+" "+t[KEYS[label]],quote=True)}"'+(' aria-current="true"' if selected else '')+f'>{flag}<span class="language-copy"><span class="language-name" dir="auto">{escape(native)}</span><span class="language-description" lang="{code}">{tr(label)}</span></span>'+'</a>')
    dialog=f'<dialog class="language-dialog" id="language-dialog" aria-labelledby="language-title"><div class="language-dialog-header"><h2 id="language-title">{tr("Choose your language")}</h2><button class="language-close" type="button" aria-label="{tr("Close language picker")}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18"/></svg></button></div><div class="language-grid">'+''.join(items)+f'</div></dialog>'
    return button,dialog
def render(page,code,t,available):
    route='/' if page=='index.html' else '/'+page.removesuffix('index.html')
    source=(SOURCES/page).read_text(encoding='utf-8')
    chunks=re.split(r'(<[^>]+>)',source)
    skip=[]; output=[]
    for chunk in chunks:
        if chunk.startswith('<'):
            tag=re.match(r'<(/?)([\w:-]+)',chunk)
            if tag:
                closing,name=tag.groups(); name=name.lower()
                if name in {'script','style','svg'}:
                    if closing:
                        if skip: skip.pop()
                    else: skip.append(name)
                if not skip and not closing:
                    attrs=dict(re.findall(r'([\w:-]+)="([^"]*)"',chunk))
                    def attr(m):
                        key,value=m.groups()
                        if key in {'alt','aria-label','title','placeholder'}: value=translate_attr(value,t)
                        if name=='meta' and key=='content':
                            kind=attrs.get('name',attrs.get('property'))
                            if kind in {'description','og:title','og:description','twitter:title','twitter:description','og:image:alt','twitter:image:alt'}: value=translate_attr(value,t)
                            if kind=='og:locale': value=next(x[3] for x in LANGUAGES if x[0]==code)
                            if kind=='og:url': value=BASE+localized(route,code)
                        if key=='href' and name=='a': value=page_link(value,code)
                        if name=='link' and key=='href' and attrs.get('rel')=='canonical': value=BASE+localized(route,code)
                        if name=='link' and key=='href' and attrs.get('type')=='text/markdown': value=localized(route,code)+'index.md'
                        if name=='link' and key=='href' and attrs.get('type')=='application/json': value=localized('/games.json',code)
                        return f'{key}="{value}"'
                    chunk=re.sub(r'([\w:-]+)="([^"]*)"',attr,chunk)
            output.append(chunk)
        elif skip: output.append(chunk)
        else: output.append(translate_text(chunk,t))
    html=''.join(output)
    # Reserve a real header row above the clue. Long translated labels must not
    # compete with either the game wordmark or the counter inside the tilted card.
    brand=re.search(r'<div class="floating-icon">.*?</div>',html,re.S)
    sticker=re.search(r'<span class="play-sticker".*?</span>',html,re.S)
    if brand and sticker:
        html=html.replace(brand[0],'__CLUE_BRAND_ROW__',1).replace(sticker[0],'',1)
        html=html.replace('__CLUE_BRAND_ROW__','<div class="clue-brand-row">'+brand[0]+sticker[0]+'</div>',1)
    html=re.sub(r'<html[^>]*>',f'<html lang="{code}" dir="{"rtl" if code=="ar" else "ltr"}">',html,count=1)
    html=re.sub(r'(<script type="application/ld\+json">)(.*?)(</script>)',lambda m:m[1]+json.dumps(schema_translate(json.loads(m[2]),code,t),ensure_ascii=False)+m[3],html,flags=re.S)
    alternates='\n'.join(f'<link rel="alternate" hreflang="{lc}" href="{BASE+localized(route,lc)}">' for lc in available)
    alternates+=f'\n<link rel="alternate" hreflang="x-default" href="{BASE+route}">'
    html=html.replace('</head>',alternates+'\n<link rel="stylesheet" href="/assets/languages.css?v=language-picker-3">\n<link rel="stylesheet" href="/assets/header.css?v=floating-c-4">\n<script src="/assets/languages.js?v=language-picker-3" defer></script>\n<script src="/assets/header.js?v=floating-c-4" defer></script>\n</head>')
    button,dialog=picker(code,route,t)
    tr=lambda s:escape(t[KEYS[s]])
    trigger=f'<button class="preferences-trigger" type="button" aria-label="{tr("Preferences")}" aria-expanded="false" aria-controls="preferences-panel"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" aria-hidden="true"><path d="M4 7h8m4 0h4M4 17h3m4 0h9"/><circle cx="14" cy="7" r="2"/><circle cx="9" cy="17" r="2"/></svg><span dir="ltr">{code.upper()}</span></button>'
    def preferences(m):
        return '<div class="header-preferences">'+trigger+f'<section class="preferences-panel" id="preferences-panel" aria-labelledby="preferences-title" hidden><h2 id="preferences-title">{tr("Preferences")}</h2>'+button+f'<div class="preferences-appearance"><span>{tr("Appearance")}</span>'+m[0]+'</div></section></div>'
    html=re.sub(r'<button class="theme-toggle".*?</button>',preferences,html,count=1,flags=re.S)
    dictionary={s:t[k] for s,k in KEYS.items() if s in ['Switch to light mode','Switch to dark mode','Not quite. Try another character.','That’s {name}! You know your stuff.','Try the clues again','Next clue','Who does this belong to?','YOUR FIRST CLUE','YOUR NEXT CLUE','A red cap and a plumber’s wrench','A pair of purple seashells','A silver hammer with a short brown handle','Based on your browser','Thor','Mario','Luigi','Loki','Aquaman','Elsa','Belle','Ariel']}
    data=json.dumps(dictionary,ensure_ascii=False).replace('<','\\u003c')
    html=html.replace('</body>',dialog+'<script type="application/json" id="site-translations">'+data+'</script></body>')
    if code!='en' and ('/privacy/' in route or '/delete-data/' in route):
        html=html.replace('</main>',f'<p class="original-policy"><a href="{route}" lang="en">{escape(t[KEYS["Read the English original"]])}</a></p></main>')
    fallback='<noscript><nav class="wrap language-fallback" aria-label="'+escape(t[KEYS['All languages']])+'">'+' · '.join(f'<a href="{localized(route,lc)}" lang="{lc}" hreflang="{lc}">{escape(native)}</a>' for lc,native,*_ in LANGUAGES)+'</nav></noscript>'
    html=html.replace('</footer>',fallback+'</footer>')
    return html
class PlainText(HTMLParser):
    def __init__(self): super().__init__(); self.parts=[]; self.ignore=0; self.main=False
    def handle_starttag(self,tag,attrs):
        if tag=='main': self.main=True
        if tag in {'script','style','svg'}: self.ignore+=1
        if self.main and tag in {'p','h1','h2','h3','li','section','article'}: self.parts.append('\n\n')
    def handle_endtag(self,tag):
        if tag=='main': self.main=False
        if tag in {'script','style','svg'}: self.ignore=max(0,self.ignore-1)
    def handle_data(self,data):
        if self.main and not self.ignore and data.strip(): self.parts.append(norm(data)+' ')
    def text(self):
        text = re.sub(r'\n\n\s*\n\n','\n\n',''.join(self.parts)).strip()
        return '\n'.join(line.rstrip() for line in text.splitlines())+'\n'
def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--available-only',action='store_true'); args=parser.parse_args()
    catalogs={'en':{x['key']:x['en'] for x in CATALOG}}
    for code,*_ in LANGUAGES[1:]:
        file=ROOT/'i18n'/'translations'/f'{code}.json'
        if not file.exists():
            if args.available_only: continue
            raise SystemExit(f'Missing translation catalog: {file}')
        t=json.loads(file.read_text(encoding='utf-8-sig'))
        missing=set(catalogs['en'])-set(t)
        if missing: raise SystemExit(f'{code}: missing {len(missing)} translations')
        for k,v in t.items():
            if not isinstance(v,str) or not v.strip(): raise SystemExit(f'{code}/{k}: empty translation')
            if '{name}' in catalogs['en'].get(k,'') and '{name}' not in v: raise SystemExit(f'{code}/{k}: missing name placeholder')
        catalogs[code]=t
    for code,t in catalogs.items():
        for page in PAGES:
            target=ROOT/page if code=='en' else ROOT/code/page
            target.parent.mkdir(parents=True,exist_ok=True)
            html=render(page,code,t,catalogs)
            target.write_text(html,encoding='utf-8')
            if code!='en':
                plain=PlainText(); plain.feed(html)
                target.with_suffix('.md').write_text(plain.text(),encoding='utf-8')
        if code!='en':
            game_catalog=json.loads((ROOT/'games.json').read_text(encoding='utf-8'))
            game_catalog=schema_translate(game_catalog,code,t)
            game_catalog['language']=code
            game_catalog['website']=BASE+'/'+code+'/'
            # Reuse the translated visible facts rather than publishing English
            # fragments that never existed as whole source-catalog strings.
            for game in game_catalog['games']:
                game_html=(ROOT/code/'games'/game['id']/'index.html').read_text(encoding='utf-8')
                facts=re.search(r'<ul class="game-facts"[^>]*>(.*?)</ul>',game_html,re.S)
                if facts:
                    game['features']=[norm(re.sub(r'<[^>]+>',' ',li)) for li in re.findall(r'<li[^>]*>(.*?)</li>',facts[1],re.S)]
                if game['id']=='whose-stuff':
                    game['status']=t[KEYS['Available on Google Play.']]
                    game['features'].append(t[KEYS['The Android game contains ads and optional in-app purchases. Offline gameplay is available; ads, purchases and online services need a connection.']])
                if game['id']=='fox-on-ice':game['status']=t[KEYS['Browser demo available.']]
            (ROOT/code/'games.json').write_text(json.dumps(game_catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    ns='http://www.sitemaps.org/schemas/sitemap/0.9'; xh='http://www.w3.org/1999/xhtml'
    ET.register_namespace('',ns); ET.register_namespace('xhtml',xh)
    tree=ET.Element('{'+ns+'}urlset')
    for code in catalogs:
        for route in ROUTES:
            url=ET.SubElement(tree,'{'+ns+'}url'); ET.SubElement(url,'{'+ns+'}loc').text=BASE+localized(route,code)
            for other in [*catalogs,'x-default']:
                ET.SubElement(url,'{'+xh+'}link',{'rel':'alternate','hreflang':other,'href':BASE+localized(route,'en' if other=='x-default' else other)})
    ET.indent(tree,space='  '); ET.ElementTree(tree).write(ROOT/'sitemap.xml',encoding='utf-8',xml_declaration=True)
    print(f'Generated {len(PAGES)*len(catalogs)} pages in {len(catalogs)} languages.')
if __name__=='__main__': main()
