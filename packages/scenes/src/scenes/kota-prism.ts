/**
 * The Kota pentagon (home, second section): a prism with one engraved brass plate per point of
 * the Kota system. The number of sides follows the content, so a sixth point makes a hexagon.
 * Each plate is a brushed, engraved board in a bevelled brass frame with four rivets; the prism
 * stands between two bevelled slabs, on corner pillars, round a lit core, and is crowned with a
 * finial. Scrolling turns each plate to the front in turn, settling on each one.
 */
import { BoxGeometry, CylinderGeometry, ExtrudeGeometry, Group, LatheGeometry, Mesh, Path, Shape, SphereGeometry, Vector2 } from "three";
import { canvasFont, wrapLines } from "../canvas-text.ts";
import { config, perTier, tokenColor } from "../config.ts";
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

/** A regular polygon slab, bevelled all round, standing on y = 0 (lying along y, not z). */
function slab(sides: number, radius: number, depth: number, bevel: number, segments: number): ExtrudeGeometry {
  const shape = new Shape();
  for (let i = 0; i < sides; i++) {
    const a = (i * 2 * Math.PI) / sides;
    const x = Math.sin(a) * radius;
    const y = -Math.cos(a) * radius; // lying down turns shape y into -z; this puts the corners where the plates meet
    if (i === 0) shape.moveTo(x, y);
    else shape.lineTo(x, y);
  }
  shape.closePath();
  const g = new ExtrudeGeometry(shape, { depth, bevelEnabled: true, bevelThickness: bevel, bevelSize: bevel, bevelSegments: segments, steps: 1 });
  g.rotateX(-Math.PI / 2);
  g.translate(0, -depth / 2, 0);
  return g;
}

/** A rectangular frame with a hole, bevelled, facing +z. */
function frame(width: number, height: number, border: number, depth: number, bevel: number, segments: number): ExtrudeGeometry {
  const outer = new Shape();
  outer.moveTo(-width / 2, -height / 2);
  outer.lineTo(width / 2, -height / 2);
  outer.lineTo(width / 2, height / 2);
  outer.lineTo(-width / 2, height / 2);
  outer.closePath();
  const hole = new Path();
  const w = width / 2 - border;
  const h = height / 2 - border;
  hole.moveTo(-w, -h);
  hole.lineTo(-w, h);
  hole.lineTo(w, h);
  hole.lineTo(w, -h);
  hole.closePath();
  outer.holes.push(hole);
  return new ExtrudeGeometry(outer, { depth, bevelEnabled: true, bevelThickness: bevel, bevelSize: bevel, bevelSegments: segments });
}

/** The knop on top of the prism: a turned profile (a lathe), like a finial on a clock. */
function finial(size: number, segments: number): LatheGeometry {
  const profile = [[0, 0], [0.55, 0], [0.62, 0.06], [0.42, 0.14], [0.28, 0.3], [0.34, 0.46], [0.5, 0.62], [0.44, 0.8], [0.22, 0.92], [0.1, 1], [0, 1.04]];
  return new LatheGeometry(profile.map(([x, y]) => new Vector2(x! * size, y! * size)), segments);
}

export function createKotaPrism(ctx: SceneContext, input: KotaPrismInput): Scene {
  const c = config.scenes["kota-prism"];
  const sides = input.points.length;
  if (sides < 3) throw new Error("the Kota prism needs at least three points");
  const { textures } = ctx;
  const detail = perTier(c.detail, ctx.tier);
  const apothem = c.radius * Math.cos(Math.PI / sides);
  const faceWidth = 2 * c.radius * Math.sin(Math.PI / sides);

  const root = new Group();
  root.name = "kota-prism";
  const body = new Group();
  root.add(body);

  // The core: dark stone, and a faint lit column inside it that shows through while the plates fly in.
  body.add(new Mesh(new CylinderGeometry(c.coreRadius, c.coreRadius, c.height, sides), material("stone-dark")));
  body.add(new Mesh(new CylinderGeometry(c.coreRadius * 0.5, c.coreRadius * 0.5, c.height * 0.96, detail.round), material("river")));

  // Two bevelled slabs at each end, the upper one smaller, and the finial on top.
  const brass = material("brass");
  const polished = material("brass-polished");
  for (const sign of [1, -1]) {
    const lower = new Mesh(slab(sides, c.radius * 1.04, c.capHeight, c.cap.bevel, detail.bevel), brass);
    lower.position.y = (sign * (c.height + c.capHeight)) / 2;
    const upper = new Mesh(slab(sides, c.radius * 0.86, c.capHeight * 0.7, c.cap.bevel * 0.8, detail.bevel), polished);
    upper.position.y = lower.position.y + sign * (c.capHeight * 0.85 + c.cap.bevel);
    body.add(lower, upper);
  }
  const crown = new Mesh(finial(c.cap.finial, detail.round * 2), polished);
  crown.position.y = (c.height + c.capHeight) / 2 + c.capHeight * 1.55 + c.cap.bevel;
  body.add(crown);

  // Corner pillars, where two plates meet.
  const pillarGeometry = new CylinderGeometry(c.pillar.radius, c.pillar.radius, c.height + c.capHeight, detail.round);
  const knobGeometry = new SphereGeometry(c.pillar.radius * 1.5, detail.round, Math.round(detail.round * 0.7));
  for (let i = 0; i < sides; i++) {
    const a = (i * 2 * Math.PI) / sides;
    const x = Math.sin(a) * c.radius;
    const z = Math.cos(a) * c.radius;
    const pillar = new Mesh(pillarGeometry, polished);
    pillar.position.set(x, 0, z);
    body.add(pillar);
    for (const sign of [1, -1]) {
      const knob = new Mesh(knobGeometry, polished);
      knob.position.set(x, (sign * (c.height + c.capHeight)) / 2, z);
      body.add(knob);
    }
  }

  const plate = c.plate;
  const plateHeight = Math.round((plate.width * c.height) / faceWidth); // the texture keeps the face's proportions
  const boardWidth = faceWidth - c.frame.width * 2;
  const boardHeight = c.height - c.frame.width * 2;
  const label = (g: CanvasRenderingContext2D, w: number, h: number, text: string, number: string) => {
    const pad = w * plate.padding;
    g.textBaseline = "top";
    g.font = canvasFont("display", 800, w * plate.numberSize);
    g.fillText(number, pad, pad);
    const size = w * plate.labelSize;
    g.font = canvasFont(plate.font as "display", 700, size, text);
    wrapLines(g, text, w - pad * 2).forEach((line, k) => g.fillText(line, pad, h * plate.labelTop + k * size * plate.lineHeight));
  };
  const boardGeometry = new BoxGeometry(boardWidth, boardHeight, c.frame.depth * 0.6);
  const frameGeometry = frame(faceWidth, c.height, c.frame.width, c.frame.depth, c.frame.bevel, detail.bevel);
  const rivetGeometry = new SphereGeometry(c.rivet.radius, detail.rivet, Math.round(detail.rivet * 0.7));
  const plates: { mesh: Group; angle: number }[] = [];
  input.points.forEach((text, i) => {
    const number = String(i + 1).padStart(2, "0");
    const face = textures.canvas(plate.width, plateHeight, (g, w, h) => {
      g.fillStyle = tokenColor(plate.face);
      g.fillRect(0, 0, w, h);
      // Brushed metal: many faint horizontal strokes, light then dark, from a fixed sequence so every visit looks the same.
      for (let k = 0; k < plate.brushed.strokes; k++) {
        const y = (((k * 7919 + i * 104729) % 9973) / 9973) * h;
        g.fillStyle = k % 2 ? `rgba(255, 255, 255, ${plate.brushed.alpha})` : `rgba(0, 0, 0, ${plate.brushed.alpha})`;
        g.fillRect(0, y, w, 1 + (k % 3));
      }
      const wash = g.createLinearGradient(0, 0, w, h);
      wash.addColorStop(0, "rgba(255, 255, 255, 0.14)");
      wash.addColorStop(0.5, "rgba(255, 255, 255, 0)");
      wash.addColorStop(1, "rgba(0, 0, 0, 0.2)");
      g.fillStyle = wash;
      g.fillRect(0, 0, w, h);
      g.fillStyle = tokenColor(plate.text);
      label(g, w, h, text, number);
    }, "colour");
    const relief = textures.canvas(plate.width, plateHeight, (g, w, h) => {
      g.fillStyle = "#808080";
      g.fillRect(0, 0, w, h);
      g.fillStyle = "#000000"; // the engraving sinks into the metal
      label(g, w, h, text, number);
    }, "data");
    const plateGroup = new Group();
    plateGroup.name = `plate-${i}`;
    plateGroup.add(new Mesh(boardGeometry, material("plate", { map: face, bumpMap: relief })));
    const rim = new Mesh(frameGeometry, polished);
    rim.position.z = -c.frame.depth * 0.3;
    plateGroup.add(rim);
    for (const sx of [-1, 1]) {
      for (const sy of [-1, 1]) {
        const rivet = new Mesh(rivetGeometry, polished);
        rivet.position.set((sx * (faceWidth - c.frame.width)) / 2, (sy * (c.height - c.frame.width)) / 2, c.frame.depth * 0.75);
        plateGroup.add(rivet);
      }
    }
    const angle = Math.PI / sides + (i * 2 * Math.PI) / sides;
    plateGroup.position.set(Math.sin(angle) * apothem, 0, Math.cos(angle) * apothem);
    plateGroup.rotation.y = angle;
    body.add(plateGroup);
    plates.push({ mesh: plateGroup, angle });
  });

  root.rotation.x = c.tilt;
  const camera = c.camera as CameraPose;
  const a = c.assemble;
  const scene: Scene = {
    root,
    halfWidth: c.halfWidth,
    halfHeight: c.halfHeight,
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
