/**
 * From Kota to Pune (home, third section): a small relief map, plains on the Kota side and a
 * ridge between the two cities, drawn as lit terrain with a fine contour mesh over it. A route
 * draws itself from Kota to Pune as the reader scrolls, a bead of light running along it. Kota is
 * a pin on a ring; Pune is a house, and when the route arrives its windows light and warm the
 * ground round it: the Kota programme comes home. The names hang on plates over each city.
 */
import {
  AdditiveBlending,
  BoxGeometry,
  BufferGeometry,
  CatmullRomCurve3,
  Color,
  ConeGeometry,
  ExtrudeGeometry,
  Float32BufferAttribute,
  Group,
  Line,
  LineBasicMaterial,
  LineDashedMaterial,
  Mesh,
  MeshBasicMaterial,
  MeshStandardMaterial,
  PlaneGeometry,
  PointLight,
  Shape,
  SphereGeometry,
  Sprite,
  SpriteMaterial,
  TorusGeometry,
  TubeGeometry,
  Vector3,
} from "three";
import { canvasFont } from "../canvas-text.ts";
import { config, perTier, tokenColor } from "../config.ts";
import { scrub } from "../keyframes.ts";
import { material } from "../materials.ts";
import type { CameraPose, Scene, SceneContext } from "../scene.ts";

export interface RouteInput {
  /** The two city names, as the page shows them. */
  kota: string;
  pune: string;
}

const clamp = (x: number) => Math.min(1, Math.max(0, x));
const smooth = (x: number) => {
  const t = clamp(x);
  return t * t * (3 - 2 * t);
};

/** How much of the route is drawn at this progress: nothing until `from`, all of it from `to`. */
export function routeDrawn(progress: number): number {
  const { from, to } = config.scenes.route.draw;
  return scrub(clamp((progress - from) / (to - from)));
}

/** Smooth value noise on a grid, hashed from the cell, so the land is the same on every visit. */
function noise(x: number, z: number, seed: number): number {
  const hash = (i: number, j: number) => {
    const n = Math.sin(i * 127.1 + j * 311.7 + seed * 74.7) * 43758.5453;
    return n - Math.floor(n);
  };
  const ix = Math.floor(x);
  const iz = Math.floor(z);
  const fx = smooth(x - ix);
  const fz = smooth(z - iz);
  const a = hash(ix, iz);
  const b = hash(ix + 1, iz);
  const c = hash(ix, iz + 1);
  const d = hash(ix + 1, iz + 1);
  return (a + (b - a) * fx) + ((c + (d - c) * fx) - (a + (b - a) * fx)) * fz;
}

function fbm(x: number, z: number, seed: number): number {
  let sum = 0;
  let amplitude = 0.5;
  let frequency = 1;
  for (let o = 0; o < 4; o++) {
    sum += noise(x * frequency, z * frequency, seed + o) * amplitude;
    amplitude /= 2;
    frequency *= 2;
  }
  return sum;
}

/** Ground height at (x, z): gentle plains, a ridge between the cities, falling to nothing at the map's edge. */
export function terrainHeight(x: number, z: number): number {
  const t = config.scenes.route.terrain;
  const edge = clamp(1 - (x / t.halfWidth) ** 2 - (z / t.halfDepth) ** 2);
  const plains = fbm(x * t.scale, z * t.scale, t.seed) * t.plains;
  const ridge = Math.exp(-((x - t.ridge.at) ** 2) / (2 * t.ridge.width ** 2)) * t.ridge.height * (0.55 + 0.9 * fbm(x * t.scale * 1.3, z * t.scale * 1.3, t.seed + 9));
  return (plains + ridge) * smooth(edge * 2.2);
}

export function createRoute(ctx: SceneContext, input: RouteInput): Scene {
  const c = config.scenes.route;
  const t = c.terrain;
  const root = new Group();
  root.name = "route";
  const colour = (path: string) => tokenColor(path);

  // --- the land: lit terrain coloured by height, fading into the page at its edge, with a contour mesh over it ---
  const cells = perTier(c.cells, ctx.tier);
  const land = new PlaneGeometry(t.halfWidth * 2, t.halfDepth * 2, cells[0], cells[1]);
  land.rotateX(-Math.PI / 2);
  const pos = land.attributes.position!;
  const colours = new Float32Array(pos.count * 4); // colour and opacity: the land fades into the page at its edge

  const low = new Color(colour(c.colours.low));
  const mid = new Color(colour(c.colours.mid));
  const high = new Color(colour(c.colours.high));
  const scratch = new Color();
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i);
    const z = pos.getZ(i);
    const h = terrainHeight(x, z);
    pos.setY(i, h);
    const level = clamp(h / (t.ridge.height * 1.1));
    scratch.copy(low).lerp(mid, smooth(level * 1.6)).lerp(high, smooth((level - 0.55) * 2.4));
    const inside = clamp(1 - (x / t.halfWidth) ** 2 - (z / t.halfDepth) ** 2);
    colours.set([scratch.r, scratch.g, scratch.b, smooth(inside * 3)], i * 4);

  }
  land.setAttribute("color", new Float32BufferAttribute(colours, 4));
  land.computeVertexNormals();
  root.add(new Mesh(land, new MeshStandardMaterial({ vertexColors: true, transparent: true, roughness: 0.92, metalness: 0.05 })));
  // The contour mesh is a coarser grid over the same land, its lines fading to nothing with it.
  const grid = new PlaneGeometry(t.halfWidth * 2, t.halfDepth * 2, c.contour.cells[0], c.contour.cells[1]);
  grid.rotateX(-Math.PI / 2);
  const gp = grid.attributes.position!;
  const lines = new Float32Array(gp.count * 3);
  const lineColour = new Color(colour(c.contour.color));
  for (let i = 0; i < gp.count; i++) {
    const x = gp.getX(i);
    const z = gp.getZ(i);
    gp.setY(i, terrainHeight(x, z));
    const fade = smooth(clamp(1 - (x / t.halfWidth) ** 2 - (z / t.halfDepth) ** 2) * 3);
    lines.set([lineColour.r * fade, lineColour.g * fade, lineColour.b * fade], i * 3);
  }
  grid.setAttribute("color", new Float32BufferAttribute(lines, 3));
  const mesh = new Mesh(grid, new MeshBasicMaterial({ vertexColors: true, wireframe: true, transparent: true, opacity: c.contour.opacity, blending: AdditiveBlending, depthWrite: false }));
  mesh.position.y = 0.012;
  root.add(mesh);

  const ground = (x: number, z: number) => terrainHeight(x, z);
  const [kotaAt, puneAt] = c.cities.map((p) => new Vector3(p[0], ground(p[0]!, p[1]!), p[1])) as [Vector3, Vector3];

  // --- the route: along the ground between the cities, bending a little, lifted over the ridge ---
  const points: Vector3[] = [];
  const steps = 48;
  for (let i = 0; i <= steps; i++) {
    const u = i / steps;
    const x = kotaAt.x + (puneAt.x - kotaAt.x) * u;
    const z = kotaAt.z + (puneAt.z - kotaAt.z) * u + Math.sin(u * Math.PI * 1.6) * c.route.bend;
    points.push(new Vector3(x, ground(x, z) + c.route.lift + Math.sin(u * Math.PI) * c.route.arch, z));
  }
  const curve = new CatmullRomCurve3(points, false, "catmullrom", 0.5);
  const tubular = c.route.segments;
  const sides = c.route.sides;
  const core = new Mesh(new TubeGeometry(curve, tubular, c.route.radius, sides, false), material("brass-polished"));
  const halo = new Mesh(new TubeGeometry(curve, tubular, c.route.radius * 3, sides, false), new MeshBasicMaterial({ color: colour(c.bead.color), transparent: true, opacity: 0.22, blending: AdditiveBlending, depthWrite: false }));
  const drawIndices = (share: number) => Math.floor(share * tubular) * sides * 6;
  core.geometry.setDrawRange(0, 0);
  halo.geometry.setDrawRange(0, 0);
  // The whole route, faint and dashed, so the reader sees where it is going.
  const ghost = new Line(new BufferGeometry().setFromPoints(curve.getPoints(120)), new LineDashedMaterial({ color: colour(c.bead.color), dashSize: 0.18, gapSize: 0.16, transparent: true, opacity: 0.35 }));
  ghost.computeLineDistances();
  root.add(ghost, halo, core);

  const dot = ctx.textures.canvas(64, 64, (g, w, h) => {
    const r = g.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, w / 2);
    r.addColorStop(0, "rgba(255, 255, 255, 1)");
    r.addColorStop(0.4, "rgba(255, 255, 255, 0.4)");
    r.addColorStop(1, "rgba(255, 255, 255, 0)");
    g.fillStyle = r;
    g.fillRect(0, 0, w, h);
  }, "colour");
  const bead = new Mesh(new SphereGeometry(c.bead.radius, 20, 14), new MeshBasicMaterial({ color: colour(c.bead.color) }));
  const glow = new Sprite(new SpriteMaterial({ map: dot, color: colour(c.bead.color), transparent: true, blending: AdditiveBlending, depthWrite: false }));
  glow.scale.set(c.bead.glow, c.bead.glow, 1);
  root.add(bead, glow);

  // --- Kota: a pin on a ring ---
  const pin = new Group();
  pin.position.copy(kotaAt);
  const spike = new Mesh(new ConeGeometry(0.13, 0.55, 20), material("brass"));
  spike.rotation.x = Math.PI;
  spike.position.y = 0.3;
  const head = new Mesh(new SphereGeometry(0.2, 24, 16), material("brass-polished"));
  head.position.y = 0.72;
  const ring = new Mesh(new TorusGeometry(0.5, 0.025, 12, 48), new MeshBasicMaterial({ color: colour(c.bead.color), transparent: true, opacity: 0.7 }));
  ring.rotation.x = Math.PI / 2;
  ring.position.y = 0.05;
  pin.add(spike, head, ring);
  root.add(pin);

  // --- Pune: a house with a gabled roof, a chimney, a door and two windows that light on arrival ---
  const house = new Group();
  house.position.copy(puneAt);
  const size = c.house.size;
  const walls = new Mesh(new BoxGeometry(size, size * 0.75, size * 0.8), material("chalk"));
  walls.position.y = (size * 0.75) / 2;
  const gable = new Shape();
  gable.moveTo(-size * 0.58, 0);
  gable.lineTo(size * 0.58, 0);
  gable.lineTo(0, size * 0.5);
  gable.closePath();
  const roofGeometry = new ExtrudeGeometry(gable, { depth: size * 0.95, bevelEnabled: true, bevelThickness: 0.02, bevelSize: 0.02, bevelSegments: 2 });
  roofGeometry.translate(0, 0, -size * 0.475);
  const roof = new Mesh(roofGeometry, material("brass-polished"));
  roof.position.y = size * 0.75;
  const chimney = new Mesh(new BoxGeometry(size * 0.14, size * 0.3, size * 0.14), material("stone"));
  chimney.position.set(size * 0.25, size * 0.98, -size * 0.15);
  const door = new Mesh(new BoxGeometry(size * 0.2, size * 0.4, 0.03), material("brass"));
  door.position.set(0, size * 0.2, size * 0.4);
  const windowMaterial = new MeshStandardMaterial({ color: colour(c.bead.color), emissive: colour(c.bead.color), emissiveIntensity: 0, roughness: 0.4 });
  const windows = [-1, 1].map((side) => {
    const w = new Mesh(new BoxGeometry(size * 0.17, size * 0.17, 0.03), windowMaterial);
    w.position.set(side * size * 0.28, size * 0.42, size * 0.4);
    return w;
  });
  house.add(walls, roof, chimney, door, ...windows);
  const homeLight = new PointLight(colour(c.bead.color), 0, 5);
  homeLight.position.set(0, size * 0.6, size * 0.9);
  house.add(homeLight);
  root.add(house);

  // --- plates with the names, hanging over each city on a fine line ---
  const label = (text: string, at: Vector3) => {
    const texture = ctx.textures.canvas(512, 160, (g, w, h) => {
      g.fillStyle = colour(c.plate.face);
      g.beginPath();
      g.roundRect(6, 6, w - 12, h - 12, 22);
      g.fill();
      g.strokeStyle = colour(c.plate.text);
      g.lineWidth = 4;
      g.globalAlpha = 0.5;
      g.beginPath();
      g.roundRect(16, 16, w - 32, h - 32, 14);
      g.stroke();
      g.globalAlpha = 1;
      g.fillStyle = colour(c.plate.text);
      g.textAlign = "center";
      g.textBaseline = "middle";
      g.font = canvasFont("display", 800, h * 0.48, text);
      g.fillText(text, w / 2, h / 2 + 4);
    }, "colour");
    const sprite = new Sprite(new SpriteMaterial({ map: texture, transparent: true }));
    sprite.scale.set(c.plate.width, (c.plate.width * 160) / 512, 1);
    sprite.position.set(at.x, at.y + c.plate.lift, at.z);
    const stem = new Line(new BufferGeometry().setFromPoints([at.clone().add(new Vector3(0, 0.1, 0)), sprite.position.clone().add(new Vector3(0, -0.25, 0))]), new LineBasicMaterial({ color: colour(c.plate.face), transparent: true, opacity: 0.6 }));
    root.add(sprite, stem);
  };
  label(input.kota, kotaAt);
  label(input.pune, puneAt);

  const camera = c.camera as CameraPose;
  let arrivedAt = 0;
  const scene: Scene = {
    root,
    halfWidth: c.halfWidth,
    halfHeight: c.halfHeight,
    cameraAt: () => camera,
    setProgress(progress) {
      const drawn = routeDrawn(progress);
      core.geometry.setDrawRange(0, drawIndices(drawn));
      halo.geometry.setDrawRange(0, drawIndices(drawn));
      const at = curve.getPointAt(Math.min(0.999, Math.max(0.001, drawn)));
      bead.position.copy(at);
      glow.position.copy(at);
      bead.visible = glow.visible = drawn > 0.002 && drawn < 0.998;
      arrivedAt = smooth((drawn - 0.94) / 0.06);
      windowMaterial.emissiveIntensity = arrivedAt * 2.2;
      homeLight.intensity = arrivedAt * 3;
      house.scale.setScalar(1 + arrivedAt * 0.1);
    },
    update(timeMs) {
      const pulse = (timeMs / 1600) % 1;
      ring.scale.setScalar(1 + pulse * 0.6);
      (ring.material as MeshBasicMaterial).opacity = 0.7 * (1 - pulse);
      return true; // the ring on Kota keeps pulsing while the scene is on screen
    },
  };
  scene.setProgress(0);
  return scene;
}
