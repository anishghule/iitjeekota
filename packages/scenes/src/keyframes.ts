/** Scroll keyframes: where an object is at a point of its section's progress. */
import { tokens } from "@dsap/tokens";
import type { Vec3 } from "./config.ts";

export interface Keyframe {
  at: number;
  position: number[];
  rotation: number[];
}

export interface Pose {
  position: Vec3;
  rotation: Vec3;
}

/** A CSS-style cubic-bezier easing, solved for x by Newton's method. */
export function cubicBezier([x1, y1, x2, y2]: readonly number[]): (x: number) => number {
  const a = (p1: number, p2: number) => 1 - 3 * p2 + 3 * p1;
  const b = (p1: number, p2: number) => 3 * p2 - 6 * p1;
  const c = (p1: number) => 3 * p1;
  const at = (t: number, p1: number, p2: number) => ((a(p1, p2) * t + b(p1, p2)) * t + c(p1)) * t;
  const slope = (t: number, p1: number, p2: number) => 3 * a(p1, p2) * t * t + 2 * b(p1, p2) * t + c(p1);
  const [px1, py1, px2, py2] = [x1 ?? 0, y1 ?? 0, x2 ?? 1, y2 ?? 1];
  return (x) => {
    if (x <= 0) return 0;
    if (x >= 1) return 1;
    let t = x;
    for (let i = 0; i < 8; i++) {
      const d = slope(t, px1, px2);
      if (Math.abs(d) < 1e-6) break;
      t -= (at(t, px1, px2) - x) / d;
    }
    return at(t, py1, py2);
  };
}

/** The scrub easing from the motion tokens, used for everything tied to scrolling. */
export const scrub = cubicBezier(tokens.motion.ease.scrub);

function lerp3(a: number[], b: number[], k: number): Vec3 {
  return [0, 1, 2].map((i) => (a[i] ?? 0) + ((b[i] ?? 0) - (a[i] ?? 0)) * k) as Vec3;
}

/** The pose at a progress between 0 and 1, eased between the two keyframes around it. */
export function poseAt(keyframes: readonly Keyframe[], progress: number): Pose {
  const first = keyframes[0];
  const last = keyframes[keyframes.length - 1];
  if (!first || !last) throw new Error("a scene needs at least one keyframe");
  if (progress <= first.at) return { position: lerp3(first.position, first.position, 0), rotation: lerp3(first.rotation, first.rotation, 0) };
  for (let i = 1; i < keyframes.length; i++) {
    const a = keyframes[i - 1]!;
    const b = keyframes[i]!;
    if (progress <= b.at) {
      const k = scrub((progress - a.at) / (b.at - a.at));
      return { position: lerp3(a.position, b.position, k), rotation: lerp3(a.rotation, b.rotation, k) };
    }
  }
  return { position: lerp3(last.position, last.position, 0), rotation: lerp3(last.rotation, last.rotation, 0) };
}
