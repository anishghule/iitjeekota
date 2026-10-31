# Voice

How iitjeekota.com sounds, in every language. The rules the linter enforces live in `packages/brand/voice.json`; this page explains them.

## Who we are talking to

A parent, often at the end of a long day, deciding where their child will spend two important years. And the student, who wants to know what a week will look like. Both want plain facts from people who know the exam.

## How we write

- Write like a senior teacher talking to a parent at the front desk.
- One idea per sentence. Keep sentences under about 20 words; the linter warns past 28.
- Say the number. "30 students a batch" tells a parent more than "small batches".
- Every claim has a source in the facts register, or it is cut.
- Indian English: programme, centre, enrol, practise (verb). Dates as 1 April 2027. Fees as ₹1,50,000.
- Headings in sentence case. No small labels above headings.
- The Kota partnership is stated plainly: D-SAP Ghule Tutorials is powered by a named Kota institute, with Kota faculty. It is a partnership, never a copied style.

## Punctuation

No em dashes or en dashes, anywhere. Use a full stop, a comma or a colon. For ranges, write "Class 9 to 10". The linter also catches a spaced hyphen used as a dash.

## Claims

The CCPA guidelines for coaching advertisements (2024) treat unsupported superlatives, guarantees and selective results as misleading. Words that make such claims are listed under `claims` in `voice.json`. They are allowed only after legal review, with `copy-lint-allow` on that line. A blog may ask how to choose a good coaching institute as a question, and answer it with real criteria.

## Hindi and Marathi

Native writers write them; they are not machine translated. Until a native review is done, text is marked as a draft (`draft` in OG copy, `draftLocales` in the media library). Native reviewers add Hindi and Marathi word lists to `voice.json`.

## The linter

`make copy-lint` reads the files listed under `scan` in `voice.json`. Directives, in any comment:

- `copy-lint-disable` and `copy-lint-enable` skip the lines between them, for pages that quote bad copy on purpose.
- `copy-lint-allow: word` allows a listed word on that line and the next.
- `copy-lint-allow-file: word` allows it in the whole file.

Every rewrite example in `voice.json` is also a test: its "before" must fail and its "after" must pass.
