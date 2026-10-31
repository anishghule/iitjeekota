import { describe, expect, it } from "vitest";
import { Color, InstancedMesh, Mesh, MeshPhysicalMaterial, Texture } from "three";
import { tokens } from "@dsap/tokens";
import syllabus from "../../content/syllabus.json";
import kotaSystem from "../../content/blocks/en/kota-system.json";
import {
  config,
  createKotaPrism,
  createMedal,
  createSpecimens,
  createSyllabusSlab,
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
  chapters: syllabus.chapters.map((c) => ({ id: c.id, subject: c.subject, symbol: c.symbol, classes: c.classes, main: c.main })),
};

const scenes: Record<string, (ctx: SceneContext) => Scene> = {
  medal: (ctx) => createMedal(ctx, { faceUrl: "face.png", normalUrl: "normal.webp" }),
  "kota-prism": (ctx) => createKotaPrism(ctx, { points }),
  "syllabus-slab": (ctx) => createSyllabusSlab(ctx, slabInput),
  specimens: (ctx) => createSpecimens(ctx),
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
    scene.setProgress(0.45);
    expect(scene.root.position.length()).toBeCloseTo(0);
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
