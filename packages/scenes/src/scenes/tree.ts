/**
 * The journey tree (home, two-years section), ported from the v3.2 scene: an open book with a
 * golden tree growing from its gutter, one branch per milestone of the programme spiralling up the
 * trunk, twigs and leaves following each branch, a crown and a lit finial at the top, laurel
 * sprigs round the book, and motes of light lifting off the pages. Limbs are tapered tubes whose
 * rings are laid out again as they grow, so every tip is pointed. Leaves are one instanced mesh;
 * each waits for its limb to grow past it. The number of branches follows the content.
 */
import {
  AdditiveBlending,
  BoxGeometry,
  BufferAttribute,
  BufferGeometry,
  CatmullRomCurve3,
  Color,
  CylinderGeometry,
  DoubleSide,
  EdgesGeometry,
  Euler,
  Float32BufferAttribute,
  Group,
  InstancedMesh,
  LineBasicMaterial,
  LineSegments,
  Mesh,
  MeshStandardMaterial,
  Object3D,
  PointLight,
  Points,
  PointsMaterial,
  PolarGridHelper,
  Quaternion,
  RepeatWrapping,
  Shape,
  ShapeGeometry,
  Sprite,
  SpriteMaterial,
  SphereGeometry,
  Vector3,
} from "three";
import { config, perTier, tokenColor } from "../config.ts";
import type { CameraPose, Scene, SceneContext } from "../scene.ts";

export interface TreeInput {
  /** How many milestones the programme has: one branch each. */
  milestones: number;
}

const clamp = (x: number, lo = 0, hi = 1) => Math.min(hi, Math.max(lo, x));
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const smooth = (x: number) => {
  const t = clamp(x);
  return t * t * (3 - 2 * t);
};
const UP = new Vector3(0, 1, 0);

/** A small seeded generator, so the leaves sit the same way on every visit. */
function seeded(seed: number): () => number {
  let a = seed;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Where up the trunk (0 to 1) branch i of n leaves it. */
export function branchHeight(i: number, n: number): number {
  const t = config.scenes.tree.branches;
  return t.from + t.span * (i / Math.max(1, n - 1));
}

/** The scroll progress at which branch i starts to grow. */
export function branchStart(i: number, n: number): number {
  const t = config.scenes.tree.branches;
  return t.start + t.startSpan * (i / Math.max(1, n - 1));
}

/** How grown the trunk is at this progress: it climbs to each branch's height as that branch starts. */
export function trunkGrowth(progress: number, n: number): number {
  const stops: [number, number][] = [[0, 0]];
  for (let i = 0; i < n; i++) stops.push([branchStart(i, n), branchHeight(i, n)]);
  stops.push([config.scenes.tree.branches.crownAt, 1]);
  for (let i = 1; i < stops.length; i++) {
    const [p, u] = stops[i]!;
    if (progress <= p) {
      const [p0, u0] = stops[i - 1]!;
      return lerp(u0, u, (progress - p0) / (p - p0));
    }
  }
  return 1;
}

interface Grower {
  /** How grown it is, 0 to 1; leaves read it. */
  g: number;
}

/** A tapered limb along a curve. Its rings are laid out again whenever the growth changes. */
class Limb implements Grower {
  g = -1;
  readonly curve: CatmullRomCurve3;
  readonly mesh: Mesh;
  twigs: Limb[] = [];
  node?: Mesh;
  private readonly centres: Vector3[] = [];
  private readonly normals: Vector3[] = [];
  private readonly binormals: Vector3[] = [];
  private readonly positions: Float32Array;
  private readonly geometry = new BufferGeometry();

  constructor(
    points: Vector3[],
    private readonly r0: number,
    private readonly r1: number,
    private readonly rings: number,
    private readonly sides: number,
    private readonly flare: number,
    material: MeshStandardMaterial,
    parent: Group,
  ) {
    this.curve = new CatmullRomCurve3(points, false, "catmullrom", 0.5);
    const tangents: Vector3[] = [];
    for (let k = 0; k <= rings; k++) {
      this.centres.push(this.curve.getPointAt(k / rings));
      tangents.push(this.curve.getTangentAt(k / rings));
    }
    // Parallel transport: carry a normal along the curve so the rings never twist.
    const t0 = tangents[0]!;
    const n0 = Math.abs(t0.y) < 0.9 ? new Vector3(0, 1, 0) : new Vector3(1, 0, 0);
    n0.sub(t0.clone().multiplyScalar(n0.dot(t0))).normalize();
    this.normals[0] = n0;
    this.binormals[0] = new Vector3().crossVectors(t0, n0);
    for (let k = 1; k <= rings; k++) {
      const axis = new Vector3().crossVectors(tangents[k - 1]!, tangents[k]!);
      const n = this.normals[k - 1]!.clone();
      if (axis.length() > 1e-6) n.applyAxisAngle(axis.normalize(), Math.acos(clamp(tangents[k - 1]!.dot(tangents[k]!), -1, 1)));
      this.normals[k] = n;
      this.binormals[k] = new Vector3().crossVectors(tangents[k]!, n);
    }
    const vertices = (rings + 1) * (sides + 1);
    this.positions = new Float32Array(vertices * 3);
    this.geometry.setAttribute("position", new BufferAttribute(this.positions, 3));
    const index: number[] = [];
    for (let k = 0; k < rings; k++) {
      for (let j = 0; j < sides; j++) {
        const a = k * (sides + 1) + j;
        const b = a + sides + 1;
        index.push(a, b, a + 1, a + 1, b, b + 1);
      }
    }
    this.geometry.setIndex(index);
    this.mesh = new Mesh(this.geometry, material);
    this.mesh.frustumCulled = false;
    this.mesh.visible = false;
    parent.add(this.mesh);
  }

  set(growth: number): void {
    const g = clamp(growth);
    if (Math.abs(g - this.g) < 4e-4 && !(g === 1 && this.g !== 1)) return;
    this.g = g;
    this.mesh.visible = g > 0.002;
    if (!this.mesh.visible) return;
    const { rings, sides, positions: p } = this;
    const reach = g * rings;
    let o = 0;
    for (let k = 0; k <= rings; k++) {
      const kk = Math.min(k, reach);
      const a = Math.min(rings, Math.floor(kk));
      const b = Math.min(rings, a + 1);
      const f = kk - a;
      const ca = this.centres[a]!;
      const cb = this.centres[b]!;
      const n = this.normals[a]!;
      const bn = this.binormals[a]!;
      const u = k / rings;
      let r = (this.r0 + (this.r1 - this.r0) * Math.pow(u, 0.85)) * (1 + this.flare * Math.exp(-u * 10));
      const tip = g > 0.999 ? 1 : clamp((reach - k) / 3);
      r *= tip * (2 - tip); // pointed while growing
      for (let j = 0; j <= sides; j++) {
        const th = (j / sides) * Math.PI * 2;
        const c = Math.cos(th) * r;
        const s = Math.sin(th) * r;
        p[o++] = lerp(ca.x, cb.x, f) + n.x * c + bn.x * s;
        p[o++] = lerp(ca.y, cb.y, f) + n.y * c + bn.y * s;
        p[o++] = lerp(ca.z, cb.z, f) + n.z * c + bn.z * s;
      }
    }
    this.geometry.attributes.position!.needsUpdate = true;
    this.geometry.computeVertexNormals();
  }
}

interface Leaf {
  owner: Grower;
  threshold: number;
  position: Vector3;
  rotation: Quaternion;
  size: number;
  phase: number;
}

function leafGeometry(): ShapeGeometry {
  const c = config.scenes.tree.leaf;
  const shape = new Shape();
  const n = 10;
  shape.moveTo(0, 0);
  for (let i = 1; i <= n; i++) {
    const t = i / n;
    shape.lineTo(c.width * Math.pow(Math.sin(Math.PI * Math.pow(t, 0.8)), 0.9), c.length * t);
  }
  for (let i = n - 1; i >= 1; i--) {
    const t = i / n;
    shape.lineTo(-c.width * Math.pow(Math.sin(Math.PI * Math.pow(t, 0.8)), 0.9), c.length * t);
  }
  const geometry = new ShapeGeometry(shape);
  const pos = geometry.attributes.position!;
  for (let v = 0; v < pos.count; v++) {
    const x = pos.getX(v);
    const y = pos.getY(v);
    pos.setZ(v, Math.abs(x) * 0.9 + y * y * 0.18); // cupped, like a real leaf
  }
  geometry.computeVertexNormals();
  return geometry;
}

export function createTree(ctx: SceneContext, input: TreeInput): Scene {
  const c = config.scenes.tree;
  const n = Math.max(1, Math.floor(input.milestones));
  const detail = perTier(c.detail, ctx.tier);
  const rand = seeded(11);
  const colour = (path: string) => tokenColor(path);

  const root = new Group();
  root.name = "tree";
  const world = new Group(); // everything that turns with the scroll
  root.add(world);

  // The stage: a faint polar grid under the book, and the lights that belong to this scene.
  const grid = new PolarGridHelper(c.stage.radius, 20, 14, 96, colour(c.stage.ring), colour(c.stage.spoke));
  grid.position.y = -0.2;
  const gridMaterial = grid.material as LineBasicMaterial;
  gridMaterial.transparent = true;
  gridMaterial.opacity = c.stage.opacity;
  root.add(grid);
  const key = new PointLight(colour(c.light.key), c.light.keyIntensity, c.light.distance);
  key.position.set(1.5, 4.5, 5);
  const back = new PointLight(colour(c.light.back), c.light.backIntensity, c.light.distance - 2);
  back.position.set(-4, 4, -4);
  const glow = new PointLight(colour(c.light.glow), 0, 9);
  glow.position.set(0, 0.9, 0);
  root.add(key, back);
  world.add(glow);

  // --- the book ---
  const { pageWidth: PW, pageDepth: PD, thickness: BT, segments: NX } = c.book;
  const profile = (x: number) => {
    const t = x / PW;
    return 0.3 + 0.1 * Math.sin(Math.PI * Math.min(1, t * 1.15)) - 0.16 * Math.exp(-t * 7);
  };
  const paper = ctx.textures.canvas(256, 256, (g, w, h) => {
    g.fillStyle = colour(c.book.paper);
    g.fillRect(0, 0, w, h);
    g.globalAlpha = 0.35;
    const shade = g.createLinearGradient(0, 0, w, 0);
    shade.addColorStop(0, colour(c.book.ink));
    shade.addColorStop(0.16, "transparent");
    g.fillStyle = shade;
    g.fillRect(0, 0, w, h);
    g.strokeStyle = colour(c.book.ink);
    g.globalAlpha = 0.3;
    g.lineWidth = 1.6;
    for (let y = 36; y < h - 20; y += 17) {
      g.beginPath();
      g.moveTo(34, y);
      g.lineTo(w - 26 - ((y * 7) % 40), y);
      g.stroke();
    }
    g.globalAlpha = 0.55;
    g.fillStyle = colour(c.book.rule);
    g.fillRect(34, 20, 70, 4);
  }, "colour");
  const edge = ctx.textures.canvas(8, 128, (g, w, h) => {
    g.fillStyle = colour(c.book.paperEdge);
    g.fillRect(0, 0, w, h);
    g.fillStyle = colour(c.book.ink);
    g.globalAlpha = 0.4;
    for (let y = 0; y < h; y += 4) g.fillRect(0, y, w, 1);
  }, "colour");
  edge.wrapS = edge.wrapT = RepeatWrapping;
  const paperMaterial = new MeshStandardMaterial({ map: paper, roughness: 0.9, metalness: 0, envMapIntensity: 0.35, side: DoubleSide, emissive: colour(c.book.glow), emissiveIntensity: 0 });
  const edgeMaterial = new MeshStandardMaterial({ map: edge, roughness: 0.9, metalness: 0, envMapIntensity: 0.35, side: DoubleSide });
  const coverMaterial = new MeshStandardMaterial({ color: colour(c.book.cover), roughness: 0.55, metalness: 0.45, envMapIntensity: 0.9 });
  const gold = colour(c.gold);

  const surface = (build: (pos: number[], uv: number[], idx: number[]) => void) => {
    const pos: number[] = [];
    const uv: number[] = [];
    const idx: number[] = [];
    build(pos, uv, idx);
    const g = new BufferGeometry();
    g.setAttribute("position", new Float32BufferAttribute(pos, 3));
    g.setAttribute("uv", new Float32BufferAttribute(uv, 2));
    g.setIndex(idx);
    g.computeVertexNormals();
    return g;
  };
  const bookHalf = () => {
    const half = new Group();
    const top = surface((pos, uv, idx) => {
      for (let i = 0; i <= NX; i++) {
        const x = (PW * i) / NX;
        for (let j = 0; j <= 1; j++) {
          pos.push(x, profile(x), (j - 0.5) * PD);
          uv.push(i / NX, j);
        }
      }
      for (let i = 0; i < NX; i++) {
        const a = i * 2;
        idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2);
      }
    });
    half.add(new Mesh(top, paperMaterial));
    for (const side of [-1, 1]) {
      const wall = surface((pos, uv, idx) => {
        for (let i = 0; i <= NX; i++) {
          const x = (PW * i) / NX;
          pos.push(x, 0, (side * PD) / 2, x, profile(x), (side * PD) / 2);
          uv.push(i / NX, 0, i / NX, 1);
        }
        for (let i = 0; i < NX; i++) {
          const a = i * 2;
          idx.push(a, a + 2, a + 1, a + 1, a + 2, a + 3);
        }
      });
      half.add(new Mesh(wall, edgeMaterial));
    }
    const end = surface((pos, uv, idx) => {
      const h = profile(PW);
      pos.push(PW, 0, -PD / 2, PW, 0, PD / 2, PW, h, -PD / 2, PW, h, PD / 2);
      uv.push(0, 0, 1, 0, 0, 1, 1, 1);
      idx.push(0, 1, 2, 1, 3, 2);
    });
    half.add(new Mesh(end, edgeMaterial));
    const cover = new Mesh(new BoxGeometry(PW + 0.16, BT, PD + 0.16), coverMaterial);
    cover.position.set((PW + 0.16) / 2 - 0.06, -BT / 2, 0);
    const trim = new LineSegments(new EdgesGeometry(cover.geometry), new LineBasicMaterial({ color: gold }));
    trim.position.copy(cover.position);
    half.add(cover, trim);
    return half;
  };
  const bookRight = new Group();
  const bookLeft = new Group();
  bookRight.add(bookHalf());
  const mirrored = bookHalf();
  mirrored.scale.x = -1;
  bookLeft.add(mirrored);
  world.add(bookRight, bookLeft);
  const spine = new Mesh(new CylinderGeometry(0.1, 0.1, PD + 0.16, 14), new MeshStandardMaterial({ color: gold, metalness: 1, roughness: 0.3 }));
  spine.rotation.x = Math.PI / 2;
  spine.position.set(0, -0.045, 0);
  world.add(spine);

  const dot = ctx.textures.canvas(64, 64, (g, w, h) => {
    const r = g.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, w / 2);
    r.addColorStop(0, "rgba(255, 255, 255, 1)");
    r.addColorStop(0.35, "rgba(255, 255, 255, 0.45)");
    r.addColorStop(1, "rgba(255, 255, 255, 0)");
    g.fillStyle = r;
    g.fillRect(0, 0, w, h);
  }, "colour");
  const glowSprite = (path: string, size: number) => {
    const sprite = new Sprite(new SpriteMaterial({ map: dot, color: colour(path), transparent: true, opacity: 0, blending: AdditiveBlending, depthWrite: false }));
    sprite.scale.set(size, size, 1);
    return sprite;
  };
  const gutterGlow = glowSprite(c.light.glow, 3.2);
  gutterGlow.scale.set(3.2, 1.6, 1);
  gutterGlow.position.set(0, 0.35, 0);
  world.add(gutterGlow);

  // --- limbs, leaves ---
  const bark = new MeshStandardMaterial({ color: colour(c.bark), roughness: 0.5, metalness: 0.55, envMapIntensity: 0.9 });
  const limb = (pts: Vector3[], r0: number, r1: number, rings: number, sides: number, flare: number) => new Limb(pts, r0, r1, rings, sides, flare, bark, world);
  const trunkHeight = c.trunk.height;
  const trunk = new Limb(
    c.trunk.points.map(([x, y, z]) => new Vector3(x, y, z)),
    c.trunk.base, c.trunk.tip, detail.trunkRings, detail.trunkSides, c.trunk.flare, bark, world,
  );

  const leaves: Leaf[] = [];
  const palette = c.leaf.colours.map(colour);
  const leafMesh = new InstancedMesh(leafGeometry(), new MeshStandardMaterial({ color: 0xffffff, metalness: 0.5, roughness: 0.5, side: DoubleSide, envMapIntensity: 0.75 }), c.leaf.max);
  leafMesh.frustumCulled = false;
  world.add(leafMesh);
  const scratch = new Color();
  const addLeaf = (owner: Grower, threshold: number, pos: Vector3, dir: Vector3, size: number) => {
    if (leaves.length >= c.leaf.max) return;
    const q = new Quaternion().setFromUnitVectors(UP, dir.clone().normalize());
    q.multiply(new Quaternion().setFromAxisAngle(UP, rand() * 6.28));
    leaves.push({ owner, threshold, position: pos.clone(), rotation: q, size: size * (0.8 + rand() * 0.45), phase: rand() * 6.28 });
    const pick = rand() < 0.2 ? palette.length - 1 : Math.floor(rand() * (palette.length - 1));
    leafMesh.setColorAt(leaves.length - 1, scratch.set(palette[pick]!));
  };
  const limbLeaves = (l: Limb, from: number, to: number, count: number, size: number, lift = 0.35) => {
    for (let i = 0; i < count; i++) {
      const tp = from + ((to - from) * (i + rand() * 0.5)) / count;
      const centre = l.curve.getPointAt(tp);
      const tangent = l.curve.getTangentAt(tp);
      const perp = new Vector3(rand() - 0.5, rand() * 0.4 - 0.2, rand() - 0.5).normalize();
      const dir = tangent.clone().multiplyScalar(0.5).add(perp.multiplyScalar(0.9)).add(new Vector3(0, lift, 0));
      addLeaf(l, Math.min(0.995, tp + 0.04), centre, dir, size);
    }
  };
  const tipFan = (l: Limb, count: number, size: number) => {
    const tip = l.curve.getPointAt(1);
    const tangent = l.curve.getTangentAt(1);
    const p1 = new Vector3().crossVectors(tangent, UP).normalize();
    const p2 = new Vector3().crossVectors(tangent, p1).normalize();
    for (let k = 0; k < count; k++) {
      const f = k === 0 ? 0 : 0.55 + (k % 2) * 0.25;
      const az = k * 2.4;
      const dir = tangent.clone().multiplyScalar(Math.cos(f)).add(p1.clone().multiplyScalar(Math.sin(f) * Math.cos(az))).add(p2.clone().multiplyScalar(Math.sin(f) * Math.sin(az)));
      addLeaf(l, 0.97, tip, dir, size * 1.1);
    }
  };

  // --- one branch per milestone, spiralling round the trunk ---
  const nodeMaterial = () => new MeshStandardMaterial({ color: colour(c.gold), emissive: colour(c.light.glow), emissiveIntensity: 0, metalness: 0.8, roughness: 0.28 });
  const branches = Array.from({ length: n }, (_, bi) => {
    const u = branchHeight(bi, n);
    const start = trunk.curve.getPointAt(u);
    const az = bi * c.branches.spiral + 0.5;
    const d = new Vector3(Math.cos(az), 0, Math.sin(az));
    const reach = c.branches.reach - u * c.branches.reachShrink;
    const branch = limb(
      [
        start.clone(),
        start.clone().add(d.clone().multiplyScalar(reach * 0.3)).add(new Vector3(0, 0.14, 0)),
        start.clone().add(d.clone().multiplyScalar(reach * 0.7)).add(new Vector3(0, 0.55, 0)),
        start.clone().add(d.clone().multiplyScalar(reach)).add(new Vector3(0, 0.85 + rand() * 0.25, 0)),
      ],
      c.branches.radius - u * 0.025, 0.012, detail.branchRings, 7, 0.1,
    );
    for (const [at, turn] of [[0.5, 0.7], [0.78, -0.75]] as const) {
      const p = branch.curve.getPointAt(at);
      const a2 = az + turn;
      const d2 = new Vector3(Math.cos(a2), 0, Math.sin(a2));
      const len = reach * (0.42 - (turn < 0 ? 0.06 : 0));
      const twig = limb(
        [p.clone(), p.clone().add(d2.clone().multiplyScalar(len * 0.4)).add(new Vector3(0, 0.22, 0)), p.clone().add(d2.clone().multiplyScalar(len)).add(new Vector3(0, 0.62, 0))],
        0.026, 0.008, detail.twigRings, 6, 0,
      );
      branch.twigs.push(twig);
      limbLeaves(twig, 0.35, 1, 4, 0.9);
      tipFan(twig, 4, 0.9);
    }
    limbLeaves(branch, 0.45, 1, 4, 1);
    tipFan(branch, 7, 1.1);
    const node = new Mesh(new SphereGeometry(0.085, 16, 12), nodeMaterial());
    node.position.copy(branch.curve.getPointAt(1));
    node.scale.setScalar(0.001);
    world.add(node);
    branch.node = node;
    return { branch, start: branchStart(bi, n) };
  });

  limbLeaves(trunk, 0.72, 0.98, 6, 1.1);
  const crown: Grower = { g: 0 };
  const top = trunk.curve.getPointAt(1);
  (c.crown.rings as [number, number, number][]).forEach(([count, lift, size], wi) => {
    for (let k = 0; k < count; k++) {
      const a = (k / count) * Math.PI * 2 + wi * 0.4;
      const dir = new Vector3(Math.cos(a) * Math.cos(lift), Math.sin(lift), Math.sin(a) * Math.cos(lift));
      addLeaf(crown, 0.02 + wi * 0.18 + k * 0.004, top.clone().add(dir.clone().multiplyScalar(0.1)), dir, size);
    }
  });
  const finial = new Mesh(new SphereGeometry(0.1, 20, 14), new MeshStandardMaterial({ color: colour(c.book.glow), emissive: colour(c.light.glow), emissiveIntensity: 1.4, metalness: 0.5, roughness: 0.25 }));
  finial.position.copy(top).add(new Vector3(0, 0.18, 0));
  finial.scale.setScalar(0.001);
  const finialGlow = glowSprite(c.light.glow, 1.8);
  finialGlow.position.copy(finial.position);
  world.add(finial, finialGlow);

  // --- laurel sprigs round the book, like the sprigs either side of the medal ---
  const laurel = [-1, 1].map((side) => {
    const pts: Vector3[] = [];
    for (let a = 0; a <= 7; a++) {
      const th = ((36 + a * 16) * Math.PI) / 180;
      pts.push(new Vector3(side * Math.sin(th) * 3.2, 0.03 + a * 0.012, Math.cos(th) * 3));
    }
    const sprig = limb(pts, 0.032, 0.012, detail.laurelRings, 6, 0);
    for (let i = 0; i < 14; i++) {
      const tp = (i + 0.4) / 14;
      const centre = sprig.curve.getPointAt(tp);
      const tangent = sprig.curve.getTangentAt(tp);
      const outward = new Vector3(centre.x, 0, centre.z).normalize();
      for (const sg of [1, -1]) addLeaf(sprig, tp, centre, tangent.clone().multiplyScalar(0.7).add(outward.clone().multiplyScalar(sg * 0.8)).add(new Vector3(0, 0.45, 0)), 0.95);
    }
    return sprig;
  });
  if (leafMesh.instanceColor) leafMesh.instanceColor.needsUpdate = true;

  // --- motes of light lifting off the pages ---
  const moteCount = detail.motes;
  const motePositions = new Float32Array(moteCount * 3);
  const seeds = Array.from({ length: moteCount }, () => ({ a: rand() * 6.28, r: 0.15 + rand() * 1.8, v: 0.18 + rand() * 0.35, o: rand() * trunkHeight }));
  const moteGeometry = new BufferGeometry();
  moteGeometry.setAttribute("position", new BufferAttribute(motePositions, 3));
  const motes = new Points(moteGeometry, new PointsMaterial({ map: dot, color: colour(c.light.glow), size: 0.13, transparent: true, opacity: 0, blending: AdditiveBlending, depthWrite: false }));
  motes.frustumCulled = false;
  world.add(motes);

  // --- the scene ---
  const euler = new Euler();
  const sway = new Quaternion();
  const instance = new Object3D();
  const camera = c.camera as CameraPose;
  let target = 0;
  let shown = 0;
  let turned = c.turn.from;
  let pointer = 0;
  let last: number | null = null;
  let opened: number | null = null;

  const scene: Scene = {
    root,
    halfWidth: c.halfWidth,
    halfHeight: c.halfHeight,
    cameraAt: () => camera,
    setProgress(progress) {
      target = clamp(progress);
    },
    setPointer(x) {
      pointer = x;
    },
    update(timeMs) {
      const time = timeMs / 1000;
      const dt = last === null ? 0 : Math.min(0.1, (timeMs - last) / 1000);
      last = timeMs;
      shown += (target - shown) * (1 - Math.exp(-dt * 6));
      if (opened === null) opened = timeMs;
      const open = Math.min(1, (timeMs - opened) / c.book.openMs);
      const eased = 1 - Math.pow(1 - open, 3);
      const angle = lerp(3.05, 0.07, eased);
      const closed = clamp((angle - 0.07) / 2.98);
      bookRight.rotation.z = angle;
      bookRight.position.y = 0.62 * closed;
      bookLeft.rotation.z = -0.07;
      turned += (lerp(c.turn.from, c.turn.to, shown) + pointer * 0.22 - turned) * (1 - Math.exp(-dt * 3));
      world.rotation.y = turned;

      const growth = trunkGrowth(shown, n) * open;
      trunk.set(growth);
      branches.forEach(({ branch, start }) => {
        const g = smooth((shown - start) / 0.08);
        branch.set(g);
        branch.twigs.forEach((t) => t.set(clamp((g - 0.4) / 0.6)));
        const lit = smooth((g - 0.9) / 0.1);
        const node = branch.node!;
        node.scale.setScalar(lit);
        const material = node.material as MeshStandardMaterial;
        material.emissiveIntensity += ((lit > 0.9 ? 0.35 : 0) - material.emissiveIntensity) * 0.15;
      });
      laurel.forEach((l) => l.set(smooth(shown / 0.2) * eased));
      crown.g = clamp((shown - c.branches.crownAt + 0.04) / 0.08);
      const fin = smooth((shown - 0.94) / 0.06);
      finial.scale.setScalar(fin * (1 + Math.sin(time * 3) * 0.12));
      (finialGlow.material as SpriteMaterial).opacity = fin * (0.55 + Math.sin(time * 2.4) * 0.12);
      const lightUp = clamp(shown * 6) * open;
      paperMaterial.emissiveIntensity = 0.28 * lightUp + 0.1 * Math.sin(time * 1.7) * lightUp;
      glow.intensity = 1.6 * lightUp;
      (gutterGlow.material as SpriteMaterial).opacity = 0.55 * lightUp;

      leaves.forEach((leaf, i) => {
        const size = leaf.size * 1.35 * smooth((leaf.owner.g - leaf.threshold) / 0.16);
        euler.set(Math.sin(time * 1.1 + leaf.phase) * 0.08, 0, Math.cos(time * 0.9 + leaf.phase * 1.3) * 0.08);
        sway.setFromEuler(euler);
        instance.position.copy(leaf.position);
        instance.quaternion.copy(leaf.rotation).multiply(sway);
        instance.scale.setScalar(size < 0.002 ? 0.0001 : size);
        instance.updateMatrix();
        leafMesh.setMatrixAt(i, instance.matrix);
      });
      leafMesh.count = leaves.length;
      leafMesh.instanceMatrix.needsUpdate = true;

      (motes.material as PointsMaterial).opacity = 0.9 * clamp(shown * 5) * open;
      const span = growth * trunkHeight + 0.8;
      seeds.forEach((s, m) => {
        const y = (time * s.v + s.o) % span;
        const radius = s.r * (0.3 + (y / span) * 0.9);
        motePositions[m * 3] = Math.cos(s.a + time * 0.2) * radius;
        motePositions[m * 3 + 1] = 0.3 + y;
        motePositions[m * 3 + 2] = Math.sin(s.a + time * 0.2) * radius;
      });
      moteGeometry.attributes.position!.needsUpdate = true;
      return true; // the motes and the leaves move for as long as it is on screen
    },
  };
  scene.update(0);
  return scene;
}
