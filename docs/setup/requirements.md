# What is needed, and when

Commits, merges and pull requests are done by D-SAP with `gh`. Claude prepares the changes and runs `make check`.

## Before Phase 4 (content)

- [x] **Batch timings**: full evening session, 3:00 PM to 7:00 PM, same as dsapghuletutorials.com (2026-10-31). Fact `batch.timings`.
- [x] **Commutes**: confirmed by D-SAP on 2026-10-31, with Baner, Pashan and Pimple Nilakh moved to the Wakad centre. Most times are on empty roads and the pages say so. A time at 3 PM can be added later as `minutes` in `packages/site/areas.json`. The values and sources are listed under Commutes in `docs/seo/site-map.md`.
- [x] **Hindi and Marathi**: language experts proofread at release. Drafts stay marked draft until then. All 35 pages are drafted in each, with the shared blocks, the syllabus chapter names (`packages/content/syllabus/{hi,mr}.json`) and the Hindi and Marathi values of the facts the copy quotes (`localized` in `facts.json`). The guides are English only for now: a Hindi or Marathi guide needs its own title and search query in `packages/site/blog.json` first.
- [x] **Photos and videos**: D-SAP adds them at the paths in `docs/setup/media-to-add.md`, then runs `make media-fetch`.
- [ ] **Keyword Planner downloads** in `resources/keyword-planner/`: `volumes-en.csv`, `volumes-hi.csv`, `volumes-mr.csv`, `ideas-en.csv`. 8 pasted rows are recorded in `packages/site/keyword-volumes.json`; the downloads replace them. Steps: `docs/setup/keyword-planner.md`.
- [x] **Phone number**: +91 22 6971 9828 for now. D-SAP changes `contact.phone` once the calling provider is set up (Superfone after KYC, or Exotel or another).
- [x] **Mock pattern, method and batch size** (2026-10-31): 75 questions, all compulsory; a practice sheet every week; a doubts forum and doubt sessions; AI-powered digital boards; lectures online; tests on an online portal that works like the real JEE; batches of 30.

Copy can be written before the facts below arrive; anything that depends on them stays marked pending and gated.

## Facts the copy is waiting on

The copy that depends on these is written and held back until they are confirmed in `packages/site/facts.json`. The list per page is in `docs/content/status.md`.

- [ ] **Reports after tests** (`method.parent-reports`): do parents get one after each test, and how (WhatsApp, app)? Until then the copy uses what dsapghuletutorials.com states: personal test analysis on the portal, and parent-teacher meetings.
- [ ] **Regrouping** (`method.regrouping`): are batches regrouped as students progress, as the v3.2 build said? Dropped from the copy unless confirmed.
- [ ] **Foundation programme** (`programme.foundation-details`): subjects, timings and how it fits around school. Its page is written and shows this section once the fact is in.
- [ ] **Affiliation letter** (`partner.show-agreement`): can parents see the affiliation letter at a centre? The Powered by Kota page offers it only once confirmed.
- [ ] **Syllabus "how we teach it"** (optional): one line per chapter from the faculty, added to `packages/content/syllabus.json`. The table shows it only where it exists.
- [ ] **dsapghuletutorials.com** still says 90 questions per mock and 25 students per batch. Worth correcting there, so both sites say the same thing.

## Facts (Phase 0, at the end, but sooner is better)

From `packages/site/facts.json`: email, opening hours of both centres, the Wakad map link and pin, fees and fee range, batch dates, the Kota partner's name, written permission and what the affiliation covers, faculty profiles with consent, verified results.

## Phase 5 (3D, motion, map): done

- [x] Node.js 24 LTS and pnpm installed with Homebrew (2026-10-31). The project pins its own Node.js version, which pnpm downloads. Playwright's Chromium is in its own cache, for the browser checks.
- [x] Blender is not needed: the 3D is built in code with three.js (docs/adr/0006-browser-toolchain-and-3d.md).
- [x] **Wakad map pin** (`centre.wakad.geo`): plus code JQ55+3HC, from D-SAP on 2026-10-31.
- [x] **Commutes to Wakad.** On D-SAP's instruction (2026-10-31), every distance to Wakad now comes from the road route to the real pin, and each area points to the nearer centre by road. Baner, Pashan, Pimple Nilakh and Pimple Saudagar moved to the Head Office; their pages, the route facts and both centre pages were rewritten to match. `make map` checks that this stays true.

## Before Phase 6 (engineering setup)

- [ ] OK to install `uv` with Homebrew (Python packaging for the API). The GitHub CLI is already installed.
- [ ] Cloudflare account, Pro plan and domain active: `docs/setup/cloudflare.md`, steps 1 to 12.
- [ ] Server bought: `docs/setup/hosting.md`.

## Before Phase 8 (enquiries, CRM, calls)

- [ ] The calling provider chosen (Superfone after KYC, Exotel or another), with API access, the API key and webhook secret in `.env.local`, and their API documentation. The API talks to it through one adapter, so the choice can wait.
- [ ] Turnstile keys in `.env.local` (Cloudflare guide, step 11).
- [ ] WhatsApp Business number, if enquiries should also go to WhatsApp.

## Before Phase 10 (launch)

- [ ] Both Google Business Profiles cleaned up: `docs/seo/google-business-profiles.md`.
- [ ] Search Console and Bing Webmaster Tools verified through a DNS record (Claude gives the record at the time).
- [ ] Phase 0 facts confirmed and Phase 1 legal review signed off.
