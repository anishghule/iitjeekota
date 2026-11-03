/**
 * The syllabus slab (opening scene of /jee-syllabus/, docs/design/syllabus-table.md): one stone
 * tile per chapter, set into a slab with a brass edge. Each subject is a block of columns, Class 11
 * before Class 12, and the JEE Advanced only chapters sit in detached rows below their block, like
 * the two separate rows of a periodic table. Scrolling raises the tiles into place while the camera
 * glides from a low angle to straight above, where the HTML table takes over.
 */
import { BoxGeometry, Group, InstancedBufferAttribute, InstancedMesh, Matrix4, Mesh, PlaneGeometry, Vector2 } from "three";
import { canvasFont } from "../canvas-text.ts";
import { config, tokenColor, type Vec3 } from "../config.ts";
import { scrub } from "../keyframes.ts";
import { material } from "../materials.ts";
import type { CameraPose, Scene, SceneContext } from "../scene.ts";

export interface SlabChapter {
  id: string;
  subject: string;
  /** Short text on the tile face, large (the chapter's number within its class). */
  label: string;
  classes: readonly number[];
  /** JEE Main unit number, or null for a chapter in JEE Advanced only. */
  main: number | null;
}

export interface SlabInput {
  /** Subject ids, left to right. */
  subjects: readonly string[];
  chapters: readonly SlabChapter[];
}

export interface TilePlace {
  id: string;
  x: number;
  z: number;
  detached: boolean;
}

/** Class 11 first, then chapters spanning both classes, then Class 12. */
function classOrder(classes: readonly number[]): number {
  if (classes.length > 1) return 1;
  return classes[0] === 11 ? 0 : 2;
}

/** Where each tile sits on the slab, centred on the origin. Pure, so it is tested directly. */
export function slabLayout(input: SlabInput, c = config.scenes["syllabus-slab"]): { tiles: TilePlace[]; width: number; depth: number } {
  const pitch = c.tile.size + c.tile.gap;
  const cols = c.columnsPerSubject;
  const tiles: TilePlace[] = [];
  let x0 = 0;
  let depth = 0;
  for (const subject of input.subjects) {
    const own = input.chapters.filter((ch) => ch.subject === subject);
    const main = own.filter((ch) => ch.main !== null).sort((a, b) => classOrder(a.classes) - classOrder(b.classes));
    const detached = own.filter((ch) => ch.main === null);
    const mainRows = Math.ceil(main.length / cols);
    main.forEach((ch, k) => tiles.push({ id: ch.id, x: x0 + (k % cols) * pitch, z: Math.floor(k / cols) * pitch, detached: false }));
    const detachedTop = mainRows * pitch + c.detachedGap;
    detached.forEach((ch, k) => tiles.push({ id: ch.id, x: x0 + (k % cols) * pitch, z: detachedTop + Math.floor(k / cols) * pitch, detached: true }));
    const rows = detached.length ? detachedTop + Math.ceil(detached.length / cols) * pitch : mainRows * pitch;
    depth = Math.max(depth, rows - c.tile.gap);
    x0 += cols * pitch - c.tile.gap + c.blockGap;
  }
  const width = x0 - c.blockGap;
  for (const t of tiles) {
    t.x += c.tile.size / 2 - width / 2;
    t.z += c.tile.size / 2 - depth / 2;
  }
  return { tiles, width, depth };
}

/**
 * A camera straight above the origin, high enough that a width x depth area fills `fit` of the
 * screen in whichever direction is tighter. The vertical field of view comes from scenes.json.
 */
export function topView(width: number, depth: number, aspect: number, fit: number): CameraPose {
  const halfTan = Math.tan(((config.renderer.fov / 2) * Math.PI) / 180);
  const forDepth = depth / (2 * halfTan);
  const forWidth = width / (2 * halfTan * aspect);
  // A hair off vertical, so the camera's up direction stays defined.
  return { position: [0, Math.max(forDepth, forWidth) / fit, 0.001], target: [0, 0, 0] };
}

export function createSyllabusSlab(ctx: SceneContext, input: SlabInput): Scene {
  const c = config.scenes["syllabus-slab"];
  const { textures } = ctx;
  const layout = slabLayout(input, c);
  const byId = new Map(input.chapters.map((ch) => [ch.id, ch]));
  const count = layout.tiles.length;

  const root = new Group();
  root.name = "syllabus-slab";

  const slabWidth = layout.width + c.slab.margin * 2;
  const slabDepth = layout.depth + c.slab.margin * 2;
  const slab = new Mesh(new BoxGeometry(slabWidth, c.slab.depth, slabDepth), material("stone-dark"));
  slab.position.y = -c.slab.depth / 2;
  const edge = new Mesh(new BoxGeometry(slabWidth + c.slab.edge * 2, c.slab.depth * 0.9, slabDepth + c.slab.edge * 2), material("brass"));
  edge.position.y = -c.slab.depth / 2 - c.slab.depth * 0.06;
  root.add(edge, slab);

  // The tile faces: one atlas texture, one cell per chapter, chosen per instance.
  const a = c.atlas;
  const rows = Math.ceil(count / a.columns);
  const atlas = textures.canvas(a.columns * a.cell, rows * a.cell, (g) => {
    layout.tiles.forEach((place, i) => {
      const ch = byId.get(place.id)!;
      const x = (i % a.columns) * a.cell;
      const y = Math.floor(i / a.columns) * a.cell;
      g.fillStyle = tokenColor("color.stone.600");
      g.fillRect(x, y, a.cell, a.cell);
      g.fillStyle = tokenColor(place.detached ? "color.brass.300" : "color.chalk.50");
      g.textBaseline = "top";
      g.font = canvasFont("body", 600, a.cell * 0.14);
      g.fillText(ch.main === null ? "A" : String(ch.main), x + a.cell * 0.1, y + a.cell * 0.08);
      g.textBaseline = "middle";
      g.textAlign = "center";
      g.font = canvasFont("display", 800, a.cell * 0.42);
      g.fillText(ch.label, x + a.cell / 2, y + a.cell * 0.58);
      g.textAlign = "start";
    });
  }, "colour");

  const tiles = new InstancedMesh(new BoxGeometry(c.tile.size, c.tile.height, c.tile.size), material("stone"), count);
  const faceGeometry = new PlaneGeometry(c.tile.size * 0.9, c.tile.size * 0.9);
  faceGeometry.rotateX(-Math.PI / 2);
  const offsets = new Float32Array(count * 2);
  layout.tiles.forEach((_, i) => {
    offsets[i * 2] = (i % a.columns) / a.columns;
    offsets[i * 2 + 1] = 1 - (Math.floor(i / a.columns) + 1) / rows; // texture v runs bottom to top
  });
  faceGeometry.setAttribute("atlasOffset", new InstancedBufferAttribute(offsets, 2));
  const faceMaterial = material("chalk", { map: atlas });
  const atlasScale = new Vector2(1 / a.columns, 1 / rows);
  faceMaterial.onBeforeCompile = (shader) => {
    shader.uniforms.atlasScale = { value: atlasScale };
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", "#include <common>\nattribute vec2 atlasOffset;\nuniform vec2 atlasScale;")
      .replace("#include <uv_vertex>", "#include <uv_vertex>\n#ifdef USE_MAP\n  vMapUv = vMapUv * atlasScale + atlasOffset;\n#endif");
  };
  const faces = new InstancedMesh(faceGeometry, faceMaterial, count);
  root.add(tiles, faces);

  const m = new Matrix4();
  const placeTiles = (rise: number) => {
    layout.tiles.forEach((t, i) => {
      // Tiles arrive one after another, left to right, during the first third of the section.
      const delay = (i / count) * 0.5;
      const k = scrub(Math.min(1, Math.max(0, (rise - delay) / 0.5)));
      const y = (k - 1) * c.tile.height * 3;
      tiles.setMatrixAt(i, m.makeTranslation(t.x, y + c.tile.height / 2, t.z));
      faces.setMatrixAt(i, m.makeTranslation(t.x, y + c.tile.height + 0.002, t.z));
    });
    tiles.instanceMatrix.needsUpdate = true;
    faces.instanceMatrix.needsUpdate = true;
  };

  const from = c.camera.from;
  const lerp = (p: number[], q: number[], k: number) => [0, 1, 2].map((i) => p[i]! + (q[i]! - p[i]!) * k) as Vec3;
  const scene: Scene = {
    root,
    cameraAt(progress, aspect) {
      const above = topView(slabWidth + c.slab.edge * 2, slabDepth + c.slab.edge * 2, aspect, c.camera.to.fit);
      const k = scrub(progress);
      return { position: lerp(from.position, above.position, k), target: lerp(from.target, above.target, k) } satisfies CameraPose;
    },
    setProgress(progress) {
      placeTiles(Math.min(1, progress * 3));
    },
    update: () => false,
  };
  scene.setProgress(0);
  return scene;
}
