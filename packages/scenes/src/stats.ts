/** Counts for budgets: triangles and draw calls of a scene graph, without a renderer. */
import { InstancedMesh, Mesh, type Object3D } from "three";

export interface SceneStats {
  triangles: number;
  drawCalls: number;
}

export function sceneStats(root: Object3D): SceneStats {
  let triangles = 0;
  let drawCalls = 0;
  root.traverse((obj) => {
    if (!(obj instanceof Mesh) || !obj.visible) return;
    const geometry = obj.geometry;
    const perInstance = geometry.index ? geometry.index.count / 3 : (geometry.getAttribute("position")?.count ?? 0) / 3;
    const instances = obj instanceof InstancedMesh ? obj.count : 1;
    triangles += perInstance * instances;
    drawCalls += Array.isArray(obj.material) ? Math.max(1, geometry.groups.length) : 1;
  });
  return { triangles: Math.round(triangles), drawCalls };
}
