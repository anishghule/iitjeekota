/**
 * Scene preview (pnpm preview): every scene on a pinned section, with real content and autoscroll.
 * ?tier=full|lite forces a quality tier. This page is a development tool and never ships.
 */
import { bindAutoscroll, observeProgress } from "@dsap/motion";
import facts from "../../site/facts.json";
import syllabus from "../../content/syllabus.json";
import kotaSystem from "../../content/blocks/en/kota-system.json";
import faceUrl from "../../brand/dist/logo/medal-512.png?url";
import normalUrl from "../../media/assets/brand/dsap-medal-normal.webp?url";
import {
  createKotaPrism,
  createMedal,
  createSpecimens,
  createSyllabusSlab,
  mountScene,
  qualityTier,
  readDeviceSignals,
  type RenderTier,
  type Scene,
  type SceneContext,
} from "../src/index.ts";

/**
 * Preview only: fills {{fact:id}} and {{fact:id#field}} from facts.json so the Kota plates read as
 * they will. The site gets copy already resolved by make web-data (docs/adr/0007-web-app.md).
 */
function fillFacts(text: string): string {
  return text.replace(/\{\{fact:([\w.-]+)(?:#(\w+))?\}\}/g, (_, id: string, field?: string) => {
    const fact = facts.facts.find((f) => f.id === id);
    const value: unknown = field ? (fact?.value as Record<string, unknown> | undefined)?.[field] : fact?.value;
    return typeof value === "string" ? value : "";
  });
}

const forced = new URLSearchParams(location.search).get("tier");
const detected = qualityTier(readDeviceSignals(window));
const tier: RenderTier = forced === "full" || forced === "lite" ? forced : detected === "still" ? "lite" : detected;
document.getElementById("tier")!.textContent = `Tier: ${tier}${forced ? " (forced)" : ""}`;

const points = kotaSystem.points.map((p) => fillFacts(typeof p === "string" ? p : p.text));
const builders: Record<string, (ctx: SceneContext) => Scene> = {
  medal: (ctx) => createMedal(ctx, { faceUrl, normalUrl }),
  "kota-prism": (ctx) => createKotaPrism(ctx, { points }),
  "syllabus-slab": (ctx) =>
    createSyllabusSlab(ctx, {
      subjects: syllabus.subjects.map((s) => s.id),
      chapters: syllabus.chapters.map((c) => ({ id: c.id, subject: c.subject, label: c.names.en.slice(0, 2), classes: c.classes, main: c.main })),
    }),
  specimens: (ctx) => createSpecimens(ctx),
};

for (const section of document.querySelectorAll<HTMLElement>("[data-scene]")) {
  const create = builders[section.dataset.scene!];
  const canvas = section.querySelector("canvas");
  const readout = section.querySelector("output");
  if (!create || !canvas) continue;
  mountScene({ canvas, section, tier, create });
  if (readout) observeProgress(section, (p) => (readout.textContent = `${Math.round(p * 100)}%`));
}

const autoscroll = bindAutoscroll(window);
const toggle = document.getElementById("autoscroll") as HTMLButtonElement;
const show = () => {
  toggle.setAttribute("aria-pressed", String(autoscroll.isOn()));
  toggle.textContent = autoscroll.isAvailable() ? `Autoscroll ${autoscroll.isOn() ? "on" : "off"}` : "Autoscroll off (reduced motion)";
};
toggle.addEventListener("click", () => {
  autoscroll.setOn(!autoscroll.isOn());
  show();
});
show();
