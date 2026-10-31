# Scenes and pinned sections

The storyboard for every pinned section, from the plan (C1, C3, C5). Numbers a designer tunes live in `packages/scenes/scenes.json`; finishes and colours in `packages/tokens/tokens.json`. Every pinned section opts into autoscroll (`data-autoscroll`). Each is a tall box with a sticky stage one screen high, and progress runs from 0 to 1 through it.

Tiers (`qualityTier` in `@dsap/scenes`):

- **Full:** high-end devices get everything.
- **Lite:** four cores or fewer, or 4 GB of memory or less, get less geometry and no antialiasing.
- **Still:** reduced motion, Save-Data or no WebGL2 get a still image of the scene's key frame, and no pinning.

## Built in Phase 5

| Scene | Where | Scroll | What happens |
| --- | --- | --- | --- |
| Medal | Home, opening (not pinned) | as it scrolls past | The struck brass medal floats gently and leans towards the pointer (`float`, `pointer` in scenes.json). The page opens part way through its keyframes, face on; as the hero scrolls away, the medal turns to show its reeded edge. On phones it sits above the hero text. |
| Kota pentagon | Home, Kota system | 0 to 0.3 | The plates fly in from all sides, tumbling, one after another, and lock onto the prism (`assemble`, as in v3.2). |
| | | 0.3 to 1 | Scrolling turns each plate to the front in turn, settling on each; the page's list marks the same point. On narrow screens the camera moves back so the whole prism fits (`fit`). |
| Syllabus slab | Syllabus page, opening | 0 to 0.33 | Tiles rise into the slab, left to right. |
| | | 0 to 1 | The camera glides from a low angle over Physics to straight above, framing the whole table at any screen shape. The HTML table then takes over in the same place. |
| Specimens | Syllabus page and chapter panel | any | A pendulum swings, the benzene ring turns, the surface plot rotates. They animate only while on screen. |

What the medal draws:

- the official medal image as its face
- its normal map for relief
- a reeded edge and brass rims

The pentagon's plates come from `packages/content/blocks/{locale}/kota-system.json`, so a sixth point makes a hexagon. The slab's tiles come from `packages/content/syllabus.json`. The specimens are a Physics pendulum, a Chemistry benzene ring and a Mathematics surface plot, each in a glass case on a brass base.

**Pinning on every screen.** Pinned sections (the Kota system, Kota to Pune, the report and the two-year timeline) pin at every width, so autoscroll works on phones too. From the `pin-from` breakpoint the whole stage holds still, text beside the visual. Below it, the text scrolls past first and only the part marked `data-pin-visual` holds still: the prism with the current point, the Kota to Pune line, the report card, the timeline. Autoscroll acts only while a pinned section fills the whole screen, and never moves against the reader.

**Rendering on demand.** Scenes draw a frame only when something changes. A texture that finishes after the first frame (an image, or a plate redrawn once its font arrives) asks for a new frame itself, so a jump straight to a section (a link, autoscroll) never leaves a blank canvas.

Budgets per tier (triangles and draw calls) are in `scenes.json` and checked by the unit tests. `pnpm exec playwright test` renders every scene at the start, middle and end of its section, on both tiers, and fails on any console error.

## Still to build

| Section | Phase | Approach |
| --- | --- | --- |
| Kota to Pune | 5, with the map data | A low-poly relief of western India with a light trail from Kota to Pune. Rivers glow but are not named. Data from the same OpenStreetMap pipeline as the area map. |
| A real classroom | 5, once `home/classroom-film.mp4` is added | Frames from the upright video, drawn to a canvas by scroll progress. Still tier: the poster frame. |
| The Mac window | 7 | HTML and CSS, tilted with CSS 3D toward the cursor. Not three.js: the window has to be real, readable and accessible. |
| Live test | 7 | HTML. The test is a form, not a scene. |
| Area map | 5 | SVG built from OpenStreetMap (see `make map`). Choosing an area draws the route to its nearer centre. |
| Syllabus slab press-down filter | 7 | CSS 3D on the HTML table: tiles that do not match the filter sink (docs/design/syllabus-table.md). |

## Rules every scene follows

- Text and meaning never live only in a scene. Each section's heading and paragraph are HTML from `packages/content`, and the scene illustrates them.
- Scenes render only while on screen, and only when something changed or they are animating.
- Under reduced motion there is no pinning and no autoscroll, and the still image shows.
- Each scene's materials come from `material.*` tokens, and its sizes, keyframes and budgets from `scenes.json`. Its content comes from the page's own data.
