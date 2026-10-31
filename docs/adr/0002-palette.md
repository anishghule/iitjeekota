# 0002. Palette: Kota Stone and Brass

Date: 2026-10-30. Status: accepted.

## Context

The plan asked for a D-SAP palette built from Kota stone, brass and chalk, one action colour for calls to action, and contrast checked for every pair. The official D-SAP medal is warm sand on a dark field.

## Decision

- Neutrals are Kota stone greys with a green-blue cast (`ink`, `stone`). Light pages use a cool limestone off-white (`chalk`), not a warm cream.
- Brass is tuned to the official medal: `brass.300` is the medal's sand (#e6c296), sampled from the logo, and the other steps share its hue.
- There is no separate vermilion or saffron call-to-action colour. One colour cannot pass contrast on both a near-black and an off-white surface, and a lone bright accent on near-black is a common generic look. The action role is polished brass on ink surfaces and ink on chalk surfaces.
- River blue is kept for the map and the Kota to Pune route.
- Components only use surface roles (`--text`, `--accent`, `--action-bg`); `data-surface` switches every role at once.

## Consequences

`contrast.json` lists 22 pairs per surface; the token build stops if any falls below AA (4.5:1), AAA for body text (7:1) or the 3:1 rule for marks and field edges.
