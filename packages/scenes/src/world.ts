/**
 * The world: one canvas behind the whole page, one three.js world, and a camera that travels
 * between scenes as the reader scrolls (the v3.2 camera rail, rebuilt on the scene contract). Each
 * scene sits at its own anchor below the one before; the camera dwells on a scene while its section
 * holds the screen and flies to the next over the scroll between (rail.ts). Each scene is framed
 * into its slot, the empty box in the page where it belongs, so the layout decides where it sits.
 * Scenes stay pure builders: they never learn they share a canvas.
 */
import { holdProgress, passageProgress, type ProgressMeasure } from "@dsap/motion";
import {
  AdditiveBlending,
  ACESFilmicToneMapping,
  BufferAttribute,
  BufferGeometry,
  Fog,
  Group,
  PerspectiveCamera,
  Points,
  PointsMaterial,
  Scene as World,
  Vector3,
  WebGLRenderer,
} from "three";
import { config, perTier, tokenColor, type RenderTier, type Vec3 } from "./config.ts";
import { addLights, browserTextures, disposeAll, studioEnvironment } from "./host.ts";
import { fitWidth } from "./scenes/kota-prism.ts";
import { railAt, type Extent } from "./rail.ts";
import type { Scene, SceneContext } from "./scene.ts";

export type Progress = "passage" | "pinned" | ProgressMeasure;

export interface StationOptions {
  /** The section that drives the scene's progress and the camera's travel. */
  section: HTMLElement;
  /** The empty box the scene is framed into. */
  slot: HTMLElement;
  create: (ctx: SceneContext) => Scene;
  /** False while the slot is not shown (a phone that hides it): the scene then drops out of the rail. */
  enabled?: () => boolean;
  /** "passage": while the section scrolls past; "pinned": while its held part holds still; or a measure of your own. */
  progress: Progress;
}

export interface WorldOptions {
  canvas: HTMLCanvasElement;
  tier: RenderTier;
  /** In page order. */
  stations: StationOptions[];
  win?: Window;
}

const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

/** Specks along the whole rail, placed from a seed so every visit looks the same. */
export function dustPositions(count: number, stationCount: number, seed: number): Float32Array {
  const d = config.world.dust;
  const depth = (stationCount - 1) * config.world.spacing;
  let state = seed;
  const next = () => {
    state = (state * 1664525 + 1013904223) % 4294967296;
    return state / 4294967296;
  };
  const out = new Float32Array(count * 3);
  for (let i = 0; i < count; i++) {
    out[i * 3] = (next() - 0.5) * 2 * d.width;
    out[i * 3 + 1] = 10 - next() * (depth + 20);
    out[i * 3 + 2] = (next() - 0.5) * 2 * d.depth;
  }
  return out;
}

export function mountWorld(options: WorldOptions): () => void {
  const win = options.win ?? window;
  const { canvas, tier } = options;
  const renderer = new WebGLRenderer({ canvas, antialias: tier === "full", alpha: true, powerPreference: "high-performance" });
  renderer.setPixelRatio(Math.min(win.devicePixelRatio || 1, config.tiers.pixelRatio[tier]));
  renderer.toneMapping = ACESFilmicToneMapping;
  renderer.toneMappingExposure = config.renderer.exposure;

  const world = new World();
  world.environment = studioEnvironment(renderer);
  world.fog = new Fog(tokenColor(config.world.fog.color), config.world.fog.near, config.world.fog.far);
  addLights(world);

  let dirty = true;
  let frame = 0;
  const textures = browserTextures(win.document, () => request());
  const ctx: SceneContext = { tier, textures };

  const stations = options.stations.map((o, i) => {
    const scene = o.create(ctx);
    const anchor: Vec3 = [0, -i * config.world.spacing, 0];
    const holder = new Group();
    holder.position.set(...anchor);
    holder.add(scene.root);
    world.add(holder);
    const measure: ProgressMeasure =
      typeof o.progress === "function" ? o.progress : o.progress === "passage" ? passageProgress : holdProgress(o.section, win);
    return { ...o, scene, anchor, measure };
  });

  const dust = config.world.dust;
  const specks = new BufferGeometry();
  specks.setAttribute("position", new BufferAttribute(dustPositions(perTier(dust.count, tier), stations.length, dust.seed), 3));
  const dot = textures.canvas(64, 64, (g, w, h) => {
    const glow = g.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, w / 2);
    glow.addColorStop(0, "rgba(255, 255, 255, 1)");
    glow.addColorStop(1, "rgba(255, 255, 255, 0)");
    g.fillStyle = glow;
    g.fillRect(0, 0, w, h);
  }, "colour");
  const speckMaterial = new PointsMaterial({
    map: dot,
    color: tokenColor(dust.color),
    size: dust.size,
    sizeAttenuation: true,
    transparent: true,
    opacity: dust.opacity,
    depthWrite: false,
    blending: AdditiveBlending,
  });
  world.add(new Points(specks, speckMaterial));

  const camera = new PerspectiveCamera(config.renderer.fov, 1, config.renderer.near, config.renderer.far);
  const here = new Vector3();
  const there = new Vector3();
  const lookAt = new Vector3();

  /** Where the camera would be for station i: its own pose, fitted to its slot, moved to its anchor. */
  const poseFor = (i: number, progress: number, slot: DOMRect, viewport: { w: number; h: number }) => {
    const s = stations[i]!;
    let pose = s.scene.cameraAt(progress, viewport.w / viewport.h);
    const w = slot.width || viewport.w;
    const h = slot.height || viewport.h;
    // Fit across the slot, then down it: a height fits like a width of the slot's proportions.
    if (s.scene.halfWidth) pose = fitWidth(pose, s.scene.halfWidth, w / viewport.h);
    if (s.scene.halfHeight) pose = fitWidth(pose, (s.scene.halfHeight * w) / h, w / viewport.h);
    return {
      position: new Vector3(pose.position[0] + s.anchor[0], pose.position[1] + s.anchor[1], pose.position[2] + s.anchor[2]),
      target: new Vector3(pose.target[0] + s.anchor[0], pose.target[1] + s.anchor[1], pose.target[2] + s.anchor[2]),
    };
  };

  let animating = false;
  const render = (time: number) => {
    frame = 0;
    const vw = win.innerWidth;
    const vh = win.innerHeight;
    const y = win.scrollY;
    const view = { w: vw, h: vh };
    const live = stations.map((s, i) => i).filter((i) => stations[i]!.enabled?.() ?? true);
    const boxes = stations.map((s) => s.section.getBoundingClientRect());
    const slots = stations.map((s) => s.slot.getBoundingClientRect());
    const extents: Extent[] = live.map((i) => ({ start: boxes[i]!.top + y, end: boxes[i]!.bottom + y }));
    const found = railAt(extents, y, vh);
    const state = { ...found, from: live[found.from] ?? 0, to: live[found.to] ?? 0 };
    const progress = stations.map((s, i) => s.measure(boxes[i]!.top, boxes[i]!.height, vh));
    stations.forEach((s, i) => s.scene.setProgress(progress[i]!));
    if (live.length === 0) {
      canvas.style.opacity = "0";
      return;
    }

    const a = poseFor(state.from, progress[state.from]!, slots[state.from]!, view);
    const b = poseFor(state.to, progress[state.to]!, slots[state.to]!, view);
    here.lerpVectors(a.position, b.position, state.t);
    there.lerpVectors(a.target, b.target, state.t);
    camera.position.copy(here);
    lookAt.copy(there);
    // Fog starts beyond the subject, wherever the camera had to stand to fit it in its slot: a smaller slot must not dim it.
    const subject = here.distanceTo(there);
    if (world.fog instanceof Fog) {
      world.fog.near = subject + config.world.fog.near;
      world.fog.far = subject + config.world.fog.far;
    }
    camera.lookAt(lookAt);
    // Each scene is framed into its slot: shift the picture so the scene's centre lands on the slot's centre.
    const offset = (i: number) => ({ x: (slots[i]!.left + slots[i]!.width / 2 || vw / 2) - vw / 2, y: (slots[i]!.top + slots[i]!.height / 2 || vh / 2) - vh / 2 });
    const from = offset(state.from);
    const to = offset(state.to);
    camera.setViewOffset(vw, vh, -lerp(from.x, to.x, state.t), -lerp(from.y, to.y, state.t), vw, vh);

    canvas.style.opacity = state.opacity.toFixed(3);
    animating = stations.map((s) => s.scene.update(time)).some(Boolean) && state.opacity > 0.02;
    if (state.opacity > 0.01) renderer.render(world, camera);
    dirty = false;
    if (animating) frame = win.requestAnimationFrame(render);
  };
  function request() {
    dirty = true;
    if (!frame) frame = win.requestAnimationFrame(render);
  }

  const sizes = new ResizeObserver(() => {
    const w = win.innerWidth;
    const h = win.innerHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    request();
  });
  sizes.observe(win.document.documentElement);
  win.addEventListener("scroll", request, { passive: true });
  win.addEventListener("resize", request);
  const follow = stations.map((s) => s.scene.setPointer?.bind(s.scene));
  const onPointer = (e: PointerEvent) => {
    follow.forEach((f) => f?.((e.clientX / win.innerWidth) * 2 - 1, (e.clientY / win.innerHeight) * 2 - 1));
    request();
  };
  win.addEventListener("pointermove", onPointer, { passive: true });
  request();

  return () => {
    if (frame) win.cancelAnimationFrame(frame);
    win.removeEventListener("scroll", request);
    win.removeEventListener("resize", request);
    win.removeEventListener("pointermove", onPointer);
    sizes.disconnect();
    disposeAll(world);
    specks.dispose();
    speckMaterial.dispose();
    world.environment?.dispose();
    renderer.dispose();
  };
}

