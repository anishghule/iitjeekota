# 0005. Page copy as JSON in packages/content

Date: 2026-10-31. Status: accepted.

## Context

Phase 4 writes the copy for every page in three languages before the Astro app exists (Phase 6). The copy has to be:

- checked now by `dsapkit`, which uses only the Python standard library
- read later by Astro content collections without conversion
- tied to the facts register, so a claim cannot go live before its fact is confirmed
- free of URLs and hard-coded facts, so that changing a slug or a phone number changes every page (CLAUDE.md, section 2)

## Decision

- Each page and locale has one file: `packages/content/pages/{locale}/{route-id}.json`. Astro's `glob()` loader reads JSON natively, and Python reads it with `json`.
- Copy shared by several pages (for example the short description of the Kota system on every area page) lives once in `packages/content/blocks/{locale}/{block-id}.json`. A section points to it with `"block": "id"`, and the similarity check leaves it out.
- `packages/content/templates.json` sets the sections each template has, in order:
  - each section's kind: prose, faq or list
  - how many paragraphs or questions it takes
  - the facts that must be confirmed before it shows
  - the component that draws its data (commute card, programme table)
  - per-route layouts where one template's pages differ (for example Powered by Kota among the pillars)
- Inside copy:
  - `{{fact:id}}` (or `{{fact:id#field}}`) inserts a confirmed fact.
  - `{{commute:area-id#km}}` inserts the distance from an area to its nearest centre, from `areas.json`, so an answer-first sentence never repeats a number by hand. Travel times are left to the commute card, which says whether a time is on empty roads or at batch time.
  - `[anchor](page:route-id)` links to a page by route id.
  - A paragraph can instead be `{"text": "...", "requires": ["fact.id"]}` when its claim depends on facts it does not quote.
  - `{{syllabus:main#year}}`, `{{syllabus:all#chapters}}` and similar read the syllabus documents and chapter counts from `syllabus.json`.
  - A paragraph that names a pending fact is held back and listed. A link to a page that is not live yet shows as plain text.
- Facts in other languages: a fact's `value` is English, and `localized` holds the same value in Hindi and Marathi. On a Hindi or Marathi page, a fact whose value has words in it is held back until that language's value exists, so copy never mixes English words into Devanagari. Numbers and phone numbers need no translation.
- `make content` checks the structure, meta lengths, primary keyword in the title or H1, references, and how similar pages of the same template are (word shingles). It writes `docs/content/status.md`. The copy linter covers voice and readability.
- `status` is `draft` until the copy is final. Hindi and Marathi stay `draft` until the language experts proofread them at release.

## Consequences

- Phase 6 points Astro content collections at `packages/content`. Components render sections by id, and the inline syntax is resolved once, in one helper per side (`dsapkit.content.text` now, a TypeScript port then), tested against the same fixtures.
- Blog posts are Markdown with JSON front matter (`posts/{locale}/{post-id}.md`), which is valid YAML, so Astro and Python both read it. The H1 is the post title in `packages/site/blog.json`, where each post is `planned` or `written`; `make content` checks the two agree, and checks the opening answer, length, links to the pages the post supports and its author. Legal pages will use the same format in Phase 1.
- The syllabus table's structure and English names are in `syllabus.json`. Each other language's chapter names are in `syllabus/{locale}.json`, checked to name every chapter.
- A page's language version publishes only when its route is live and its copy is `ready`. Phase 7 feeds this into hreflang and the sitemaps.
