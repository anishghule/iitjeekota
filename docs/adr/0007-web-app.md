# ADR 0007: The web app renders data that dsapkit exports

Date: 2026-10-31. Status: accepted. Phase 6 and 7.

## Context

The copy, facts, routes, syllabus, media slots and map are data in `packages/*`. dsapkit already
resolves them for its checks: it fills `{{fact:id}}`, holds back a paragraph whose fact is
pending, hides a section whose gate is not met and turns `[anchor](page:id)` into a link only when
that page is live. The site must show exactly what those checks approve. Two implementations of
the same rules (Python for checks, TypeScript for pages) would drift apart.

## Decision

1. **One resolver.** `make web-data` (dsapkit `web` module) writes everything the site renders
   into `apps/web/src/generated/`, already resolved:
   - `data/site.json`: locales, routes with paths and live state, brand names, contact links,
     centres, areas with their confirmed commutes, and every confirmed fact per language.
   - `data/pages/{locale}/{route}.json`: each live page with facts filled, held paragraphs and
     gated sections left out, links as `{text, path}` parts, breadcrumbs, alternates and the
     structured data from `packages/site/jsonld`.
   - `data/widgets/{locale}/{name}.json`: data for the interactive sections (live test, sample
     report, two-year timeline, programmes, portal), resolved by the same rules. Source:
     `packages/content/widgets/`.
   - `data/syllabus/{locale}.json`, `data/area-map.json` and `data/media.json`.
   - `public/`: fonts, favicons, the icon sprite and the media files, named by content hash.
   Astro never reads `packages/*` copy or facts itself.
2. **Sections can wait for media.** A section gate is a fact id or `media:{slot}`. A section
   whose slot is still `awaited` (a file D-SAP has not added yet) is hidden, like a section
   waiting for a fact. The home classroom film uses this.
3. **Astro 7.4, static output, no UI framework.** Layers: pages, layouts, sections, blocks, ui.
   Interactive parts are small TypeScript islands in `apps/web/src/islands/`. They read their data
   from the DOM (data attributes and `application/json` blocks the section renders) and never
   import content.
4. **No inline scripts or styles in the output.** `build.inlineStylesheets: "never"` and
   `vite.build.assetsInlineLimit: 0`, so the Content Security Policy can be `script-src 'self'`.
   A build check fails on any executable inline script.
5. **Values stay in tokens.** Components use surface roles and token variables only. `make
   web-lint` rejects raw colours, font families, px font sizes, raw durations and easings,
   palette primitives and URL strings in `apps/web/src`.
6. **UI strings** live in `apps/web/src/i18n/{en,hi,mr}.json`; English defines the keys and the
   type check fails when another language misses one. Hindi and Marathi strings are drafts until
   native review. **Feature flags and site settings** live in `apps/web/src/config/`.
7. **Indexing is off until launch.** `config/site.json` sets `indexing: false`, so every page
   carries `noindex`. Phase 10 turns it on.
8. **The enquiry form sends on WhatsApp until the API exists.** The form composes a message to
   D-SAP's WhatsApp number from the four fields; nothing is stored by the site. Phase 8 adds the
   API as a second transport behind the same form (`config/features.json` `enquiryTransport`).

## Consequences

- A change to copy, a fact or a route needs `make web-data` before `astro build`. `make web`
  runs both.
- `.astro` files are not type checked (the Astro checker does not support TypeScript 7 yet), so
  logic lives in `.ts` modules that `tsc` checks, and components stay thin.
- Pages other than home render through one generic template (intro, prose, lists, questions,
  enquiry) until their own sections are built.
