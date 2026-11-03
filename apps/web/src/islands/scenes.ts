/**
 * Mounts the 3D world (@dsap/scenes) behind the page: one canvas, and the camera travels between
 * the scenes of the sections marked data-scene as the page scrolls. Each section has a slot
 * (data-scene-slot), the empty box its scene is framed into. three.js loads only when a scene
 * section comes near and the device is not on the still tier (reduced motion, Save-Data, no WebGL,
 * low memory); on the still tier the sections keep their still images or plain content.
 * Scene input comes from the section: a JSON block marked data-scene-input.
 */
import { qualityTier, readDeviceSignals } from "@dsap/scenes/quality";
import { readJson } from "../lib/format.ts";

const NEAR = "50% 0px";

/** The tree grows from where its section reaches this share of the screen height, to the section's end. */
const TREE_FROM = 0.8;

/** Share of the section scrolled through, counting from when its top reaches `TREE_FROM` of the screen. */
export function sectionFill(top: number, height: number, viewport: number): number {
  if (height <= 0) return 0;
  return Math.min(1, Math.max(0, (viewport * TREE_FROM - top) / height));
}

/** How far a box has crossed the screen, 0 as its top enters at the bottom, 1 once it is two thirds of the way up. */
export function slotCrossing(top: number, viewport: number): number {
  return Math.min(1, Math.max(0, (viewport - top) / (viewport * 0.75)));
}

function input<T>(section: HTMLElement, fallback: T): T {
  return readJson<T>(section, "script[data-scene-input]") ?? fallback;
}

async function mount(canvas: HTMLCanvasElement, sections: HTMLElement[], tier: "full" | "lite", win: Window): Promise<void> {
  const scenes = await import("@dsap/scenes");
  const wide = () => win.document.documentElement.dataset.layout === "wide";
  const stations = sections.flatMap((section): Parameters<typeof scenes.mountWorld>[0]["stations"] => {
    const slot = section.querySelector<HTMLElement>("[data-scene-slot]");
    if (!slot) return [];
    // A slot the layout hides (the Kota route on a phone) takes its scene out of the rail.
    const enabled = () => slot.getClientRects().length > 0;
    switch (section.dataset.scene) {
      case "medal":
        return [{ section, slot, enabled, progress: "passage", create: (ctx) => scenes.createMedal(ctx, { faceUrl: section.dataset.face ?? "", normalUrl: section.dataset.normal ?? "" }) }];
      case "kota-prism":
        return [{ section, slot, enabled, progress: "pinned", create: (ctx) => scenes.createKotaPrism(ctx, input(section, { points: [] as string[] })) }];
      case "route":
        return [{ section, slot, enabled, progress: "pinned", create: (ctx) => scenes.createRoute(ctx, input(section, { kota: "", pune: "" })) }];
      case "tree":
        return [{
          section, slot, enabled,
          // Wide, the tree holds beside the timeline and grows as the section passes; narrow, it sits above the timeline and grows as it crosses the screen.
          progress: (top, height, viewport) => (wide() ? sectionFill(top, height, viewport) : slotCrossing(slot.getBoundingClientRect().top, viewport)),
          create: (ctx) => scenes.createTree(ctx, input(section, { milestones: 1 })),
        }];
      default:
        return [];
    }
  });
  if (stations.length === 0) return;
  scenes.mountWorld({ canvas, tier, stations });
  win.document.documentElement.dataset.world = "";
}

export function initScenes(win: Window): void {
  const tier = qualityTier(readDeviceSignals(win));
  const doc = win.document;
  doc.documentElement.dataset.sceneTier = tier;
  const canvas = doc.querySelector<HTMLCanvasElement>("canvas[data-world]");
  const sections = Array.from(doc.querySelectorAll<HTMLElement>("[data-scene]"));
  if (tier === "still" || !canvas || sections.length === 0) return;
  const watcher = new IntersectionObserver(
    (entries) => {
      if (!entries.some((e) => e.isIntersecting)) return;
      watcher.disconnect();
      void mount(canvas, sections, tier, win);
    },
    { rootMargin: NEAR },
  );
  sections.forEach((s) => watcher.observe(s));
}
