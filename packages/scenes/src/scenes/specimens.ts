/**
 * Three specimens in glass cases on brass bases, one per subject: a swinging pendulum (Physics),
 * a benzene ring (Chemistry) and a surface plot (Mathematics). Used in the syllabus opening and as
 * the header mark of the chapter panel (docs/design/syllabus-table.md).
 *
 * Repeated parts (cases, bases, atoms, bonds) are instanced: one draw call per kind, however many.
 */
import {
  BoxGeometry,
  CylinderGeometry,
  DoubleSide,
  Group,
  InstancedMesh,
  Matrix4,
  Mesh,
  PlaneGeometry,
  Quaternion,
  SphereGeometry,
  Vector3,
  type BufferGeometry,
  type Material,
} from "three";
import { config, perTier } from "../config.ts";
import { material } from "../materials.ts";
import type { CameraPose, Scene, SceneContext } from "../scene.ts";

const UP = new Vector3(0, 1, 0);

/** One draw call for many copies of a part, each placed by its own matrix. */
function instanced(geometry: BufferGeometry, mat: Material, matrices: Matrix4[]): InstancedMesh {
  const mesh = new InstancedMesh(geometry, mat, matrices.length);
  matrices.forEach((m, i) => mesh.setMatrixAt(i, m));
  mesh.instanceMatrix.needsUpdate = true;
  return mesh;
}

/** Places a unit-height cylinder between two points. */
function between(from: Vector3, to: Vector3): Matrix4 {
  const direction = to.clone().sub(from);
  const rotation = new Quaternion().setFromUnitVectors(UP, direction.clone().normalize());
  const middle = from.clone().add(to).multiplyScalar(0.5);
  return new Matrix4().compose(middle, rotation, new Vector3(1, direction.length(), 1));
}

const at = (x: number, y: number, z: number) => new Matrix4().makeTranslation(x, y, z);

export function createSpecimens(ctx: SceneContext): Scene {
  const c = config.scenes.specimens;
  const { tier } = ctx;
  const seg = perTier(c.sphereSegments, tier);
  const root = new Group();
  root.name = "specimens";
  const brass = material("brass");
  const polished = material("brass-polished");

  const centres = [-1, 0, 1].map((k) => k * c.case.spacing);
  root.add(
    instanced(new BoxGeometry(c.case.width * 1.08, c.case.base, c.case.depth * 1.08), brass,
      centres.map((x) => at(x, -c.case.height / 2 - c.case.base / 2, 0))),
    instanced(new BoxGeometry(c.case.width, c.case.height, c.case.depth), material("glass"),
      centres.map((x) => at(x, 0, 0))),
  );

  // Physics: a pendulum hanging from the top of the case.
  const p = c.pendulum;
  const pendulum = new Group();
  pendulum.position.set(centres[0]!, c.case.height / 2 - 0.1, 0);
  const rod = new Mesh(new CylinderGeometry(p.rod, p.rod, p.length, 8), brass);
  rod.position.y = -p.length / 2;
  const bob = new Mesh(new SphereGeometry(p.bob, seg, seg / 2), polished);
  bob.position.y = -p.length;
  pendulum.add(rod, bob);
  root.add(pendulum);

  // Chemistry: benzene, six carbons in a ring with a hydrogen on each.
  const mol = c.molecule;
  const carbons: Vector3[] = [];
  const hydrogens: Vector3[] = [];
  for (let i = 0; i < 6; i++) {
    const angle = (i * Math.PI) / 3;
    const carbon = new Vector3(Math.cos(angle), Math.sin(angle), 0).multiplyScalar(mol.ringRadius);
    carbons.push(carbon);
    hydrogens.push(carbon.clone().multiplyScalar((mol.ringRadius + mol.hydrogenOffset) / mol.ringRadius));
  }
  const bonds = [
    ...carbons.map((cAt, i) => between(cAt, carbons[(i + 1) % 6]!)),
    ...carbons.map((cAt, i) => between(cAt, hydrogens[i]!)),
  ];
  const molecule = new Group();
  molecule.position.set(centres[1]!, 0, 0);
  molecule.add(
    instanced(new SphereGeometry(mol.carbon, seg, seg / 2), material("stone-dark"), carbons.map((v) => at(v.x, v.y, v.z))),
    instanced(new SphereGeometry(mol.hydrogen, seg, seg / 2), material("chalk"), hydrogens.map((v) => at(v.x, v.y, v.z))),
    instanced(new CylinderGeometry(mol.bondRadius, mol.bondRadius, 1, 8), polished, bonds),
  );
  root.add(molecule);

  // Mathematics: z = sin(x) cos(y), a surface in brass.
  const s = c.surface;
  const n = perTier(s.segments, tier);
  const surfaceGeometry = new PlaneGeometry(s.size, s.size, n, n);
  surfaceGeometry.rotateX(-Math.PI / 2);
  const pos = surfaceGeometry.getAttribute("position");
  const k = (2 * Math.PI) / s.size;
  for (let i = 0; i < pos.count; i++) {
    pos.setY(i, s.amplitude * Math.sin(pos.getX(i) * k) * Math.cos(pos.getZ(i) * k));
  }
  surfaceGeometry.computeVertexNormals();
  const surfaceMaterial = material("brass");
  surfaceMaterial.side = DoubleSide;
  const surface = new Mesh(surfaceGeometry, surfaceMaterial);
  surface.position.set(centres[2]!, 0, 0);
  root.add(surface);

  const camera = c.camera as CameraPose;
  return {
    root,
    cameraAt: () => camera,
    setProgress: () => {},
    update(t) {
      pendulum.rotation.z = p.amplitude * Math.sin((2 * Math.PI * t) / p.periodMs);
      const turn = (2 * Math.PI * t) / c.spinMs;
      molecule.rotation.set(turn * 0.5, turn, 0);
      surface.rotation.y = turn * 0.5;
      return true;
    },
  };
}
