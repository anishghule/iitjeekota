# The syllabus index

The design for `/{lang}/jee-syllabus/` and its smaller copy on the home page (`SyllabusTeaser`). Data is `packages/content/syllabus.json`; the page copy is in `packages/content/pages/{locale}/`.

## What it has to do

A parent or student comes to find one thing: "is this chapter in the syllabus, and what does it cover?" So the page must be complete (all 78 chapters, every topic), quick to scan, and fully readable without JavaScript, by search engines and by screen readers.

## The design

A plain index, one subject at a time.

- **Rows, not tiles.** Each chapter is one line: its code, its name, and its place in JEE Main. Rows sit under a "Class 11" or "Class 12" heading. There are no boxes, side tags or colour per subject.
- **Codes.** `11-P-03` is the class the chapter is first taught in (11), the subject letter (P, C or M, from `subjects[].code` in `syllabus.json`) and its place among that subject's chapters of that class, in the order of the file, counted from 01. A chapter taught across both classes is listed with Class 11, and its open row says so. Codes are built by `Syllabus.code` in `tools/dsapkit` and exported as `code`; they are never typed in by hand. Inserting a chapter renumbers the ones after it, so copy refers to chapters by id, as everywhere else.
- **Open a row for the topics.** A row is a native `<details>`: the topics, and "JEE Advanced also asks" where `advancedAlso` has entries. Nothing is fetched or built by script, so closed rows are still in the page for crawlers, and the keyboard and screen readers work as they do for any disclosure.
- **Three filters.** Subject (one at a time, Physics first), class (all, 11, 12) and exam (all, JEE Main, JEE Advanced). Filtering hides rows, and a count says how many remain. A class or exam filter that leaves nothing in a class hides its heading. "Expand all" opens every visible row.
- **Links to a chapter.** Each row has the lower-case code as its id: `#11-p-03` selects that subject, clears the filters, opens the row and scrolls to it.
- **JEE Advanced only.** Those rows say so in place of a unit number, in the accent colour. Nothing is set apart.
- **Other languages.** Topics exist in English only so far; Hindi and Marathi show the chapter name and unit on a plain row until the topics are translated.

## What was dropped

The earlier design was a periodic table: a tile per chapter with a two-letter symbol, a side panel, a slab in perspective. Two letters said nothing about the chapter, the grid hid names behind taps, and the table metaphor explained nothing a list does not. The 3D slab scene (`packages/scenes`, `syllabus-slab`) is not used by the page; its tile label is now whatever the caller passes.

## Behaviour and access

- Filters are toggle buttons with `aria-pressed`; the count is announced politely.
- Under reduced motion nothing animates except the row chevron's turn, which the motion tokens already shorten.
- Keyboard: Tab to a row, Enter or Space opens it.

## Performance

- The HTML for all 78 chapters stays small; there is no JSON copy of the data in the page.
- One small island does the filtering.
