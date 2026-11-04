"""Reuse the actual localized website shell; do not maintain a second header."""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
BASE = '/website-statistics/'
CODES = ('en','ja','ko','de','zh-Hant','fr','es','pt-BR','it','ar','th','tr','id','pl','nl','vi')


def build():
    target = ROOT/'deploy/statistics/shells'
    target.mkdir(exist_ok=True)
    for code in CODES:
        prefix = '' if code == 'en' else code+'/'
        source = (ROOT/prefix/'privacy/website/index.html').read_text(encoding='utf-8')
        header = re.search(r'<header class="header wrap">.*?</header>',source,re.S)[0]
        footer = re.search(r'<footer class="footer">.*?</footer>',source,re.S)[0]
        dialog = re.search(r'<dialog class="language-dialog".*?</dialog>',source,re.S)[0]
        dictionary = re.search(r'<script type="application/json" id="site-translations">.*?</script>',source,re.S)[0]
        skip = re.search(r'<a class="skip-link".*?</a>',source,re.S)[0]
        styles = re.findall(r'<link rel="stylesheet"[^>]*>',source)
        scripts = re.findall(r'<script src="[^"]+"[^>]*></script>',source)
        html = '<!doctype html><html lang="'+code+'" dir="'+('rtl' if code=='ar' else 'ltr')+'"><head>'
        html += '<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow,noarchive"><meta name="color-scheme" content="light dark"><title><!--STATISTICS_TITLE--></title>'
        html += '<link rel="icon" href="/assets/studio/favicon.svg?v=theme-1" type="image/svg+xml">'
        html += ''.join(scripts[:1])+''.join(styles)+''.join(scripts[1:])
        html += '<link rel="stylesheet" href="/assets/statistics.css?v=studio-1"><script src="/assets/statistics.js?v=studio-1" defer></script>'
        html += '</head><body class="statistics-page">'+skip+header+'<!--STATISTICS_CONTENT-->'+footer+dialog+dictionary+'</body></html>'
        # Public navigation keeps its localized studio destinations.
        html = re.sub(r'href="(/(?!assets/)[^"]*)"',lambda m:'href="https://ducknap.games'+m[1]+'"',html)
        # Language changes stay inside the private report and retain the period.
        html = re.sub(r'(<a class="language-option" href=")[^"]*(" hreflang="([^"]+)")',
                      lambda m:m[1]+BASE+'?lang='+m[3]+'&amp;days=<!--STATISTICS_DAYS-->'+m[2],html)
        html = re.sub(r'(<a href=")[^"]*(" lang="([^"]+)" hreflang="[^"]+")',
                      lambda m:m[1]+BASE+'?lang='+m[3]+'&amp;days=<!--STATISTICS_DAYS-->'+m[2],html)
        html = html.replace('/assets/',BASE+'assets/')
        (target/(code+'.html.template')).write_text(html,encoding='utf-8')
    print('Built 16 private dashboard shells from the current localized website.')


if __name__ == '__main__':
    build()
