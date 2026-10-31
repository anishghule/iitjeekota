# 0004. The official logo and the media library

Date: 2026-10-30. Status: accepted.

## Context

D-SAP has an official medal logo (a 1024 px PNG, also served at dsapghuletutorials.com/images/logo.png). A vector redraw was started before this was confirmed and has been removed. The v3.2 reference build shows the medal in 3D as struck metal.

## Decision

- Every image the site uses has a slot in `packages/media/manifest.json` with its source, alt text per language, credit, licence and a placeholder flag. Supplied files are fetched from their recorded source and pinned in `media.lock.json`.
- The official medal is the only logo. The build finds the medal inside the image from its transparency, centres it, and makes every logo size, favicon, app icon and OG image from it. Favicons use the official medal at every size, by D-SAP's choice.
- The 3D medal follows v3.2 (`scene.js`): the same image as the face texture, its normal map (slot `brand/logo-medal-normal`) for relief, and the `material.medal-*` tokens for the metal finish. It is built in Phase 5.
- Before any asset is drawn, generated or replaced, the source is checked in `packages/media`, `resources/` and dsapghuletutorials.com, and D-SAP confirms it.

## Consequences

Replacing the logo means pointing the slot at the new file and running `make media-fetch brand`; nothing else changes. Prof. Ghule's photo is in the library; consent for its use on iitjeekota.com is to be confirmed in Phase 0.
