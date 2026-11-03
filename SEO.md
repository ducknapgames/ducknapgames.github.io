# Search and agent discovery maintenance

The production origin is https://ducknapgames.github.io/. Keep canonical URLs on that origin unless the whole site is deliberately migrated.

- Each game has an HTML landing page under `/games/<slug>/`, linked from the homepage. Keep its availability and play destination accurate.
- Update visible game descriptions, `VideoGame` JSON-LD, `games.json`, and the corresponding `index.md` together. The validator checks description/name consistency between catalog and game schema.
- Add new canonical HTML pages to `sitemap.xml`. Do not include fragment URLs, query variants or the legacy `privacy.html` redirect.
- `robots.txt` permits crawling and advertises the sitemap. It is not access control.
- `llms.txt` indexes concise Markdown game information. This is an emerging discovery convention, not a ranking guarantee or authorization for an agent to act.
- Keep social image metadata synchronized with the actual 1200x630 image. Do not invent ratings, reviews, prices or platform availability for structured data.
- Preserve the public Google Search Console verification meta tag in the homepage. It is a verification token, not a private credential.
- There are no localized website pages yet, so no `hreflang` alternates are declared. A game's language count does not make this English website multilingual.

Run before publishing:

```powershell
python scripts/check-site.py
node --check assets/studio.js
git diff --check
```

Search Console ownership and sitemap submission are account-side operations. Passing the local checks does not prove Google has indexed a page or granted a rich result. Monitor indexing and search performance there after release.
