/** Typed access to scenes.json and to token colours by path. */
import { tokens } from "@dsap/tokens";
import data from "../scenes.json";

export type Tier = "full" | "lite" | "still";
/** Tiers that render 3D. "still" shows an image instead. */
export type RenderTier = Exclude<Tier, "still">;
export type Vec3 = [number, number, number];

export const config = data;
export type SceneName = keyof typeof data.scenes;

/** A colour from the tokens by path, such as "color.brass.200" or "scene.light-key". */
export function tokenColor(path: string): string {
  let node: unknown = tokens;
  for (const key of path.split(".")) {
    node = typeof node === "object" && node !== null ? (node as Record<string, unknown>)[key] : undefined;
  }
  if (typeof node !== "string" || !node.startsWith("#")) {
    throw new Error(`scenes.json: ${path} is not a colour token`);
  }
  return node;
}

/** A per-tier value from scenes.json, such as { "full": 128, "lite": 64 }. */
export function perTier<T>(value: Record<RenderTier, T>, tier: RenderTier): T {
  return value[tier];
}
