# 0003. Typefaces: Archivo, Inter and Mukta

Date: 2026-10-30. Status: accepted.

## Context

The brief suggested Inter. Inter is excellent for reading but, used for headlines, it is one of the most common generic looks. The site needs headlines in English, Hindi and Marathi.

## Options tested

A. Archivo semi-expanded at 800 for headlines, with Mukta 800 for Devanagari.
B. Zilla Slab 700 for headlines, with Martel 800 for Devanagari.

Both are shown side by side, in all three languages, in the brand guide.

## Decision

A. Archivo's wide, heavy cut stays clear on a phone and sits well beside the 3D medal, and Mukta matches its weight in Devanagari. B echoes the slab lettering on the medal, but reads like print and competes with the medal itself.

- Body and interface text: Inter (variable, with tabular figures for scores and fees).
- Hindi and Marathi: Mukta for headlines and text, set 116.64% larger so its x-height matches Inter, with taller lines and no letter-spacing.
- While web fonts load, Arial stands in with measured overrides (Inter Fallback 107.34%, Archivo Fallback 115.5%), so the layout does not move.

## Consequences

Fonts are vendored, subset and pinned by SHA-256 in `fonts.lock.json`. Changing a face means editing `fonts.config.json` and `tokens.json`, then `make fonts metrics brand`.
