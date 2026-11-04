"""Build a redirect-only GitHub Pages tree without changing Dokploy's source.

The output must be a new directory. Publish it on the pages-redirect branch.
GitHub Pages cannot set application HTTP status headers: HTML routes use an
immediate meta refresh plus a query/fragment-preserving JavaScript redirect.
"""
import argparse
from html import escape
import json
from pathlib import Path, PurePosixPath
import re
import shutil
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://ducknap.games"
NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def document(target, verification=""):
    safe = escape(target, quote=True)
    script = json.dumps(target)
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Duck Nap Games has moved</title>
  {verification}
  <link rel="canonical" href="{safe}">
  <meta http-equiv="refresh" content="0;url={safe}">
  <script>location.replace({script} + location.search + location.hash);</script>
</head>
<body><p>Duck Nap Games has moved to <a href="{safe}">{safe}</a>.</p></body>
</html>
'''


def build(source, output):
    if output.exists():
        raise ValueError("Output must be a new directory; existing files are never removed")
    routes = {}
    for loc in ET.parse(source / "sitemap.xml").findall("s:url/s:loc", NS):
        url = loc.text or ""
        parsed = urlsplit(url)
        if (parsed.scheme, parsed.netloc) != ("https", "ducknap.games") or parsed.query or parsed.fragment:
            raise ValueError("Sitemap URL is not a canonical studio route")
        path = PurePosixPath(parsed.path.lstrip("/"))
        if ".." in path.parts or not parsed.path.startswith("/"):
            raise ValueError("Invalid route")
        relative = path / "index.html" if parsed.path.endswith("/") else path
        if relative.suffix != ".html" or not (source / relative).is_file():
            raise ValueError("Sitemap route has no source HTML: " + parsed.path)
        routes[str(relative)] = url
    if routes.get("index.html") != ORIGIN + "/":
        raise ValueError("Sitemap must include the canonical homepage")
    # The historical flat privacy URL is still linked externally.
    legacy = source / "privacy.html"
    if legacy.is_file():
        match = re.search(r'<link\s+rel="canonical"\s+href="([^"]+)"', legacy.read_text(encoding="utf-8"))
        if not match or not match[1].startswith(ORIGIN + "/"):
            raise ValueError("Legacy privacy page has no canonical destination")
        routes["privacy.html"] = match[1]
    home = (source / "index.html").read_text(encoding="utf-8")
    verification = re.search(r'<meta\b[^>]*name="google-site-verification"[^>]*>', home)
    output.mkdir(parents=True)
    for relative, target in routes.items():
        destination = output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(document(target, verification[0] if relative == "index.html" and verification else ""), encoding="utf-8")
    # Unknown historical paths retain their path; never accept a supplied host.
    (output / "404.html").write_text('''<!doctype html><html lang="en"><head>
<meta charset="utf-8"><title>Duck Nap Games has moved</title>
<script>location.replace("https://ducknap.games" + location.pathname + location.search + location.hash);</script>
</head><body><a href="https://ducknap.games/">Visit Duck Nap Games</a></body></html>
''', encoding="utf-8")
    # Keep crawling enabled so Google can discover the redirects.
    (output / "robots.txt").write_text("User-agent: *\nAllow: /\nSitemap: https://ducknap.games/sitemap.xml\n", encoding="utf-8")
    (output / ".nojekyll").write_text("", encoding="utf-8")
    # Old developer-site links may still be used for app-ads.txt discovery.
    shutil.copy2(source / "app-ads.txt", output / "app-ads.txt")
    return routes


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    routes = build(ROOT, args.output.resolve())
    print(f"Built {len(routes)} HTML redirects, a 404 fallback and ad/crawler support files.")
