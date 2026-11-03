# 0008. Structured data, dates and crawl files

Date: 2026-11-01. Status: accepted.

## Context

Only seven pages had hand-written JSON-LD. Area pages and the Hindi and Marathi pages had none, a fixture held a hard-coded future date, and opening hours were stored as `07:00` where Google asks for `hh:mm:ss`. These are the format mistakes Search Console reports weeks after launch. Google's rules also change. In 2026 FAQ markup was retired and a creator property was added to video. Google also said that `llms.txt` and other AI-only files have no effect on Search.

## Decision

1. **Rules come from Google's live pages, read on the day.** `packages/site/jsonld-rules.json` records, per type, the required and recommended properties and the format of each value, with the page's "Last updated" date. `make docs-drift` fetches those pages and fails when a date differs. `make site` fails when the rules were read more than 90 days ago. Google publishes no machine-readable rules, so a person re-reads a page that changed.
2. **One builder per type, in Python.** `site/jsonld_build.py` writes every page's JSON-LD from data. Astro prints the result. The checks in `site/jsonld.py` run in `make web-data` and stop it on any error. The plan sketched TypeScript builders; the web app only reads generated data and the validator lives beside the builders, so they are Python.
3. **Dates cannot be written wrong.** Content stores `YYYY-MM-DD` (or `YYYY-MM-DDTHH:MM`). `site/formats.py` is the only code that turns them into ISO 8601 timestamps. The offset and time of day come from `site.json` `dates`: `+05:30`, and 9 am when only the day is stored. A real time can be written as `YYYY-MM-DDTHH:MM`. Google recommends the offset and otherwise assumes Googlebot's timezone. Event dates are the exception: Google asks for a day, or a local time with no fake midnight. Times of day in facts are written `07:00` and rendered `07:00:00`.
   A date never changes by itself. It changes only when a person edits `dates.modified` in that page, so a page whose content did not change keeps its date through every deployment. Google ignores a `lastmod` that moves on each deploy, so no script, build or deployment sets one. Two tests guard this: a rebuild must produce byte-identical files, and every visible date, sitemap `lastmod` and `dateModified` must equal the page's own `dates.modified`. Cloudflare Pages sends an ETag that is a hash of the file and no Last-Modified, so an unchanged file looks unchanged to a crawler.
4. **Pending facts leave a property out.** Nothing is filled with a placeholder.
5. **Area pages are not local businesses.** An area page is a `WebPage` that points at its nearest centre through `about`. Only the two centres are `LocalBusiness`, each listing the areas it serves.
6. **One site name.** `Organization` and `WebSite` live on `/en/` (the root redirects there and Google reads the redirect target) and use the same name and alternate names. Other languages' home pages refer to them by `@id`.
7. **Sitemaps and `robots.txt` come from the pages actually built** (`make web-data`). A sitemap lists only built pages, with hreflang alternates that exist. `lastmod` is written only where a page says when it changed; `priority` and `changefreq` are never written. Before launch `robots.txt` disallows everything and every page is `noindex`.
8. **After launch `robots.txt` follows dsapghuletutorials.com** (read 2026-11-01): `Content-Signal: search=yes, ai-input=yes, ai-train=no`, `Disallow: /api/`, and the training crawlers blocked. Search and user-triggered agents are not listed, so they are allowed. The list is in `crawl.json`.

## Open

- **`llms.txt`:** Google's guide (updated 2026-07-10) says Google Search ignores these files and that they neither help nor harm. None is generated until the owner decides they are wanted for other services.
- **AI crawler policy:** plan B7 said to allow AI crawlers. Item 8 follows the sister site instead. Change `crawl.json` to change it.
- **`og:type` article and `article:published_time`** wait for blog posts to be rendered.

## Consequences

Every live page in every language gets a graph. A wrong date, time, URL, phone number, country code or breadcrumb stops the build instead of reaching Search Console. A reviewer reads `docs/seo/structured-data.md` (rules) and `docs/seo/structured-data-results.md` (what the last export found).
