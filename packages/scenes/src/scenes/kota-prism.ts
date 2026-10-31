/**
 * The Kota pentagon (home, second section): a prism with one engraved brass plate per point of
 * the Kota system. The number of sides follows the content, so a sixth point makes a hexagon.
 * Scrolling turns each plate to the front in turn, settling on each one.
 */
import { CylinderGeometry, Group, Mesh, PlaneGeometry } from "three";
import { canvasFont, wrapLines } from "../canvas-text.ts";
import { config, tokenColor } from "../config.ts";
import { scrub } from "../keyframes.ts";
import { material } from "../materials.ts";
import type { CameraPose, Scene, SceneContext } from "../scene.ts";

export interface KotaPrismInput {
  /** The points of the Kota system block, as shown on the page (facts already filled in). */
  points: readonly string[];
}

/** Rotation that brings plate `index` of `sides` to face the camera. */
export function plateFacing(index: number, sides: number): number {
  return -(Math.PI / sides + (index * 2 * Math.PI) / sides);
}

/**
 * How far plate i has come home (0 to 1) when the assembly is this far along (0 to 1). Each plate
 * starts a little after the one before it; all have landed when the assembly is complete.
 */
export function plateArrival(assembly: number, index: number, count: number, stagger: number): number {
  const span = 1 - stagger * (count - 1);
  const t = Math.min(1, Math.max(0, (assembly - index * stagger) / span));
  return 1 - (1 - t) ** 3; // fast, then settling into place
}

/**
 * The camera pose, moved back along its line of sight when the screen is too narrow for an object
 * this wide (half width in world units) to fit across it. Wide screens keep the pose as it is.
 */
export function fitWidth(pose: CameraPose, halfWidth: number, aspect: number): CameraPose {
  const [px, py, pz] = pose.position;
  const [tx, ty, tz] = pose.target;
  const distance = Math.hypot(px - tx, py - ty, pz - tz);
  const halfAcross = Math.tan(((config.renderer.fov / 2) * Math.PI) / 180) * aspect;
  const needed = halfWidth / halfAcross;
  if (needed <= distance) return pose;
  const k = needed / distance;
  return { position: [tx + (px - tx) * k, ty + (py - ty) * k, tz + (pz - tz) * k], target: pose.target };
}

export function createKotaPrism(ctx: SceneContext, input: KotaPrismInput): Scene {
  const c = config.scenes["kota-prism"];
  const sides = input.points.length;
  if (sides < 3) throw new Error("the Kota prism needs at least three points");
  const { textures } = ctx;
  const apothem = c.radius * Math.cos(Math.PI / sides);
  const faceWidth = 2 * c.radius * Math.sin(Math.PI / sides);

  const root = new Group();
  root.name = "kota-prism";
  const body = new Group();
  root.add(body);

  body.add(new Mesh(new CylinderGeometry(c.coreRadius, c.coreRadius, c.height, sides), material("stone-dark")));
  const capGeometry = new CylinderGeometry(c.radius, c.radius, c.capHeight, sides);
  const capMaterial = material("brass");
  for (const sign of [1, -1]) {
    const cap = new Mesh(capGeometry, capMaterial);
    cap.position.y = sign * (c.height + c.capHeight) / 2;
    body.add(cap);
  }

  const plate = c.plate;
  const plates: { mesh: Mesh; angle: number }[] = [];
  const plateGeometry = new PlaneGeometry(faceWidth, c.height);
  const plateHeight = Math.round((plate.width * c.height) / faceWidth); // the texture keeps the face's proportions
  input.points.forEach((text, i) => {
    const texture = textures.canvas(plate.width, plateHeight, (g, w, h) => {
      const pad = w * plate.padding;
      g.fillStyle = tokenColor(plate.face);
      g.fillRect(0, 0, w, h);
      g.fillStyle = tokenColor(plate.text);
      g.textBaseline = "top";
      g.font = canvasFont("display", 800, w * plate.numberSize);
      g.fillText(String(i + 1).padStart(2, "0"), pad, pad);
      const size = w * plate.labelSize;
      g.font = canvasFont(plate.font as "display", 700, size, text);
      wrapLines(g, text, w - pad * 2).forEach((line, k) => g.fillText(line, pad, h * plate.labelTop + k * size * plate.lineHeight));
    }, "colour");
    const mesh = new Mesh(plateGeometry, material("plate", { map: texture }));
    const angle = Math.PI / sides + (i * 2 * Math.PI) / sides;
    mesh.position.set(Math.sin(angle) * apothem, 0, Math.cos(angle) * apothem);
    mesh.rotation.y = angle;
    mesh.name = `plate-${i}`;
    body.add(mesh);
    plates.push({ mesh, angle });
  });

  root.rotation.x = c.tilt;
  const camera = c.camera as CameraPose;
  const a = c.assemble;
  const scene: Scene = {
    root,
    cameraAt: (_progress, aspect) => fitWidth(camera, c.radius * c.fit.value, aspect),
    setProgress(progress) {
      // First the plates fly in and lock onto the faces, one after another.
      const assembly = Math.min(1, progress / a.until);
      plates.forEach(({ mesh, angle }, i) => {
        const away = 1 - plateArrival(assembly, i, sides, a.stagger);
        const out = apothem + away * a.distance;
        const side = i % 2 === 0 ? 1 : -1; // alternate plates come from above and below
        mesh.position.set(Math.sin(angle) * out, side * away * a.lift, Math.cos(angle) * out);
        mesh.rotation.set(side * away * a.tumble, angle + away * a.spin, 0);
      });
      // Then the prism turns plate by plate: whole steps between plates, eased within each step.
      const turn = Math.max(0, (progress - a.until) / (1 - a.until));
      const steps = turn * (sides - 1);
      const whole = Math.min(sides - 1, Math.floor(steps));
      const eased = whole + scrub(steps - whole);
      body.rotation.y = plateFacing(0, sides) - (eased * 2 * Math.PI) / sides;
    },
    update: () => false,
  };
  scene.setProgress(0);
  return scene;
}
