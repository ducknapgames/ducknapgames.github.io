# Website languages

This folder holds the editable source for the studio website's 16 languages.

- `templates/`: English HTML originals, before adding the generated language picker.
- `source.json`: stable translation keys, English text and page/element context.
- `translations/`: full contextual translations, one JSON file for each non-English locale.

Brand and game names remain unchanged. Translate interface text, descriptions, accessible labels, metadata, support and policy text. Preserve factual details, destinations and placeholders such as `{name}`. Inline fragments must read naturally together in the original markup order. Do not invent availability, privacy guarantees, statistics or reviews.

To update a sentence, edit its English template and its existing source key, then update that key in every translation. Add a new key for new text; do not renumber existing keys. New English pages need a matching template and must be included in the source extraction and build page list. The extraction helper is for the initial catalog only and refuses to overwrite existing keys.

Generate and check:

```powershell
python scripts/build-locales.py
python scripts/check-site.py
python scripts/check-locales.py
node --check assets/studio.js
node --check assets/languages.js
```

Every translated page is static HTML. The language picker keeps the current page and fragment. Arabic pages use `dir=rtl`; artwork and the studio wordmark keep their original orientation. Language suggestions use browser language settings without redirecting visitors. Language selection does not add tracking, cookies or remote translation calls.

The build emits reciprocal HTML/sitemap alternates, localized canonical/OG URLs, descriptions, JSON-LD, Markdown and game catalogs. The existing English URLs stay unchanged.

Translation provenance: the first set was produced by three AI translation agents with the English text, element context, game facts and studio tone. These are context-adapted AI translations, not a claim of certified legal or native-speaker review. English policy originals remain linked from translated policy pages.

Context review, 4 November 2026: all 315 source entries and all 4,725 translated entries were checked against the templates and game context. The review corrected 147 entries across the 15 translation catalogs, including purchase unlocking, third-party deletion limits, controller terminology, linked-sentence grammar, gender-neutral quiz feedback, and natural game descriptions. Quiz character names were checked against the canonical game's locale catalogs. Facts, dates, placeholders, brands, and policy scope were preserved. This was an AI-assisted translation review, not native-speaker or legal certification.

The generated pages are published at ducknap.games. Review source and catalog changes locally, rebuild, and run the checks above before deployment.
