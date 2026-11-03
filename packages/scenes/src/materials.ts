/** three.js materials from the material.* tokens: one place decides what brass, stone and glass look like. */
import { tokens, type MaterialName } from "@dsap/tokens";
import { Color, MeshPhysicalMaterial, Vector2, type Texture } from "three";

interface MaterialToken {
  color: string;
  metalness: number;
  roughness: number;
  normalScale?: number;
  envMapIntensity?: number;
  bumpScale?: number;
  opacity?: number;
  emissive?: string;
  emissiveIntensity?: number;
}

export interface MaterialMaps {
  map?: Texture;
  normalMap?: Texture;
  bumpMap?: Texture;
}

/** A material from its token, with any texture maps the scene supplies. */
export function material(name: MaterialName, maps: MaterialMaps = {}): MeshPhysicalMaterial {
  const t = tokens.material[name] as MaterialToken;
  const m = new MeshPhysicalMaterial({
    color: new Color(t.color),
    metalness: t.metalness,
    roughness: t.roughness,
    envMapIntensity: t.envMapIntensity ?? 1,
  });
  if (maps.map) m.map = maps.map;
  if (maps.normalMap) {
    m.normalMap = maps.normalMap;
    const s = t.normalScale ?? 1;
    m.normalScale = new Vector2(s, Math.abs(s));
  }
  if (maps.bumpMap) {
    m.bumpMap = maps.bumpMap;
    m.bumpScale = t.bumpScale ?? 1;
  }
  if (t.emissive) {
    m.emissive = new Color(t.emissive);
    m.emissiveIntensity = t.emissiveIntensity ?? 1;
  }
  if (t.opacity !== undefined) {
    m.transparent = true;
    m.opacity = t.opacity;
    m.depthWrite = false; // what is behind a see-through surface still draws
  }
  return m;
}
