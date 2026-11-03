# Google Business Profiles (Phase 3)

Both centres already have a profile (confirmed by D-SAP, 2026-10-30). This is the claim and clean-up checklist for each. The exact NAP lines are in `docs/seo/listings-and-citations.md`, generated from `packages/site/centres.json`.

## For each centre: New Sangvi (head office) and Wakad

### Ownership

- [ ] Confirm D-SAP owns or manages the profile in Business Profile Manager. If someone else does, request ownership.
- [ ] Add a second manager from D-SAP so access never depends on one person.

### Name, address, phone

- [ ] Business name exactly "D-SAP Ghule Tutorials". No keywords added to the name (Google treats that as spam).
- [ ] Address exactly as in `centres.json`. Wakad: "First floor, Shiv Malhar, Swami Vivekanand Nagar, Wakad, Pimpri-Chinchwad, Maharashtra 411057".
- [ ] Phone: the same number as the site (`contact.phone`, still to confirm). Use the same number everywhere.
- [ ] Map pin on the building entrance. Copy the pin's latitude and longitude (5 decimals) into `facts.json` (`centre.sangvi.geo`, `centre.wakad.geo`).
- [ ] For Wakad, copy the profile's Maps share link into `centre.wakad.maps`.

### Category, hours, description

- [ ] Primary category: the closest coaching category Google offers in the editor (look for "Coaching center"). Check the list in the editor before choosing.
- [ ] Secondary categories only if true, for example "Tutoring service".
- [ ] Opening hours, including Sundays if tests run then. Copy them into `facts.json` (`centre.*.hours`).
- [ ] Description in plain words, the same facts as the site, no "best" or guarantees. <!-- copy-lint-allow: best -->

### Website link

- [ ] Website: the centre page, `https://iitjeekota.com/en/centres/sangvi-head-office/` or `https://iitjeekota.com/en/centres/wakad/`, once live.
- [ ] Add a UTM tag to tell profile visits apart in analytics (`?utm_source=google&utm_medium=organic&utm_campaign=gbp-wakad`).

### Photos and posts

- [ ] Logo: the official medal (`packages/brand/dist/logo/medal-512.png`).
- [ ] Real photos of the entrance, classroom and digital board, from the media library. No stock photos.
- [ ] A post when a batch opens or an admission test is scheduled.

### Reviews

- [ ] Reply to every review, kindly and briefly, within a few days.
- [ ] Ask enrolled families for honest reviews. Never offer anything in return, and never review from staff accounts (Google's review policy, and fake reviews are an offence under the Consumer Protection Act).

### Features that changed

- [ ] Questions and answers: reported retired (the Q&A API closed on 3 November 2025, according to SEO agency sources). Check whether the section still shows; put common questions on the site's FAQ page instead.
- [ ] Messaging: reports say WhatsApp can now be linked as the chat option. Check in the editor and link the D-SAP WhatsApp number (`contact.whatsapp`) if available.

## Afterwards

- [ ] Use the cleaned profiles as the source for Bing Places (import) and Apple Business Connect.
- [ ] Check monthly that nobody has suggested edits that changed the name, address, hours or category.
