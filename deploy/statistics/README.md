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
priority 10000, so only this exact path is overridden. Do not add an unprotected
fallback domain/route to port 8081. Private access is through Tailscale, as for
Dokploy itself; it does not add a separate login or change control-panel access.

The dashboard includes daily counts, source groups, pages and a CSV export. It
sets no-store, noindex and a restrictive CSP, and loads no third-party assets.

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
