/**
 * Mounts the 3D scenes (@dsap/scenes) in sections marked data-scene. three.js loads only when a
 * scene section comes near and the device is not on the still tier (reduced motion, Save-Data, no
 * WebGL, low memory). On the still tier the section keeps its still image or plain content.
 * Scene input comes from the section: data attributes, or a JSON block marked data-scene-input.
 */
import { qualityTier, readDeviceSignals } from "@dsap/scenes/quality";
import { readJson } from "../lib/format.ts";

const NEAR = "50% 0px";

function input<T>(section: HTMLElement, fallback: T): T {
  return readJson<T>(section, "script[data-scene-input]") ?? fallback;
}

async function mount(section: HTMLElement, tier: "full" | "lite"): Promise<void> {
  const scenes = await import("@dsap/scenes");
  const slot = section.querySelector<HTMLElement>("[data-scene-slot]");
  if (!slot) return;
  const canvas = section.ownerDocument.createElement("canvas");
  canvas.className = "scene-canvas";
  canvas.setAttribute("aria-hidden", "true");
  slot.replaceChildren(canvas);
  section.dataset.sceneMounted = "";
  const name = section.dataset.scene;
  const create =
    name === "medal"
      ? (ctx: Parameters<typeof scenes.createMedal>[0]) =>
          scenes.createMedal(ctx, { faceUrl: section.dataset.face ?? "", normalUrl: section.dataset.normal ?? "" })
      : name === "kota-prism"
        ? (ctx: Parameters<typeof scenes.createKotaPrism>[0]) => scenes.createKotaPrism(ctx, input(section, { points: [] as string[] }))
        : undefined;
  const progress = section.dataset.sceneProgress === "passage" ? "passage" : "pinned";
  if (create) scenes.mountScene({ canvas, section, tier, create, progress });
}

export function initScenes(win: Window): void {
  const tier = qualityTier(readDeviceSignals(win));
  win.document.documentElement.dataset.sceneTier = tier;
  if (tier === "still") return;
  const watcher = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        watcher.unobserve(entry.target);
        void mount(entry.target as HTMLElement, tier);
      }
    },
    { rootMargin: NEAR },
  );
  for (const section of win.document.querySelectorAll<HTMLElement>("[data-scene]")) watcher.observe(section);
}
