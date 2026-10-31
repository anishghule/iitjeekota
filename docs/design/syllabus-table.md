# The syllabus table

The design for `/{lang}/jee-syllabus/` and its smaller copies on the home page and the Class 11 and Class 12 pages. It is built in Phase 5 (3D) and Phase 7 (frontend) from `packages/content/syllabus.json`. The page copy is in `packages/content/pages/{locale}/jee-syllabus.json`.

## What we keep from v3.2

The v3.2 table (`resources/dsap-iitjeekota-v3.2/js/modules.js`, the syllabus section) got the idea right. These parts carry over:

- One tile per chapter, with a two-letter symbol, a number and the chapter name, like an element.
- A tint per subject.
- Filter chips for subject and class.
- A side panel with the chapter's topics, closed by Esc, the close button or a tap outside.
- Tiles that arrive one after another the first time the table is seen.
- The whole syllabus as plain text in a `<details>` block, and a PDF.

## What changes, and why

1. **The data is official.** v3.2 had 62 chapters, including chapters NTA no longer sets (Mathematical Reasoning, Hydrogen and s-Block, Polymers) and a made-up "emphasis" shade. The new table has 78 chapters taken from the JEE Main 2027 syllabus and the JEE Advanced 2026 brochure. `make content` checks that every official unit and heading is covered. The emphasis shade is gone: no source backs it.
2. **It is laid out like a real periodic table.** Each subject is a block of columns. Rows are periods: Class 11 on top, Class 12 below, and chapters taught across both classes on the line between. On a phone the three blocks stack.
3. **JEE Advanced chapters are the detached rows.** A real periodic table keeps the lanthanides and actinides in two rows below the main grid. Here the 9 Chemistry chapters that are only in JEE Advanced sit in rows below the grid, labelled "JEE Advanced only". The metaphor now explains something true about the exam.
4. **The tile number is the official unit.** A tile shows its JEE Main unit number, the way an element shows its atomic number. Chapters in JEE Advanced only show "A".
5. **There is an exam filter.** Main, Advanced or both. With Advanced on, the two chapters that are only in JEE Main (Semiconductor Devices, Magnetism and Matter) step back, and the detached rows come up. A brass corner on a tile marks a chapter where JEE Advanced asks for more (`advancedAlso`).
6. **The panel reads like an element card.** It shows the symbol large, then the unit number, classes and exam badges, the topics, then "JEE Advanced adds". It links to the Class 11 or Class 12 programme. "How we teach it" shows only when the faculty have written it for that chapter; there is no sample text.
7. **Students can track their own progress.** In the panel, a student can mark a chapter as done. Done tiles fill with brass, and each subject shows a count. This is stored only in the browser (`localStorage`), never sent anywhere, and the page works the same without it. It turns the table into something a student comes back to.

## Where 3D helps, and where it does not

3D is used only where depth carries meaning. The table itself stays HTML, so it is readable by screen readers, search engines and AI crawlers, and works on slow phones.

1. **The slab (CSS 3D, on the real table).** The grid sits in a slight perspective, as tiles of Kota stone set into a slab with a brass edge. Filtering presses tiles that do not match down into the slab instead of fading them. The shape of the table stays readable, and the state is visible at a glance. When the Advanced filter turns on, the detached rows rise up out of the slab. This is CSS transforms and shadows only, using the `material.stone`, `material.stone-dark` and `material.brass` tokens.
2. **The opening scene (three.js, Phase 5).** A pinned scene at the top of the page: the camera glides low across the slab, from Physics to Chemistry to Mathematics. Each block lights up as its chapter count appears. The scene ends looking straight down, then cross-fades to the HTML table in the same position. It follows the autoscroll rules in the plan (C5). The fallback is a single still render.
3. **Three specimens (three.js, small).** One object per subject, in a glass case (`material.glass`): a pendulum for Physics, a molecule for Chemistry and a surface plot for Mathematics. They appear in the opening scene and as the header mark in the chapter panel. This reuses the "glass display cases" idea from the plan (C3), at three renders instead of 78.

Looked at and not used:

- **A rotating cylinder or helix of chapters.** It looks good in a demo, but hides half the chapters at any time and is hard to scan.
- **An animated model per chapter.** 78 models add weight and say nothing the topic list does not.
- **Physics on the tiles (falling, scattering).** It is fun once and annoying the second time.

## Behaviour and access

- Tiles are buttons in a list. Each has a label that reads in full, for example: "Physics, Class 11, unit 2: Kinematics. In JEE Main and JEE Advanced."
- Filters are toggle buttons with `aria-pressed`. The count of matching chapters is announced politely.
- On wide screens the panel is a side sheet that does not trap focus. On phones it is a bottom sheet that does. Closing it returns focus to the tile.
- Under reduced motion there is no stagger, no slab perspective and no opening scene. Filtering changes opacity only.
- Keyboard: the arrow keys move across the grid, Enter opens a tile, Esc closes the panel.

## Design tokens to add (Phase 7)

The table needs three subject tints, as surface roles with contrast pairs in `packages/tokens/contrast.json`. The proposal, to be checked on both surfaces:

| Role | Idea |
| --- | --- |
| `subject-physics` | the river blue, a step lighter |
| `subject-chemistry` | verdigris, the green of old brass |
| `subject-maths` | a warm clay |

Brass stays the accent, used for "Advanced adds" corners and for chapters marked done.

## Performance

- The table HTML for all 78 chapters stays under 25 KB, compressed.
- No script is needed to read the table or its text version. Filters, the panel and progress are one small island.
- The opening scene loads only when the page is idle and the device is in the full quality tier. Its fallback image is the poster.
