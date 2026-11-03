# iitjeekota.com

IIT JEE coaching in Pune and Pimpri-Chinchwad by D-SAP Ghule Tutorials, powered by Kota.

Read `CLAUDE.md` first: it is the engineering contract every change follows.

## Layout

```
packages/tokens   design tokens, vendored fonts, contrast rules
packages/icons    icon sources (one SVG each) and their rules
packages/brand    identity, logo sizes, favicons, Open Graph layout, voice rules
packages/media    the media library: supplied and awaited images and videos, their sources and hashes
packages/site     pages, keywords, areas, centres, the facts register, structured data
packages/content  page copy per language, shared blocks, section templates, the JEE syllabus
packages/map      the area map: configuration and pinned OpenStreetMap data
packages/motion   autoscroll and scroll progress for pinned sections (TypeScript)
packages/scenes   the 3D scenes, built in code with three.js (TypeScript)
tools/dsapkit     all build tooling, one Python package with one CLI (stdlib only)
apps/web          the site: Astro, rendered from the data make web-data resolves
docs              brand guide (generated), voice guide, architecture decisions
resources         reference material only, never shipped
```

## Build

```
make help         every target
make js-install   the browser packages, exactly as locked (needs pnpm: brew install pnpm)
make brand        tokens, icons, logo, favicons, OG images, media check, brand guide
make preview      the 3D scenes and autoscroll at http://localhost:5178
make web-dev      the site at http://localhost:5179 (make web builds it into apps/web/dist)
make check        Python and TypeScript tests, font and media verification, site, map and content checks, copy lint, the site build
make e2e          browser checks (first: pnpm exec playwright install chromium)
```

PNG rendering needs `rsvg-convert` and fontconfig: `brew install librsvg` on macOS, or `apt-get install librsvg2-bin fontconfig` on Linux.

Open `docs/brand/guide/index.html` after `make brand` to see the brand system.

## Status

Phases 2 (brand system), 3 (pages and search), 4 (content: `docs/content/status.md`) and 5 (3D, motion and the area map: `docs/design/scenes.md`) are built. Phase 6 and 7 are under way: the site renders every live page in three languages, with the full home page (`docs/adr/0007-web-app.md`); the API waits for Phase 8. Then Phase 9, then Phases 0 and 1 (facts, permissions and legal research), then launch. What D-SAP needs to supply, and when: `docs/setup/requirements.md`. Photos and videos to add: `docs/setup/media-to-add.md`.
