/** The contract every scene meets, and what the host gives it. */
import type { Group, Texture } from "three";
import type { RenderTier, Vec3 } from "./config.ts";

/**
 * How a scene gets textures. In the browser, images load from media slots and text is drawn on a
 * canvas once the brand fonts are in; in tests, a stub returns empty textures.
 */
export interface TexturePort {
  /** An image, by URL, as a colour texture (sRGB) or as data (normal and bump maps). */
  image(url: string, kind: "colour" | "data"): Texture;
  /** A texture drawn on a canvas. Drawn again once fonts load, so text never shows a fallback face. */
  canvas(width: number, height: number, draw: (g: CanvasRenderingContext2D, width: number, height: number) => void, kind: "colour" | "data"): Texture;
}

export interface SceneContext {
  tier: RenderTier;
  textures: TexturePort;
}

export interface CameraPose {
  position: Vec3;
  target: Vec3;
}

export interface Scene {
  readonly root: Group;
  /** Where the camera is at this progress through the section (0 to 1), for a screen of this width / height. */
  cameraAt(progress: number, aspect: number): CameraPose;
  /** Moves the scene to this progress through its section (0 to 1). */
  setProgress(progress: number): void;
  /** Runs continuous animation; returns true while it needs more frames. */
  update(timeMs: number): boolean;
  /** Where the pointer is, from -1 to 1 across and down the screen; scenes that follow it lean towards it. */
  setPointer?(x: number, y: number): void;
}
