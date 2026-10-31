export { config, tokenColor, type RenderTier, type SceneName, type Tier } from "./config.ts";
export { browserTextures, mountScene, type MountOptions } from "./host.ts";
export { qualityTier, readDeviceSignals, type DeviceSignals } from "./quality.ts";
export type { CameraPose, Scene, SceneContext, TexturePort } from "./scene.ts";
export { sceneStats, type SceneStats } from "./stats.ts";
export { createKotaPrism, fitWidth, plateArrival, plateFacing, type KotaPrismInput } from "./scenes/kota-prism.ts";
export { createMedal, type MedalInput } from "./scenes/medal.ts";
export { createSpecimens } from "./scenes/specimens.ts";
export { createSyllabusSlab, slabLayout, topView, type SlabChapter, type SlabInput, type TilePlace } from "./scenes/syllabus-slab.ts";
