import { describe, expect, it } from "vitest";
import { Color, InstancedMesh, Mesh, MeshPhysicalMaterial, Texture, type PointLight } from "three";
import { tokens } from "@dsap/tokens";
import syllabus from "../../content/syllabus.json";
import kotaSystem from "../../content/blocks/en/kota-system.json";
import {
  config,
  createKotaPrism,
  createMedal,
  createSpecimens,
  createRoute,
  routeDrawn,
  terrainHeight,
  createSyllabusSlab,
  createTree,
  branchHeight,
  branchStart,
  trunkGrowth,
  dustPositions,
  railAt,
  railOpacity,
  fitWidth,
  plateArrival,
  plateFacing,
  qualityTier,
  sceneStats,
  slabLayout,
  topView,
  type RenderTier,
  type Scene,
  type SceneContext,
  type SlabInput,
} from "../src/index.ts";

const stubTextures = { image: () => new Texture(), canvas: () => new Texture() };
const context = (tier: RenderTier): SceneContext => ({ tier, textures: stubTextures });
const points = kotaSystem.points.map((p) => (typeof p === "string" ? p : p.text));
const slabInput: SlabInput = {
  subjects: syllabus.subjects.map((s) => s.id),
  chapters: syllabus.chapters.map((c) => ({ id: c.id, subject: c.subject, label: c.names.en.slice(0, 2), classes: c.classes, main: c.main })),
};

const scenes: Record<string, (ctx: SceneContext) => Scene> = {
  medal: (ctx) => createMedal(ctx, { faceUrl: "face.png", normalUrl: "normal.webp" }),
  "kota-prism": (ctx) => createKotaPrism(ctx, { points }),
  "syllabus-slab": (ctx) => createSyllabusSlab(ctx, slabInput),
  specimens: (ctx) => createSpecimens(ctx),
  route: (ctx) => createRoute(ctx, { kota: "Kota", pune: "Pune" }),
};

describe("budgets", () => {
  for (const [name, create] of Object.entries(scenes)) {
    for (const tier of ["full", "lite"] as const) {
      it(`${name} stays within its ${tier} budget`, () => {
        const budget = config.scenes[name as keyof typeof config.scenes].budget;
        const stats = sceneStats(create(context(tier)).root);
        expect(stats.triangles).toBeLessThanOrEqual(budget.triangles[tier]);
        expect(stats.drawCalls).toBeLessThanOrEqual(budget.drawCalls);
      });
    }
  }

  it("the lite tier is lighter where detail is set per tier", () => {
    const full = sceneStats(scenes.medal!(context("full")).root).triangles;
    const lite = sceneStats(scenes.medal!(context("lite")).root).triangles;
    expect(lite).toBeLessThan(full);
  });
});

describe("shapes follow the content", () => {
  it("the Kota prism has one plate per point of the Kota system", () => {
    const scene = createKotaPrism(context("full"), { points });
    const named = [] as string[];
    scene.root.traverse((o) => o.name.startsWith("plate-") && named.push(o.name));
    expect(named).toHaveLength(points.length);
  });

  it("a sixth point would make a hexagon, and fewer than three is refused", () => {
    const six = createKotaPrism(context("lite"), { points: [...points, "one more"] });
    const named = [] as string[];
    six.root.traverse((o) => o.name.startsWith("plate-") && named.push(o.name));
    expect(named).toHaveLength(points.length + 1);
    expect(() => createKotaPrism(context("lite"), { points: ["a", "b"] })).toThrow();
  });

  it("the plates fly in one after another and have all landed when the assembly ends", () => {
    const { until, stagger } = config.scenes["kota-prism"].assemble;
    expect(plateArrival(0, 0, 5, stagger)).toBe(0);
    expect(plateArrival(0.3, 0, 5, stagger)).toBeGreaterThan(plateArrival(0.3, 4, 5, stagger));
    for (let i = 0; i < 5; i++) expect(plateArrival(1, i, 5, stagger)).toBe(1);

    const scene = createKotaPrism(context("lite"), { points });
    const distanceOf = (name: string) => {
      const plate = scene.root.getObjectByName(name)!;
      return Math.hypot(plate.position.x, plate.position.z);
    };
    scene.setProgress(0);
    const scattered = distanceOf("plate-0");
    scene.setProgress(until);
    expect(scattered).toBeGreaterThan(distanceOf("plate-0") + 1);
    scene.setProgress(1);
    expect(distanceOf("plate-0")).toBeCloseTo(distanceOf("plate-1"), 5);
  });

  it("on a narrow screen the camera moves back until the prism fits across", () => {
    const pose = { position: [0, 1.2, 8.2] as [number, number, number], target: [0, 0, 0] as [number, number, number] };
    expect(fitWidth(pose, 2.5, 1.6)).toEqual(pose); // wide: unchanged
    const narrow = fitWidth(pose, 2.5, 0.5);
    const away = Math.hypot(...narrow.position);
    expect(away).toBeGreaterThan(Math.hypot(...pose.position));
    const halfAcross = Math.tan(((config.renderer.fov / 2) * Math.PI) / 180) * 0.5 * away;
    expect(halfAcross).toBeCloseTo(2.5, 5);
  });

  it("each step of the prism brings the next plate to the front", () => {
    const n = points.length;
    expect(plateFacing(0, n)).toBeCloseTo(-Math.PI / n);
    expect(plateFacing(1, n) - plateFacing(0, n)).toBeCloseTo((-2 * Math.PI) / n);
  });

  it("the syllabus slab has one tile per chapter", () => {
    const scene = createSyllabusSlab(context("full"), slabInput);
    const instanced: InstancedMesh[] = [];
    scene.root.traverse((o) => o instanceof InstancedMesh && instanced.push(o));
    expect(instanced.map((m) => m.count)).toEqual([syllabus.chapters.length, syllabus.chapters.length]);
  });
});

describe("the syllabus layout", () => {
  const { tiles } = slabLayout(slabInput);
  const size = config.scenes["syllabus-slab"].tile.size;

  it("never overlaps two tiles", () => {
    for (let i = 0; i < tiles.length; i++) {
      for (let j = i + 1; j < tiles.length; j++) {
        const a = tiles[i]!;
        const b = tiles[j]!;
        const apart = Math.abs(a.x - b.x) >= size || Math.abs(a.z - b.z) >= size;
        expect(apart, `${a.id} and ${b.id}`).toBe(true);
      }
    }
  });

  it("puts subjects left to right and JEE Advanced only chapters in rows below their block", () => {
    const at = (id: string) => tiles.find((t) => t.id === id)!;
    expect(at("p-units").x).toBeLessThan(at("c-basic-concepts").x);
    expect(at("c-basic-concepts").x).toBeLessThan(at("m-sets").x);
    const chemistryMain = tiles.filter((t) => t.id.startsWith("c-") && !t.detached);
    const detached = tiles.filter((t) => t.detached);
    expect(detached.map((t) => t.id).sort()).toEqual(syllabus.chapters.filter((c) => c.main === null).map((c) => c.id).sort());
    expect(Math.min(...detached.map((t) => t.z))).toBeGreaterThan(Math.max(...chemistryMain.map((t) => t.z)));
  });
});

describe("the syllabus camera", () => {
  const visible = (height: number, aspect: number) => {
    const depth = 2 * height * Math.tan(((config.renderer.fov / 2) * Math.PI) / 180);
    return { width: depth * aspect, depth };
  };

  for (const [shape, aspect] of [["a wide desktop", 16 / 10], ["a tall phone", 9 / 19.5]] as const) {
    it(`frames the whole slab from above on ${shape}`, () => {
      const fit = config.scenes["syllabus-slab"].camera.to.fit;
      const pose = topView(32, 9, aspect, fit);
      const seen = visible(pose.position[1], aspect);
      expect(seen.width).toBeGreaterThanOrEqual(32);
      expect(seen.depth).toBeGreaterThanOrEqual(9);
      expect(Math.min(32 / seen.width, 9 / seen.depth)).toBeLessThanOrEqual(fit + 1e-9);
      expect(Math.max(32 / seen.width, 9 / seen.depth)).toBeCloseTo(fit);
    });
  }

  it("ends straight above whatever the progress started from", () => {
    const scene = createSyllabusSlab(context("lite"), slabInput);
    const end = scene.cameraAt(1, 16 / 10);
    expect(end.target).toEqual([0, 0, 0]);
    expect(end.position[0]).toBeCloseTo(0);
  });
});

describe("materials and motion", () => {
  it("the medal face takes its finish from the tokens", () => {
    const scene = createMedal(context("full"), { faceUrl: "f", normalUrl: "n" });
    const coin = scene.root.getObjectByName("coin") as Mesh;
    const face = (coin.material as MeshPhysicalMaterial[])[1]!;
    expect(face.metalness).toBe(tokens.material["medal-face"].metalness);
    expect(face.color.getHexString()).toBe(new Color(tokens.material["medal-face"].color).getHexString());
  });

  it("glass is see-through on every tier, without a refraction pass", () => {
    for (const tier of ["full", "lite"] as const) {
      const scene = createSpecimens(context(tier));
      const glass: MeshPhysicalMaterial[] = [];
      scene.root.traverse((o) => o instanceof Mesh && (o.material as MeshPhysicalMaterial).transparent && glass.push(o.material as MeshPhysicalMaterial));
      expect(glass.length).toBeGreaterThan(0);
      expect(glass.every((m) => m.transmission === 0 && m.opacity === tokens.material.glass.opacity)).toBe(true);
    }
  });

  it("the medal moves with progress and holds its keyframes at the ends", () => {
    const scene = createMedal(context("lite"), { faceUrl: "f", normalUrl: "n" });
    const [first] = config.scenes.medal.keyframes;
    scene.setProgress(0);
    expect(scene.root.position.toArray()).toEqual(first!.position);
    // Once it has spun in and settled, scrolling carries it through its keyframes.
    scene.update(0);
    scene.update(config.scenes.medal.intro.ms + 1);
    scene.setProgress(0.45);
    expect(scene.root.position.length()).toBeCloseTo(0);
  });

  it("spins in on arrival and is facing the reader once it has settled", () => {
    const scene = createMedal(context("lite"), { faceUrl: "f", normalUrl: "n" });
    scene.setProgress(0.45);
    scene.update(0);
    const turning = Math.abs(scene.root.rotation.y);
    expect(turning).toBeGreaterThan(1);
    scene.update(config.scenes.medal.intro.ms + 1);
    expect(Math.abs(scene.root.rotation.y)).toBeLessThan(turning);
    expect(scene.root.rotation.y).toBeCloseTo(0);
  });
});

describe("quality tiers", () => {
  const strong = { reducedMotion: false, saveData: false, webgl2: true, cores: 8, memoryGb: 8 };
  it("gives full 3D to strong devices, lite to modest ones and a still image when asked or unable", () => {
    expect(qualityTier(strong)).toBe("full");
    expect(qualityTier({ ...strong, cores: 4 })).toBe("lite");
    expect(qualityTier({ ...strong, memoryGb: 2 })).toBe("lite");
    expect(qualityTier({ ...strong, reducedMotion: true })).toBe("still");
    expect(qualityTier({ ...strong, saveData: true })).toBe("still");
    expect(qualityTier({ ...strong, webgl2: false })).toBe("still");
  });
});

/** Runs the tree's clock until it has settled at this progress, as the page would over a second or two of scrolling. */
function grown(milestones: number, progress: number, tier: RenderTier = "full") {
  const tree = createTree(context(tier), { milestones });
  tree.setProgress(progress);
  for (let t = 0; t <= 6000; t += 100) tree.update(t);
  return tree;
}

describe("the journey tree", () => {
  it("staggers its branches up the trunk, each starting after the one below", () => {
    for (let i = 1; i < 8; i++) {
      expect(branchHeight(i, 8)).toBeGreaterThan(branchHeight(i - 1, 8));
      expect(branchStart(i, 8)).toBeGreaterThan(branchStart(i - 1, 8));
    }
  });

  it("grows the trunk to each branch as that branch starts, and to the top at the crown", () => {
    expect(trunkGrowth(0, 8)).toBe(0);
    expect(trunkGrowth(branchStart(3, 8), 8)).toBeCloseTo(branchHeight(3, 8));
    expect(trunkGrowth(1, 8)).toBe(1);
  });

  it("is bare at the start and full at the end, within its budget", () => {
    // Limbs that have not started to grow are hidden, so a bare tree draws far fewer meshes than a full one.
    const bare = sceneStats(grown(8, 0).root).drawCalls;
    const full = sceneStats(grown(8, 1).root).drawCalls;
    expect(full).toBeGreaterThan(bare + 20);
    for (const tier of ["full", "lite"] as const) {
      const stats = sceneStats(grown(8, 1, tier).root);
      expect(stats.triangles).toBeLessThanOrEqual(config.scenes.tree.budget.triangles[tier]);
      expect(stats.drawCalls).toBeLessThanOrEqual(config.scenes.tree.budget.drawCalls);
    }
  });

  it("has a branch for each milestone", () => {
    const few = sceneStats(grown(3, 1).root).drawCalls;
    const many = sceneStats(grown(8, 1).root).drawCalls;
    expect(many).toBeGreaterThan(few);
  });
});

describe("the camera rail", () => {
  const sections = [{ start: 0, end: 1000 }, { start: 1000, end: 3000 }, { start: 5000, end: 6600 }];

  it("dwells on a scene while its section holds the screen", () => {
    expect(railAt(sections, 0, 800)).toMatchObject({ from: 0, to: 0 });
    expect(railAt(sections, 1500, 800)).toMatchObject({ from: 1, to: 1 });
  });

  it("travels to the next scene over the scroll between two dwells, and arrives when its section reaches the top", () => {
    const mid = railAt(sections, 3600, 800);
    expect(mid).toMatchObject({ from: 1, to: 2 });
    expect(mid.t).toBeGreaterThan(0);
    expect(mid.t).toBeLessThan(1);
    expect(railAt(sections, 4999, 800).t).toBeCloseTo(1, 1);
    expect(railAt(sections, 5000, 800)).toMatchObject({ from: 2, to: 2 });
  });

  it("keeps the canvas full between adjacent sections and hides it over plain content", () => {
    expect(railOpacity(sections, 500, 800)).toBe(1);
    expect(railOpacity(sections, 3300, 800)).toBe(0);
    expect(railOpacity(sections, 4600, 800)).toBeCloseTo(0.5);
  });
});

describe("the dust", () => {
  it("is the same on every visit and stays within the world", () => {
    const a = dustPositions(50, 3, 7);
    expect(Array.from(dustPositions(50, 3, 7))).toEqual(Array.from(a));
    expect(Math.max(...Array.from(a).filter((_, i) => i % 3 === 0).map(Math.abs))).toBeLessThanOrEqual(config.world.dust.width);
  });
});

describe("the Kota to Pune route", () => {
  it("draws from nothing to the whole route as the section scrolls", () => {
    expect(routeDrawn(0)).toBe(0);
    expect(routeDrawn(0.5)).toBeGreaterThan(0.2);
    expect(routeDrawn(0.5)).toBeLessThan(0.8);
    expect(routeDrawn(1)).toBe(1);
  });

  it("is the same land on every visit: a ridge between the cities, plains by Kota, nothing at the edge", () => {
    const t = config.scenes.route.terrain;
    expect(terrainHeight(1, 1)).toBe(terrainHeight(1, 1));
    expect(terrainHeight(t.ridge.at, 0)).toBeGreaterThan(terrainHeight(-6, 0));
    expect(terrainHeight(t.halfWidth, 0)).toBe(0);
    expect(terrainHeight(0, t.halfDepth)).toBe(0);
  });

  it("lights the house, and the ground round it, only once the route has arrived", () => {
    const scene = createRoute(context("full"), { kota: "Kota", pune: "Pune" });
    const light = () => {
      let intensity = -1;
      scene.root.traverse((o) => "isPointLight" in o && (intensity = (o as PointLight).intensity));
      return intensity;
    };
    scene.setProgress(0.5);
    expect(light()).toBe(0);
    scene.setProgress(1);
    expect(light()).toBeGreaterThan(0);
  });

  it("is within its budget", () => {
    for (const tier of ["full", "lite"] as const) {
      const stats = sceneStats(createRoute(context(tier), { kota: "Kota", pune: "Pune" }).root);
      expect(stats.triangles).toBeLessThanOrEqual(config.scenes.route.budget.triangles[tier]);
    }
  });
});
