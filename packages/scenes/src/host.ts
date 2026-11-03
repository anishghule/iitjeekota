/**
 * Puts a scene on a canvas in the page: renderer, studio light, camera, size, visibility and
 * scroll progress. Renders only while the canvas is on screen, and only when something changed or
 * the scene is animating. Everything it creates is released when the returned function runs.
 */
import { holdProgress, observeProgress, passageProgress } from "@dsap/motion";
import {
  ACESFilmicToneMapping,
  AmbientLight,
  CanvasTexture,
  Color,
  DirectionalLight,
  DoubleSide,
  Mesh,
  MeshBasicMaterial,
  NoColorSpace,
  PerspectiveCamera,
  PlaneGeometry,
  PMREMGenerator,
  PointLight,
  Scene as World,
  SRGBColorSpace,
  TextureLoader,
  Vector3,
  WebGLRenderer,
  type Material,
  type Texture,
} from "three";
import { config, tokenColor, type RenderTier } from "./config.ts";
import type { Scene, SceneContext, TexturePort } from "./scene.ts";

/** Textures for the browser: images from URLs, and canvases redrawn once the fonts they use have loaded. */
/**
 * Textures for the browser. A scene renders on demand, so whenever a texture changes after the
 * scene is built (an image finishes loading, a canvas is drawn again once its fonts arrive),
 * `changed` is called and the host draws a new frame.
 */
export function browserTextures(doc: Document, changed: () => void = () => {}): TexturePort {
  const loader = new TextureLoader();
  const space = (kind: "colour" | "data") => (kind === "colour" ? SRGBColorSpace : NoColorSpace);
  return {
    image(url, kind) {
      const texture = loader.load(url, changed);
      texture.colorSpace = space(kind);
      texture.anisotropy = 8;
      return texture;
    },
    canvas(width, height, draw, kind) {
      const canvas = doc.createElement("canvas");
      canvas.width = width;
      canvas.height = height;
      const context = canvas.getContext("2d");
      if (!context) throw new Error("no 2D canvas");
      const fonts = new Set<string>();
      // Record every font the drawing asks for, so we can wait for exactly those.
      const recording = new Proxy(context, {
        get: (target, key) => {
          const value = Reflect.get(target, key, target) as unknown;
          return typeof value === "function" ? (value as (...args: unknown[]) => unknown).bind(target) : value;
        },
        set: (target, key, value) => {
          if (key === "font") fonts.add(String(value));
          return Reflect.set(target, key, value, target);
        },
      });
      const texture = new CanvasTexture(canvas);
      texture.colorSpace = space(kind);
      texture.anisotropy = 8;
      const paint = () => {
        context.clearRect(0, 0, width, height);
        draw(recording, width, height);
        texture.needsUpdate = true;
      };
      paint();
      if (fonts.size && doc.fonts) {
        void Promise.all([...fonts].map((f) => doc.fonts.load(f))).then(() => {
          paint();
          changed();
        }, () => {});
      }
      return texture;
    },
  };
}

/** The studio the metal reflects: glowing panels, blurred into an environment map. */
export function studioEnvironment(renderer: WebGLRenderer): Texture {
  const s = config.studio;
  const studio = new World();
  studio.background = new Color(tokenColor(s.background));
  for (const pane of s.panes) {
    const mesh = new Mesh(
      new PlaneGeometry(pane.size[0], pane.size[1]),
      new MeshBasicMaterial({ color: new Color(tokenColor(pane.color)).multiplyScalar(pane.intensity), side: DoubleSide }),
    );
    mesh.position.set(...(pane.position as [number, number, number]));
    mesh.rotation.set(...(pane.rotation as [number, number, number]));
    studio.add(mesh);
  }
  const pmrem = new PMREMGenerator(renderer);
  const texture = pmrem.fromScene(studio, s.blur).texture;
  pmrem.dispose();
  studio.traverse((obj) => {
    if (obj instanceof Mesh) {
      obj.geometry.dispose();
      (obj.material as Material).dispose();
    }
  });
  return texture;
}

export function addLights(world: World): void {
  const s = config.studio;
  world.add(new AmbientLight(tokenColor(s.ambient.color), s.ambient.intensity));
  const key = new DirectionalLight(tokenColor(s.key.color), s.key.intensity);
  key.position.set(...(s.key.position as [number, number, number]));
  const rim = new PointLight(tokenColor(s.rim.color), s.rim.intensity, s.rim.distance, s.rim.decay);
  rim.position.set(...(s.rim.position as [number, number, number]));
  world.add(key, rim);
}

export function disposeAll(world: World): void {
  world.traverse((obj) => {
    if (!(obj instanceof Mesh)) return;
    obj.geometry.dispose();
    const materials: Material[] = Array.isArray(obj.material) ? obj.material : [obj.material];
    for (const m of materials) {
      for (const value of Object.values(m)) if ((value as Texture | null)?.isTexture) (value as Texture).dispose();
      m.dispose();
    }
  });
}

export interface MountOptions {
  canvas: HTMLCanvasElement;
  /** The section whose scroll progress drives the scene. */
  section: HTMLElement;
  tier: RenderTier;
  create: (ctx: SceneContext) => Scene;
  /** "pinned" (default): progress while the section holds still; "passage": while it scrolls past. */
  progress?: "pinned" | "passage";
  win?: Window;
}

export function mountScene(options: MountOptions): () => void {
  const win = options.win ?? window;
  const { canvas, tier } = options;
  const renderer = new WebGLRenderer({ canvas, antialias: tier === "full", alpha: true, powerPreference: "high-performance" });
  renderer.setPixelRatio(Math.min(win.devicePixelRatio || 1, config.tiers.pixelRatio[tier]));
  renderer.toneMapping = ACESFilmicToneMapping;
  renderer.toneMappingExposure = config.renderer.exposure;

  const world = new World();
  world.environment = studioEnvironment(renderer);
  addLights(world);
  // A texture that finishes after the first frame asks for another; request is defined below and
  // only ever called later, from a load or font event.
  const scene = options.create({ tier, textures: browserTextures(win.document, () => request()) });
  world.add(scene.root);

  const camera = new PerspectiveCamera(config.renderer.fov, 1, config.renderer.near, config.renderer.far);
  const target = new Vector3();
  let progress = 0;
  let dirty = true;
  let visible = false;
  let frame = 0;

  const render = (time: number) => {
    frame = 0;
    const animating = scene.update(time);
    if (dirty || animating) {
      const pose = scene.cameraAt(progress, camera.aspect);
      camera.position.set(...pose.position);
      target.set(...pose.target);
      camera.lookAt(target);
      renderer.render(world, camera);
      dirty = false;
    }
    if (visible && animating) frame = win.requestAnimationFrame(render);
  };
  const request = () => {
    dirty = true;
    if (!frame && visible) frame = win.requestAnimationFrame(render);
  };

  const sizes = new ResizeObserver(() => {
    const { clientWidth: w, clientHeight: h } = canvas;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    request();
  });
  sizes.observe(canvas);
  const seen = new IntersectionObserver(([entry]) => {
    visible = entry?.isIntersecting ?? false;
    if (visible) request();
  });
  seen.observe(canvas);
  const stopProgress = observeProgress(options.section, (p) => {
    progress = p;
    scene.setProgress(p);
    request();
  }, win, options.progress === "passage" ? passageProgress : holdProgress(options.section, win));

  // Scenes that follow the pointer get its position across the whole window.
  const follow = scene.setPointer?.bind(scene);
  const onPointer = (e: PointerEvent) => {
    follow?.((e.clientX / win.innerWidth) * 2 - 1, (e.clientY / win.innerHeight) * 2 - 1);
    request();
  };
  if (follow) win.addEventListener("pointermove", onPointer, { passive: true });

  return () => {
    if (frame) win.cancelAnimationFrame(frame);
    win.removeEventListener("pointermove", onPointer);
    stopProgress();
    seen.disconnect();
    sizes.disconnect();
    disposeAll(world);
    world.environment?.dispose();
    renderer.dispose();
  };
}
