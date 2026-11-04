# Next steps

Written 2026-11-02. This is the to-do list after the prototype build. Tick items off here as they are done.

State of the site: 101 pages built (37 English, 32 Hindi, 32 Marathi), `make check` passes, the whole site is `noindex` until launch. Hindi and Marathi are drafts.

## 1. Needed from D-SAP

Each item unlocks pages that are built but held back until the fact is confirmed in `packages/site/facts.json`.

- [ ] **Results** (`results.verified`): verified JEE results with exam, year, course and duration. Check the four reporting rules on the results page. Unlocks the Results page and its navbar tab (sixth place, before Contact).
- [ ] **Kota partner** (`partner.name`, `partner.permission`, `partner.agreement`): the partner's name, written permission and the agreement. Unlocks Powered by Kota.
- [ ] **Faculty** (`faculty.profiles`): names, subjects, Kota experience and written consent. Unlocks the Faculty page and the faculty list.
- [ ] **Legal review** (`legal.policies-reviewed`): a lawyer's review of the privacy, terms and refund pages.
- [ ] **Foundation, Class 9 and 10**: the minimum-age rule wording (`legal.foundation-minimum-age`), and the details section. The foundation page itself is live.
- [ ] **Fee range** (`fees.range`): a price range, if you want it in the structured data. The scholarship offer is not a price range.
- [ ] **Security contact**: decide whether security reports go to a separate email address.
- [ ] **Photos and films** still awaited are listed in `docs/setup/media-to-add.md`.

## 2. Cloudflare and GitHub (you do these)

The workflow is `.github/workflows/deploy.yml`. Cloudflare builds nothing: GitHub builds the site and sends Cloudflare the finished files. Steps are in `docs/setup/security.md`, "Deploying and the headers".

- [ ] Create the Pages project `iitjeekota` (Upload assets).
- [ ] Create an API token with only Cloudflare Pages: Edit, and note the Account ID.
- [ ] In GitHub, Settings, Environments: create `preview` and `production`. Add yourself as required reviewer on `production`. Add the secrets `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` to both.
- [ ] Do the first real CI run on GitHub (`ci.yml`, `deploy.yml`, `zap.yml`) and fix what it finds. None of the workflows has run yet.
- [ ] Update `happy-dom` to 21.0.4 after 2026-11-03, then delete its entry in `osv-scanner.toml`.
- [ ] Commits and pushes are yours: nothing has been committed from this work.

## 3. Work for Claude Code

- [ ] Look at the Hindi and Marathi pages on screen, and the footer at phone width (it now groups areas under Pune and Pimpri-Chinchwad).
- [ ] Look at the home page after the section spacing was halved (`space.fluid.section` is now 32 to 80, so `--space-section` is `clamp(2rem, 1rem + 4.4444vw, 5rem)`).
- [ ] Align the other "works like the real JEE screen" sentences (test-series, class-12 and the Hinjewadi area page) with the new home page wording, if wanted.
- [ ] Add a security scanner for the browser code. Semgrep was removed because its pins were vulnerable. An ESLint security plugin is the candidate.
- [ ] Build the Faculty and Results lists as soon as their facts arrive.
- [ ] Run the e2e suite after any layout change: `make web`, then `pnpm exec playwright test --project=web` against `astro preview`.

## 4. Before launch

- [ ] Hindi and Marathi reviewed and rewritten by native writers. Drafts are marked in `docs/content/status.md`.
- [ ] Confirm the AI crawler policy in `packages/site/crawl.json` (it follows dsapghuletutorials.com), and whether `llms.txt` stays unbuilt. Google says it has no effect on Search.
- [ ] Replace placeholder photos with real ones. Student photos need the parents' written consent. Every image and video must be stripped of hidden data (`make media-fetch`, `make media-encode`).
- [x] `indexing` is on in `apps/web/src/config/site.json`; `crawl.json` `indexable` opens English and the Hindi and Marathi home pages. To open another Hindi or Marathi page after native review, add its route id there.
- [ ] Move the HSTS stage up in `packages/site/security.json` after the site has run clean for a while.
- [ ] Run `make docs-drift` to compare Google's structured data docs with `packages/site/jsonld-rules.json`. It is due quarterly and before any schema change. `make site` fails when the rules are over 90 days old.
- [ ] In Search Console: add the sitemaps, inspect a few URLs, and watch the structured data reports for the first weeks.

## 5. Upcoming phases: backend and integrations

From the plan (`~/.claude/plans/need-to-design-the-wiggly-puddle.md`, parts D4, D5, D7 and Phases 1, 8, 9, 10, 11). Nothing in `apps/api` exists yet. Today the enquiry form sends on WhatsApp (`transport` in `apps/web/src/config/features.json`).

### Phase 1. Legal research (before the API stores any personal data)
- [ ] Summarise, with links and dates: DPDP Act 2023 and Rules 2025 (notice, consent, parental consent under 18, retention, breach reporting, grievance), IT Act s.43A, CCPA coaching guidelines 2024, Ministry of Education coaching guidelines 2024, TRAI rules for calls, SMS and WhatsApp, and the Trade Marks Act for the partner's mark.
- [ ] Output: a compliance matrix, the required disclosures, a retention schedule, then draft privacy, terms, refund and grievance pages. A lawyer reviews them (this is `legal.policies-reviewed`).

### Phase 8. Backend (`apps/api`, FastAPI, hexagonal) and the lead desk

The full requirements, the options with prices, and the technical overview are in `docs/setup/crm.md`. Read it first. The summary:

**Two surfaces, one API**
- Public site (iitjeekota.com, static) posts enquiries to the API. It never receives lead data back.
- Lead desk at `admin.dsapghule.com`, a separate domain, behind Cloudflare Access, institute email sign-in and multi-factor authentication. Role-based access by centre. Telecallers see only masked numbers or hashes.

**Endpoints**
- Public: `POST /v1/leads` (idempotency key, captcha, consent), `POST /v1/callbacks`, `GET /v1/callbacks/{id}`, `POST /v1/consent/withdraw`, `GET /v1/health`.
- Provider webhooks (signed, replay-checked): call events and recording ready, and the per-call routing question for inbound calls.
- Desk (admin routes): leads (masked), lead update, assign, notes, tasks, `POST /admin/leads/{id}/call` (masked outbound), `POST /admin/leads/{id}/reveal-number` (super admin only, fresh authentication, reason, 30 seconds, owner alerted), call summaries and recordings (streamed), dashboards, flags, audit log, users and roles, data-rights export and delete.

**Flows**
- Outbound: the telecaller presses Call. The API checks role, centre, hours and limits, decrypts the number inside the server, and the provider rings the telecaller then the parent, showing the centre's number.
- Inbound: one public number. The provider asks the API who should get the call. The API finds the lead by a keyed hash of the caller number and rings the assigned executive if they spoke within the window, else the centre queue. The executive's screen shows the last call summaries while it rings.
- After every call: recording, transcript in Hindi, Marathi or English, summary, misuse checks, all attached to the lead.

**Data**
- Postgres in India with row-level security by centre. Phone numbers encrypted, plus a keyed hash for lookups. Recordings in encrypted storage in India, short-lived links only. Append-only audit log.

**Integrations behind adapters** (swap by setting): telephony provider (Exotel, MyOperator, Knowlarity or Ozonetel, chosen by pilot), speech to text (Sarvam or another, chosen by pilot on real Marathi calls), summary model, captcha (Turnstile), WhatsApp and email notices.

**Anti-theft** (see `crm.md` 4.7): no real number in any browser, no export or download for telecallers, watermarked screens, caps on lead cards opened, canary leads, transcript flags for asking a parent for another number, access-pattern alerts. These reduce the risk. They cannot stop a person photographing a screen.

**Release order**
- [ ] 1. Phase 1 legal review, then the provider pilot (including the mobile app model) and the decision record (`crm.md` section 11).
- [ ] 2. API, database, sign-in, RBAC by centre, audit log, website form to leads.
- [ ] 3. Lead desk screens: pipeline, tasks, routing rules, masked view.
- [ ] 4. Masked outbound calling, then single-number inbound with sticky routing.
- [ ] 5. Recording, speech, summary, screen pop.
- [ ] 6. Misuse detection and dashboards.
- [ ] 7. Security hardening, scans, device tests, then go live.

Estimate for a first release is 13 to 19 person-weeks (crm.md section 9). Running cost for 6 telecallers is roughly 15,000 to 35,000 a month before hosting and model costs, from unconfirmed prices. Replace with written quotes.

**Decided on 2026-11-02**
- The desk domain is `admin.dsapghule.com`, owned by D-SAP.
- Telecallers use their own mobile phones, signed in to the provider's app. A desk phone is possible if a provider needs one.
- No automated or recorded voice. A person always calls and receives. AI gives assistance and summaries only.
- A new dedicated number from the chosen provider. The current +91 22 6971 9828 is on Heyo, which has no call masking. When the new number is live, change the phone fact in `packages/site/facts.json`, both Google Business Profiles and listings in one release, and keep the old number forwarding for an agreed overlap (`crm.md` section 6.1).

- Telecallers sign in with Microsoft institute email (Entra ID). 2 to 3 telecallers per centre. The super admin reviews recordings and flags. The Heyo number stays in use. Telecallers use the provider's app on personal phones and see no numbers. The new number should be in the +91 22 or 20 series.
- The desk is an installable web app (no native app). The stack is bought telephony, speech and summary models behind adapters, and a built desk, RBAC, masking, routing decision and audit (`crm.md` 7.6 and 7.7).

**Decisions still open**
- Telephony provider, by pilot: Tata Smartflo, Exotel, MyOperator and Superfone first (`crm.md` sections 7.6 and 11). Tata and Superfone have public developer docs. Neither documents hiding the parent's number from the agent's phone, so the pilot tests it on Android and iPhone.
- City code for the new number (Pune 020 or Mumbai 022), if the provider offers a choice.
- Retention period for enquiries, recordings and transcripts. The acceptable monthly cost.
- Heyo number: forward to the new number, or keep as a separate line, and what the website shows.
- Cover for the super admin's review duty. Who signs the written device policy (no screenshots, no screen recording, app removed on leaving).
- Cloud Run or a VPS.

### Phase 9. QA and hardening
- [ ] Test on a low-end Android phone, an iPhone and a desktop, in all three languages.
- [ ] Accessibility audit (axe) and performance budgets (Lighthouse CI).
- [ ] ZAP baseline on every preview, dependency audits, an API security review.
- [ ] Swap test: change one token and one media slot and confirm the whole site follows.
- [ ] Final legal and facts sign-off.

### Phase 10. Launch
- [ ] Replace placeholders or keep their flags off, remove `noindex`, deploy.
- [ ] Submit sitemaps to Google Search Console and Bing. Check the rich results.
- [ ] Link the Google Business Profiles to the centre pages. Add links from dsapghuletutorials.com.

### Phase 11. Growth
- [ ] Publish more area and topic pages as their facts arrive. Publish guides on a schedule.
- [ ] Keep results and faculty current. Collect Google reviews. Build local listings.
- [ ] Monthly check of how AI answers describe D-SAP. Re-read Google's structured data changes each quarter.

## Rules to remember

- Dates change only when a person edits `dates.modified` in that page. A build or deployment never sets one. Tests enforce it.
- The Content Security Policy is never weakened. A new source (map tiles, analytics, payments, an embed) needs an ADR first. The Google Maps iframe on `/contact/` was left out for this reason: the page draws its own map and links to Google Maps.
- Read Google's live documentation before any SEO, structured data or GEO decision.
- Copy names facts and pages by id (`{{fact:id}}`, `[anchor](page:route-id)`). No em or en dashes. `make copy-lint` must pass.
- Every change ships with tests and passes `make check`.

## Where things live

- The engineering contract and the "change it in one place" table: `CLAUDE.md`.
- What is built and what waits: `docs/content/status.md`. Media still awaited: `docs/setup/media-to-add.md`.
- Decisions: `docs/adr/`. Security setup: `docs/setup/security.md`, `SECURITY.md`.
- Structured data rules and the last export's findings: `docs/seo/structured-data.md`, `docs/seo/structured-data-results.md`.
