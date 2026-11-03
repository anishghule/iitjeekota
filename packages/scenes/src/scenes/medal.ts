/**
 * The struck brass medal (home opening). The face is the official medal image, its relief comes
 * from the normal map, the edge is reeded, and two rims catch the light. Scrolling brings it from
 * a tilted distance to face the reader, then turns it to show its edge.
 */
import { CylinderGeometry, Group, Mesh, RepeatWrapping, TorusGeometry, type Texture } from "three";
import { config, perTier } from "../config.ts";
import { poseAt } from "../keyframes.ts";
import { material } from "../materials.ts";
import type { CameraPose, Scene, SceneContext } from "../scene.ts";

export interface MedalInput {
  /** The official medal image (media slot brand/logo-medal, built to medal-512.png). */
  faceUrl: string;
  /** Its normal map (media slot brand/logo-medal-normal). */
  normalUrl: string;
}

export function createMedal(ctx: SceneContext, input: MedalInput): Scene {
  const c = config.scenes.medal;
  const { tier, textures } = ctx;

  // The cylinder is turned to face the camera, so every map on its caps is turned back the same way.
  const upright = <T extends Texture>(texture: T): T => {
    texture.center.set(0.5, 0.5);
    texture.rotation = Math.PI / 2;
    return texture;
  };
  const face = upright(textures.image(input.faceUrl, "colour"));
  const back = upright(textures.image(input.faceUrl, "colour"));
  back.wrapS = RepeatWrapping;
  back.repeat.x = -1; // seen from behind, the medal reads mirrored, as a struck coin does
  back.offset.x = 1;
  const normal = upright(textures.image(input.normalUrl, "data"));

  const ridge = Math.round(c.reedLevels.ridge * 255);
  const groove = Math.round(c.reedLevels.groove * 255);
  const reeds = textures.canvas(c.reeds * 4, 4, (g, w, h) => {
    g.fillStyle = `rgb(${groove}, ${groove}, ${groove})`;
    g.fillRect(0, 0, w, h);
    g.fillStyle = `rgb(${ridge}, ${ridge}, ${ridge})`;
    for (let x = 0; x < w; x += 4) g.fillRect(x, 0, 2, h);
  }, "data");
  reeds.wrapS = RepeatWrapping;

  const coinGeometry = new CylinderGeometry(c.radius, c.radius, c.thickness, perTier(c.segments, tier), 1);
  coinGeometry.rotateX(Math.PI / 2);
  // CylinderGeometry groups: 0 the side, 1 the top cap (now facing the camera), 2 the bottom cap.
  const coin = new Mesh(coinGeometry, [
    material("medal-edge", { bumpMap: reeds }),
    material("medal-face", { map: face, normalMap: normal }),
    material("medal-back", { map: back, normalMap: normal }),
  ]);

  const rimGeometry = new TorusGeometry(c.radius + c.rim.offset, c.rim.tube, perTier(c.rim.radialSegments, tier), perTier(c.rim.tubularSegments, tier));
  const rimMaterial = material("medal-rim");
  const front = new Mesh(rimGeometry, rimMaterial);
  front.position.z = c.thickness / 2;
  const rear = new Mesh(rimGeometry, rimMaterial);
  rear.position.z = -c.thickness / 2;

  // The medal hangs in a holder: scroll moves the root through the keyframes; the holder adds the
  // gentle float and the lean towards the pointer, so the two never fight.
  const holder = new Group();
  coin.name = "coin";
  holder.add(coin, front, rear);
  const root = new Group();
  root.name = "medal";
  root.add(holder);

  const { float, pointer } = c;
  const aim = { x: 0, y: 0 };
  const lean = { x: 0, y: 0 };
  const camera = c.camera as CameraPose;
  // On arrival the medal spins in from its tilted distance and settles; scrolling then carries it on from there.
  let target = 0;
  let arrived = 0;
  let introStart: number | null = null;
  const place = () => {
    const eased = 1 - (1 - arrived) ** 3;
    const pose = poseAt(c.keyframes, target * eased);
    root.position.set(...pose.position);
    root.rotation.set(pose.rotation[0], pose.rotation[1] + (1 - eased) * c.intro.spin, pose.rotation[2]);
  };
  const scene: Scene = {
    root,
    halfWidth: c.halfWidth,
    halfHeight: c.halfHeight,
    cameraAt: () => camera,
    setProgress(progress) {
      target = progress;
      place();
    },
    setPointer(x, y) {
      aim.x = x;
      aim.y = y;
    },
    update(timeMs) {
      if (introStart === null) introStart = timeMs;
      const before = arrived;
      arrived = Math.min(1, (timeMs - introStart) / c.intro.ms);
      if (arrived !== before) place();
      lean.x += (aim.x - lean.x) * pointer.follow;
      lean.y += (aim.y - lean.y) * pointer.follow;
      holder.rotation.set(lean.y * pointer.maxTilt, lean.x * pointer.maxTilt, 0);
      holder.position.y = Math.sin((timeMs / float.periodMs) * 2 * Math.PI) * float.amplitude;
      return true; // it floats for as long as it is on screen
    },
  };
  scene.setProgress(0);
  return scene;
}
