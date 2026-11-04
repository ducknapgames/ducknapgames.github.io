# Private website statistics

The public nginx server sends a small message over loopback UDP to an in-container
Python/SQLite collector. nginx reduces the request to a document path and a broad
source category **before** sending it. No extra browser request or script is used.

Only successful GET requests for the 160 known document routes are counted.
Assets, 404s, known bots, empty user agents and DNT / Global Privacy Control
requests are excluded. All arbitrary query parameters, full referrers, IP
addresses and raw user agents are absent from the statistics stream and database.
Only recognised `utm_source` values (e.g. `instagram`, `youtube`, `tiktok`) can
override a source category; campaign names and arbitrary values are not stored.

The database holds daily `(day, page, source, count)` counters for 90 days, plus
the collection start date. Counts are page views, **not** unique people or
sessions. Reloads count again; crawlers can be missed; referrers can be hidden;
UDP collection is best effort. GitHub Pages traffic is not included. There is no
historical backfill and no cross-game, cross-site or advertising-profile join.

## Dokploy

Keep one replica on the existing Dokploy server. Mount named volume
`ducknap-website-statistics` at `/var/lib/ducknap-statistics` so deploys preserve
counters. No public host ports are published. The HTTP dashboard listens on
container port 8081; public website port 80 cannot serve it or its database.

Route **only** `https://dokploy.ducknap.games/website-statistics/` to
`http://duck-nap-games-website-studio-website-zpkq4c:8081` using a file-provider
router with priority 11000. Both HTTP and HTTPS routes must use the existing
`ducknap-private-admin` IP allowlist (`100.64.0.0/10`) and `ducknap-noindex`
middlewares. HTTP also uses `redirect-to-https`. The existing Dokploy routes use
priority 10000. Use a `PathPrefix` rule for `/website-statistics/` so the dashboard's own
static assets also use the private route. Do not add an unprotected
fallback domain/route to port 8081. Private access is through Tailscale, as for
Dokploy itself; it does not add a separate login or change control-panel access.

The dashboard includes daily counts, source groups, pages and a CSV export. It
sets no-store, noindex and a restrictive CSP, and loads no third-party assets.

## Shared website interface

The logo, Fredoka/Nunito wordmark, colour tokens, system-default theme switch,
preferences panel, language dialog, mobile menu, floating header and footer come
from the actual localized studio pages. `scripts/build-statistics-shell.py`
extracts those components after the public locale build; it does not copy
private counters into static files. Dashboard labels have contextual catalogs
in `translations/` for the same 16 languages. The reporting period survives a
language change, Arabic uses RTL, and dates/counts are formatted in the browser.

Shared assets are served from the existing public asset directory through the
private `/website-statistics/assets/` route. Only asset types are allowed, and
path traversal is rejected. The browser makes no third-party asset requests.
Language uses a query parameter; appearance is a local browser preference with
the same `ducknap-theme` key as the studio site. Collection and retention are
unchanged by interface preferences.

## Verification and operations

Run `python scripts/test-statistics.py`. Build the Dockerfile and run `nginx -t`.
Integration-test a real document request, repeat views, a known `utm_source`, an
unknown query containing a sentinel, assets, 404, bots, DNT, GPC, and CSV counts.
Inspect the database schema/content to confirm that the sentinel and request
identifiers are absent. Verify the private route from Tailscale and a public
403; the public website must remain accessible.

The public site does not depend on successful statistics ingestion. A stopped
collector is retried after 5 seconds; missed packets are not replayed. The public
health check still checks nginx independently. Statistics failures are logged
without request data. Back up the named volume using your existing private
server backup process; no backup destination is configured by this code.

Rollback: deploy the previous website image. Leave the volume intact to preserve
aggregate history; remove the two statistics-only routers and their service from
the private ingress file if removing the feature permanently. Existing private
middlewares, other routers, DNS and credentials must remain unchanged.
