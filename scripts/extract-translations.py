"""Create a contextual source catalog from the English HTML templates."""
from pathlib import Path
from html.parser import HTMLParser
import json, re, shutil

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'i18n'
if (DATA/'source.json').exists():
    raise SystemExit('Source catalog already exists. Keep stable translation keys; edit source.json and templates together instead of re-extracting.')
PAGES = ['index.html','games/whose-stuff/index.html','games/fox-on-ice/index.html','games/farm-pals-forever/index.html','privacy/index.html','support/index.html','games/whose-stuff/privacy/index.html','games/whose-stuff/delete-data/index.html','games/farm-pals-forever/privacy/index.html']
FIXED = {'duck nap','GAMES','Duck Nap Games','Whose Stuff?','Whose Stuff? Character Quiz','Fox on Ice','Farm Pals Forever','Instagram','YouTube','TikTok','Discord','X / Twitter','Thor','Mario','Luigi','Loki','Aquaman','Ariel','Elsa','Belle'}
entries = {}
def norm(s): return re.sub(r'\s+', ' ', s).strip()
def add(s, context):
    s = norm(s)
    if not s or s in FIXED or not re.search(r'[^\W\d_]',s) or '@' in s or s.startswith(('https:','mailto:')): return
    entries.setdefault(s, set()).add(context)
class Extract(HTMLParser):
    def __init__(self, page): super().__init__(convert_charrefs=True); self.stack=[]; self.page=page
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag not in {'meta','link','img','br','hr','input','use','path','circle','source','wbr'}: self.stack.append(tag)
        for attr in ('alt','aria-label','title','placeholder'):
            if a.get(attr): add(a[attr],self.page+' / '+tag+' '+attr)
        if tag=='meta' and a.get('name',a.get('property','')) in {'description','og:title','og:description','twitter:title','twitter:description','og:image:alt','twitter:image:alt'}: add(a.get('content',''),self.page+' / metadata')
    def handle_endtag(self,tag):
        if tag in self.stack:
            self.stack=self.stack[:len(self.stack)-1-self.stack[::-1].index(tag)]
    def handle_data(self,s):
        if not any(t in self.stack for t in ('script','style','svg')): add(s,self.page+' / '+('/'.join(self.stack[-3:])))
for page in PAGES:
    target=DATA/'templates'/page; target.parent.mkdir(parents=True,exist_ok=True)
    if not target.exists(): shutil.copyfile(ROOT/page,target)
    text=target.read_text(encoding='utf-8'); Extract(page).feed(text)
    for raw in re.findall(r'<script type="application/ld\+json">(.*?)</script>',text,re.S):
        def walk(x):
            if isinstance(x,dict):
                for k,v in x.items():
                    if k in {'name','description','genre','gamePlatform'} and isinstance(v,str): add(v,page+' / structured data '+k)
                    else: walk(v)
            elif isinstance(x,list):
                for v in x: walk(v)
        walk(json.loads(raw))
for s in ['Language','Choose your language','Search languages','No languages found','Close language picker','Current language','Switch to light mode','Switch to dark mode','Not quite. Try another character.','That’s {name}! You know your stuff.','Try the clues again','Next clue','Who does this belong to?','YOUR NEXT CLUE','A pair of purple seashells','A silver hammer with a short brown handle','Based on your browser','All languages','English','Japanese','Korean','German','Traditional Chinese','French','Spanish','Portuguese (Brazil)','Italian','Arabic','Thai','Turkish','Indonesian','Polish','Dutch','Vietnamese','Read the English original']:
    add(s,'Language picker / dynamic quiz / theme; {name} must remain unchanged')
catalog=[{'key':f's{i:03}','en':s,'context':sorted(c)} for i,(s,c) in enumerate(entries.items(),1)]
(DATA/'source.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(f'{len(catalog)} unique strings; {len(PAGES)} pages')
