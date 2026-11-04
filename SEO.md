# Search and agent discovery maintenance

The production origin is https://ducknap.games/. Keep canonical URLs on that origin unless the whole site is deliberately migrated.

- Each game has an HTML landing page under `/games/<slug>/`, linked from the homepage. Keep its availability and play destination accurate.
- Update visible game descriptions, `VideoGame` JSON-LD, `games.json`, and the corresponding `index.md` together. The validator checks description/name consistency between catalog and game schema.
- Add new canonical HTML pages to `sitemap.xml`. Do not include fragment URLs, query variants or the legacy `privacy.html` redirect.
- `robots.txt` permits crawling and advertises the sitemap. It is not access control.
- `llms.txt` indexes concise Markdown game information. This is an emerging discovery convention, not a ranking guarantee or authorization for an agent to act.
- Keep social image metadata synchronized with the actual 1200x630 image. Do not invent ratings, reviews, prices or platform availability for structured data.
- Preserve the public Google Search Console verification meta tag in the homepage. It is a verification token, not a private credential.
- The website has the same 16 languages as Whose Stuff: `en`, `ja`, `ko`, `de`, `zh-Hant`, `fr`, `es`, `pt-BR`, `it`, `ar`, `th`, `tr`, `id`, `pl`, `nl`, `vi`. English retains the existing root URLs; other languages use `/<locale>/` prefixes. Each of the ten pages has a complete static translation, its own canonical, reciprocal `hreflang` links and sitemap alternates. Arabic uses native right-to-left layout.
- Edit English source HTML in `i18n/templates/` and keep its stable source keys in `i18n/source.json` synchronized. Edit translations in `i18n/translations/<locale>.json`, then run `python scripts/build-locales.py`. Do not edit generated translated HTML directly. `--available-only` is for work-in-progress previews, never publication.
- Marketing copy is adapted for the studio context. Game and studio names, destinations and factual claims stay consistent. Policy translations include a link to their English original. The English hosting copy also describes both the custom domain and GitHub Pages mirror.
- Localized plain-text pages and game catalogs are generated alongside HTML for readers and agents; these do not guarantee search ranking or inclusion in AI answers.

Run before publishing:

```powershell
python scripts/check-site.py
python scripts/check-locales.py
node --check assets/studio.js
node --check assets/languages.js
git diff --check
```

Search Console ownership and sitemap submission are account-side operations. Passing the local checks does not prove Google has indexed a page or granted a rich result. Monitor indexing and search performance there after release.
