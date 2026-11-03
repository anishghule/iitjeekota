# 0001. Build tooling: one Python package, standard library only

Date: 2026-10-30. Status: accepted.

## Context

Phase 2 needs tooling for tokens, fonts, icons, logo sizes, favicons, OG images, a copy linter and the brand guide. Node is not installed on the development machine yet, and the contract asks for the fewest possible dependencies.

## Decision

All tooling lives in `tools/dsapkit`, a Python package that uses only the standard library, with one CLI (`python -m dsapkit`, wrapped by `make`). Data lives in `packages/*`; the package holds only logic. Modules are split by concern: `tokens`, `fonts`, `icons`, `images`, `media`, `brand`, `copylint`, `guide`. `tokens` and `fonts` never import `brand`, `icons` or `guide`.

The only external programs are `rsvg-convert` and fontconfig, used to turn SVG into PNG.

## Consequences

- Nothing to audit in a dependency tree, and the tooling runs anywhere Python 3.12 runs.
- The web build (Phase 6) runs `make tokens icons` before Astro, or reads the generated `dist/` files.
- If Phase 6 prefers Node for tooling, the module boundaries and data formats carry over unchanged.
