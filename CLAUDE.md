# iitjeekota.com: engineering contract

D-SAP Ghule Tutorials (powered by a named Kota institute) JEE coaching site for Pune and Pimpri-Chinchwad.
Plan: `~/.claude/plans/need-to-design-the-wiggly-puddle.md`. `resources/` is reference only. It is gitignored, never shipped, and nothing in the build reads it. Originals the build converts are clean copies in `packages/media/originals`, with no hidden data and each under 25 MB. Raw phone video is too large for git, so the committed film is the copy.

Every change, by a person or by Claude, follows this contract. CI enforces it wherever a rule can be checked.

## 1. Design before code, fix at the root

- No patch fixes. When something breaks, find the design flaw and fix it in the right layer. A third fix in the same area means that area gets redesigned.
- No ad-hoc string replacement of code or generated output, no fudge factors, no workaround env vars bolted on after a failure. If a behaviour depends on the environment, it is designed in, named and documented.
- Values live in data files, logic lives in code. A number that a designer might change is never a literal in code.
- Edit code as code (real edits, reviewed diffs), never through throwaway rewrite scripts.

## 2. Everything is swappable from one place

| To change | Edit only |
|---|---|
| Colours, fonts, type scale, spacing, shadows, motion, 3D materials | `packages/tokens/tokens.json` |
| Which font files are vendored, fallbacks, x-height matching | `packages/tokens/fonts.config.json` |
| Colour pairs that must pass WCAG | `packages/tokens/contrast.json` |
| Brand name, short name, domain, start URL | `packages/brand/identity.json` |
| Any image or video: logo source, photos, textures, centre films (with source, alt text, licence, spec) | one slot in `packages/media/manifest.json`; files D-SAP supplies use origin `awaited` and are listed in `docs/setup/media-to-add.md` |
| Logo sizes built from the official medal | `packages/brand/logo.json` |
| Favicons, app icons, web manifest | `packages/brand/favicons.json` |
| Open Graph layout and default text | `packages/brand/og/layout.json`, `og/copy.json` |
| Voice rules, banned words, rewrite examples | `packages/brand/voice.json` |
| Icons | one file in `packages/icons/svg/` plus its meaning in `packages/icons/icons.json` |
| Pages, slugs, pillars, breadcrumbs, keywords | `packages/site/routes.json`, `areas.json`, `centres.json`, `blog.json`; patterns and linking rules in `site.json` |
| Facts every claim and gated page depends on, and their Hindi and Marathi values | `packages/site/facts.json` (`value`, `localized`) |
| Structured data: which types and fields, and the format of each value | `packages/site/jsonld-rules.json`, read from Google's live docs (never from memory); builders in `tools/dsapkit/src/dsapkit/site/jsonld_build.py`; values come from `identity.json`, `centres.json`, `areas.json`, `facts.json` and the page's copy; page types in `site.json` `jsonld` |
| A page's or post's dates | `dates` (`published`, `modified`, as YYYY-MM-DD) in the page file or post front matter; timezone and time of day in `site.json` `dates`. Timestamps are only ever made by `site/formats.py`. A date changes only when a person edits `modified` in that page: nothing in a build or deployment sets one (tests enforce it) |
| robots.txt, which crawlers are blocked, which pages of each language may be indexed (`indexable`), sitemaps | `packages/site/crawl.json`; `indexing` (the launch switch) in `apps/web/src/config/site.json` |
| Content Security Policy, response headers, HSTS stages, security.txt, noindex hosts | `packages/site/security.json` (written to `_headers` by `make web-data`; ADR 0009); the policy is tested by `apps/web/e2e/security.spec.ts` |
| Dependency update rules, CI scans, secret and vulnerability scanner settings | `renovate.json`, `.github/workflows/`, `tools/ci/requirements.in`, `osv-scanner.toml`, `.gitleaks.toml`, `[tool.ruff]` and `[tool.bandit]` in `tools/dsapkit/pyproject.toml` |
| Listings, aggregators, ranked lists, press, community | `packages/site/citations.json` |
| Search volumes from Keyword Planner | `packages/site/keyword-volumes.json` |
| Commutes from each area to the centres (placeholder or confirmed, with source) | `commute` in `packages/site/areas.json`; sources in `site.json` `commuteSources` |
| Page copy, per page and language | `packages/content/pages/{locale}/{route-id}.json`; copy shared by several pages in `blocks/{locale}/`; sections per template in `templates.json` (ADR 0005) |
| Guides (blog posts) | `packages/content/posts/{locale}/{post-id}.md`; title, keyword and status in `packages/site/blog.json` |
| The JEE syllabus table | `packages/content/syllabus.json` (chapters, official units, English names); other languages' names in `syllabus/{locale}.json`; design in `docs/design/syllabus-table.md` |
| 3D scenes: sizes, detail per tier, keyframes, studio light, stills, budgets | `packages/scenes/scenes.json` (materials and colours stay in `packages/tokens`); storyboard in `docs/design/scenes.md` |
| Autoscroll timing | `motion.autoscroll` in `packages/tokens/tokens.json` |
| Area map: rivers, road classes, place queries, simplification, line and label sizes, commute check limits | `packages/map/map.json`; the pinned OpenStreetMap data in `packages/map/source` |
| Data for interactive sections (sample test, example report, timeline, programmes table, portal window, the AI digital board's words) | `packages/content/widgets/{locale}/{name}.json`; which section uses which in `templates.json` (`widget`) |
| The AI digital board demonstrations: timings, board size, text sizes | `apps/web/src/config/board.json` (the maths is drawn by `apps/web/src/islands/board.ts`) |
| A section that waits for a file D-SAP supplies | `gates` in `templates.json` with `media:{slot id}` |
| Site header: tint, blur, fade, height, where links fold into the menu; short link text | `nav` in `packages/tokens/tokens.json`; `navNames` in `packages/site/routes.json`; design in `docs/design/navigation.md` |
| Breakpoints | `breakpoint` in `packages/tokens/tokens.json` (CSS gets generated `.from-*` and `.below-*` classes) |
| UI strings of the site | `apps/web/src/i18n/{en,hi,mr}.json` (English defines the keys) |
| Feature flags, site settings (indexing before launch) | `apps/web/src/config/features.json`, `site.json` |
| CRM provider | API setting `CRM_PROVIDER` (Phase 8) |

Hard rules:
- No raw hex colours, font families, px font sizes, durations or easings outside `packages/tokens`.
- Components use surface roles (`--text`, `--accent`, `--action-bg`), never palette primitives (`--color-brass-300`).
- No user-visible strings in components: copy comes from content or i18n files.
- No image paths in components: ask for a media slot by its typed id.
- No URL strings in components: use the route registry.
- Every generated file starts with a "generated, do not edit" header and is rebuilt, never hand-edited.

## 3. Structure and layers

```
packages/tokens   design tokens, fonts, contrast rules           (data + generated dist/)
packages/icons    icon sources and rules                          (data + generated dist/)
packages/brand    identity, logo sizes, favicons, OG layout, voice (data + generated dist/)
packages/media    media library: slots, supplied files, media.lock.json (data)
packages/site     routes, keywords, facts register, structured data fixtures, citations (data + generated dist/)
packages/content  page copy per language, shared blocks, section templates, syllabus (data)
packages/map      area map config and pinned OpenStreetMap data (data + generated dist/)
packages/motion   @dsap/motion: autoscroll, section progress, motion preferences (TypeScript)
packages/scenes   @dsap/scenes: procedural three.js scenes, scene host, quality tiers (TypeScript + scenes.json)
tools/dsapkit     all build tooling as one Python package, one CLI (logic)
docs/             brand guide (generated), ADRs, legal research
apps/web          Astro site, rendered from data make web-data exports (ADR 0007)
apps/api          FastAPI service, hexagonal (Phase 6 and 8)
```

Layer rules:
- `tools/dsapkit`: `tokens` and `fonts` know nothing about `brand`, `icons`, `media` or `guide`. `brand` may use `tokens`, `fonts`, `images` and `media`. `guide` may read everything. No module reaches into another module's private helpers. Shared objects are built once per run in `context.py`.
- Browser packages: `@dsap/motion` depends on `@dsap/tokens` only; `@dsap/scenes` on `@dsap/tokens`, `@dsap/motion` and three. Scenes never import content: the page passes it in (Kota points, syllabus chapters, media URLs). Every scene is a pure builder (testable in Node); only `host.ts` touches WebGL and the DOM.
- `apps/web`: pages, then layouts, then sections, then blocks, then ui primitives. Sections take data as props. Islands never import content: they read what the section rendered (data attributes, `application/json` blocks). Nothing imports from pages. Astro reads only `src/generated` (from `make web-data`), never `packages/*` copy or facts, so the site shows exactly what `make content` approves. Logic lives in `.ts` modules (type checked); `.astro` files stay thin.
- `apps/api` (planned): routers call services only; domain imports nothing from api or adapters; adapters implement ports.

Patterns in use: registry (routes, media slots, icons, scenes), builder (JSON-LD, SVG documents), strategy (CRM providers, 3D quality tiers). Also data-driven layout (OG images) and lock files for anything downloaded (fonts, media, map data, pnpm-lock.yaml). Ports and adapters (scene textures, autoscroll scrolling) let logic be tested without a browser.

## 4. Code quality

- Python: type hints everywhere, stdlib unless an ADR approves a dependency, `BuildError` for user-facing failures (no bare `SystemExit` inside library code), tests next to each module's behaviour in `tools/dsapkit/tests`.
- TypeScript (Phase 6): `strict`, no `any`, typed ids for routes, media, icons, tokens.
- Small modules with one job. Names say what a thing is. Comments explain why, not what.
- Every change ships with tests and passes `make check`.

## 5. Security

- Dependencies: justify in the PR, pin exactly, at least 14 days old, clean `osv-scanner`. No CDNs, no third-party embeds, no inline scripts. pnpm enforces the age (`minimumReleaseAge`) and blocks install scripts (`pnpm-workspace.yaml`); Node.js is pinned in `package.json` and supplied by pnpm (docs/adr/0006-browser-toolchain-and-3d.md).
- Shell: never `rm` built from variables or globs. Let tools overwrite their output, or write to a new folder.
- Downloads in tooling go through `dsapkit.net`: HTTPS only, a host allowlist per caller, a size cap, a file signature check and a SHA-256 lock.
- Images and videos carry hidden data (where, when and by which phone they were taken). Nothing ships with it: images are rewritten without it by `make media-fetch` (`images/scrub.py`), videos are made clean by `make media-encode`, generated images pass through the same scrub, and `make web-lint` reads the files in `apps/web/dist` as shipped. Photos of students need the parents' written consent; `resources/` originals are never shipped. Videos are served from this site only, never embedded from another service.
- Secrets never in the repo. Previews are `noindex`; the whole site stays `noindex` until launch (`apps/web/src/config/site.json`).
- The site ships no inline scripts, styles or event handlers, and loads nothing from another site. The Content Security Policy in `packages/site/security.json` is `default-src 'none'` with `'self'` only; it is never weakened (`make site` refuses `unsafe-*`, wildcards, `data:` and framing), and a browser test runs real pages under it. Data-sized graphics use SVG attributes, islands set custom properties through CSSOM only. Any new feature that needs a new source (a payment page, a map tile server, an analytics script) needs an ADR first.
- CI runs ruff, bandit, gitleaks, OSV-Scanner and `pnpm audit`, and Renovate waits 14 days: `docs/setup/security.md`. A finding is fixed by upgrading or changing the code. An exception goes in `osv-scanner.toml` with a reason and an expiry date.

## 6. Copy

- No em dashes or en dashes as punctuation. No words from the banned list in `packages/brand/voice.json`. Plain Indian English, short sentences, numbers over adjectives.
- Copy names facts and pages by id, never by value or URL: `{{fact:id}}`, `{{fact:id#field}}`, `[anchor](page:route-id)`. A paragraph whose claim depends on facts it does not quote lists them in `requires`.
- Before any SEO, GEO or structured data decision (a type, a property, a value's format), read Google's current documentation first; the rules file records what it said and when.
- Every factual claim needs a facts register entry. "Best", "No. 1", guarantees and results need proof and legal review (CCPA coaching guidelines 2024). <!-- copy-lint-allow: best, no. 1 -->
- Assets: before drawing, generating or substituting any logo, photo or illustration, check `packages/media`, `resources/` and dsapghuletutorials.com, and ask the user to confirm the source. Internet placeholders are allowed only for photo slots, with a licence that allows commercial use.
- Hindi and Marathi are written by native writers. Drafts are marked as drafts.
- `make copy-lint` must pass.

## 7. Commands

```
make fonts        download and lock vendored fonts (network)
make metrics      measure fonts and compute fallback metrics (macOS, network)
make media-encode turn supplied videos and large photos into the files the site serves: no sound, no metadata (needs ffmpeg; settings in packages/media/encode.json)
make media-fetch  fetch supplied media from their recorded sources, strip every image of hidden data (EXIF, GPS, XMP, thumbnails) and lock them
make brand        tokens, icons, logo, favicons, OG images, media check, brand guide
make site         routes, keywords, links checks; fails if the structured data rules are over 90 days old; writes docs/seo reports
make docs-drift   compare Google's docs with the structured data rules (network; quarterly and before any schema change)
make security     ruff and bandit on the tooling, pnpm audit on what the site ships (install tools/ci/requirements.txt first; CI runs more)
make content      page copy against templates, facts and pages; writes docs/content/status.md
make map-fetch    download and pin the area map's OpenStreetMap data (network)
make map          build the area map from the pinned data
make js-install   install the browser packages exactly as locked
make js-test      type check and unit tests for packages/motion, packages/scenes and apps/web
make web-data     resolve copy, facts, routes, syllabus, map and media into apps/web/src/generated
make web          build the site into apps/web/dist, then web-lint
make web-dev      run the site at http://localhost:5179 while editing
make web-lint     contract rules on apps/web source; no inline scripts or styles in the build
make e2e          browser checks: scenes on both tiers, autoscroll, the home page (Playwright)
make stills       render each scene's still image for the still tier
make preview      serve the scene preview at http://localhost:5178
make test         unit tests (Python)
make copy-lint    voice rules over docs and content
make check        test + js-test + fonts-verify + media + site + map + content + copy-lint + web
```

Rendering PNGs needs `rsvg-convert` and fontconfig (`brew install librsvg`, or `apt-get install librsvg2-bin fontconfig`).
