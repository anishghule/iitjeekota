# 0006. Browser toolchain, procedural 3D and our own scroll motion

Date: 2026-10-31. Status: accepted (the user chose to install Node.js now and to build the 3D in code).

## Context

Phase 5 builds the 3D scenes, the autoscroll service and the area map. The scenes and autoscroll run in the browser and need a JavaScript toolchain to write and test. The plan put that toolchain in Phase 6, and the 3D models in Blender.

## Decision

**Runtime and package manager**

- Node.js is pinned in `package.json` (`devEngines.runtime`), so pnpm downloads and uses that exact version. Builds do not depend on what is installed on a machine.
- pnpm workspaces cover `packages/*` and `apps/*`. Only folders with a `package.json` are packages.

**Supply chain, enforced by pnpm rather than by memory**

- Every dependency is pinned exactly, and `pnpm-lock.yaml` is committed.
- `minimumReleaseAge` refuses any version, direct or transitive, published less than 14 days ago.
- Install scripts are blocked. A package that needs one must be named in the workspace file, with a reason.
- Phase 6 CI adds `pnpm audit` and `osv-scanner`.

**Language and tools**

- TypeScript in strict mode, Vitest for tests, and Vite to serve the preview pages. Astro uses Vite too.

**Packages**

| Package | Holds | Runtime dependencies |
| --- | --- | --- |
| `@dsap/tokens` | the generated `tokens.ts` | none |
| `@dsap/motion` | autoscroll, scroll progress, motion preferences, device quality tier | none |
| `@dsap/scenes` | the scene host, quality tiers and every 3D scene | three |

**3D is procedural.** Every object is built in code with three.js, as v3.2's `scene.js` did:

- Colours and finishes come from `material.*` in `packages/tokens/tokens.json`.
- Shapes come from content data. For example, the Kota pentagon has one face per point in the Kota system block, and the syllabus slab has one tile per chapter in `syllabus.json`.
- Textures come from media slots: the official medal and its normal map.

So there is no Blender and there are no binary model files.

**No GSAP and no Lenis.**

- Pinned sections use CSS `position: sticky`, and a section's progress is read from the scroll position.
- Autoscroll is our own service, built to the plan (C5).
- Native scrolling is never replaced, which keeps it accessible and keeps two libraries out of the bundle.

## Consequences

- The runtime dependencies in the plan (D2) shrink to `astro`, `three` and `zod`.
- Phase 6 adds `apps/web`, whose islands import `@dsap/motion` and `@dsap/scenes` unchanged.
- `make check` also runs the TypeScript checks and the Vitest tests.
- Changing a 3D object means changing code or data in this repository, never a file exported from a modelling tool.
