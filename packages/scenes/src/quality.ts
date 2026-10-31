/** Which quality tier a device gets: full 3D, lighter 3D, or a still image. */
import { readMotionPrefs } from "@dsap/motion";
import { config, type Tier } from "./config.ts";

export interface DeviceSignals {
  reducedMotion: boolean;
  saveData: boolean;
  webgl2: boolean;
  cores?: number;
  memoryGb?: number;
}

export function qualityTier(signals: DeviceSignals, thresholds = config.tiers.lite): Tier {
  if (signals.reducedMotion || signals.saveData || !signals.webgl2) return "still";
  const fewCores = signals.cores !== undefined && signals.cores <= thresholds.maxCores;
  const littleMemory = signals.memoryGb !== undefined && signals.memoryGb <= thresholds.maxMemoryGb;
  return fewCores || littleMemory ? "lite" : "full";
}

export function readDeviceSignals(win: Window): DeviceSignals {
  const prefs = readMotionPrefs(win);
  const nav = win.navigator as Navigator & { deviceMemory?: number };
  let webgl2 = false;
  try {
    webgl2 = win.document.createElement("canvas").getContext("webgl2") !== null;
  } catch {
    webgl2 = false;
  }
  return {
    reducedMotion: prefs.reducedMotion,
    saveData: prefs.saveData,
    webgl2,
    ...(nav.hardwareConcurrency ? { cores: nav.hardwareConcurrency } : {}),
    ...(nav.deviceMemory ? { memoryGb: nav.deviceMemory } : {}),
  };
}
