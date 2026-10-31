# Keyword research (Phase 3)

Researched 2026-10-30. The keyword for each page lives in `packages/site/routes.json` (fixed pages) and in the patterns in `packages/site/site.json` (area and centre pages). `make site` checks that no two pages target the same primary keyword and writes the full table to `docs/seo/site-map.md`.

## Method

1. Start from what a parent or student in west Pune and Pimpri-Chinchwad types. A search names the service (IIT JEE coaching, JEE classes) and often a place (city, area, "near me"). It may also name a class (11, 12, foundation) or an exam (JEE Main, JEE Advanced).
2. Look at who ranks for those searches today and how their pages are titled (findings below, sources in `packages/site/citations.json`).
3. Give each search intent to exactly one page. Where two pages could chase the same search, split them by intent. An area page answers "coaching for students who live in Wakad". A centre page answers "where is D-SAP in Wakad".
4. Search volumes are not available without Google Keyword Planner. Before launch, pull volumes for every primary and secondary keyword there; after launch, use Search Console queries to adjust. The map is built so a keyword change is one line in the data.

## Decisions

- **Head term.** "IIT JEE coaching in Pune" goes to the Pune pillar (`/en/iit-jee-coaching-pune/`). The home page targets "Kota coaching in Pune" and the brand name, because the Kota partnership is what sets D-SAP apart from local institutes. Decided with D-SAP on 2026-10-30.
- **Centres and areas.** Wakad and Sangvi keep both an area page and a centre page (D-SAP's decision). The area page targets "IIT JEE coaching in Wakad"; the centre page targets "D-SAP Ghule Tutorials Wakad" and is the website link on that centre's Google Business Profile.
- **"Best" searches.** Searches with "best" go to blog guides written as questions with real criteria, never to bare claims in page titles (CCPA coaching guidelines). Planned guides are in `packages/site/blog.json`. <!-- copy-lint-allow: best -->
- **No repeater page.** D-SAP does not run a repeater (dropper) batch, so there is no page for it.
- **Hindi and Marathi.** The current keywords are drafts in natural word order. Many people also search in English or in Hinglish ("jee coaching pune mein"). Native keyword research in Phase 4 replaces the drafts.

## What ranks today

- **ALLEN** (Kota) runs five Pune campuses, including Pimple Saudagar, and its pages describe a "Kota-style" system. <!-- copy-lint-allow-file: kota-style -->
- **Bakliwal Tutorials** (Aundh), **Aakash** (Balewadi, Morwadi) and **FIITJEE** (Swargate) appear in most lists.
- **Local institutes** in our areas: Target 1 Academy (Wakad), Chate Coaching Classes (Pimpri-Chinchwad), Infinity Classes (Chinchwad), Wisdom Edugate and Vishvam Coaching (Wakad), Rajat Academy (Baner).
- **Ranked lists** for "best" searches are mostly aggregators (Collegedunia, Careers360, CollegeDekho) and lists run by competitors (Chaitanya's Academy, Rajat Academy). See `docs/seo/listings-and-citations.md` for every platform and what D-SAP should do on each. <!-- copy-lint-allow: best -->
- **Directories** (Justdial, Sulekha, UrbanPro, LearnPick, AcademyCheck, Lyfskills) carry most local listings. Bakliwal had 347 Justdial reviews as early as 2020.

## Next steps

- Phase 4: native Hindi and Marathi keyword research; measured commutes for every area page; the first blog guides.
- Before launch: search volumes from Keyword Planner for every keyword in the map.
- After launch: monthly review of Search Console queries per page.
