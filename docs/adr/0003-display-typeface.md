# 0003. Typefaces: Archivo, Google Sans Flex (Inter as fallback) and Mukta

Date: 2026-10-30. Status: accepted.

## Context

The brief suggested Inter. Inter is excellent for reading but, used for headlines, it is one of the most common generic looks. The site needs headlines in English, Hindi and Marathi.

## Options tested

A. Archivo semi-expanded at 800 for headlines, with Mukta 800 for Devanagari.
B. Zilla Slab 700 for headlines, with Martel 800 for Devanagari.

Both are shown side by side, in all three languages, in the brand guide.

## Decision

A. Archivo's wide, heavy cut stays clear on a phone and sits well beside the 3D medal, and Mukta matches its weight in Devanagari. B echoes the slab lettering on the medal, but reads like print and competes with the medal itself.

- Body and interface text: Google Sans Flex (variable, SIL Open Font License, self-hosted), then Inter as the vendored web fallback, then Arial. Google Sans Flex has no Devanagari, so Hindi and Marathi text is unaffected.
- Hindi and Marathi: Mukta for headlines and text, set 108.97% larger so its x-height matches Google Sans Flex, with taller lines and no letter-spacing.
- While the display font loads, Arial stands in with measured overrides (Archivo Fallback 115.5%), so headlines do not move. Body text has no such stand-in: Inter is the next face in its stack, as chosen on 2026-11-01. Inter is never preloaded.

Amended 2026-11-01: body text moved from Inter to Google Sans Flex.

## Consequences

Fonts are vendored, subset and pinned by SHA-256 in `fonts.lock.json`. Changing a face means editing `fonts.config.json` and `tokens.json`, then `make fonts metrics brand`.
