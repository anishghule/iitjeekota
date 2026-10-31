/** What the reader's device and settings ask of motion. */
export interface MotionPrefs {
  /** prefers-reduced-motion: no autoscroll, no pinned animation, still renders instead of 3D. */
  reducedMotion: boolean;
  /** Save-Data: do not load heavy scenes. */
  saveData: boolean;
}

const REDUCED = "(prefers-reduced-motion: reduce)";

interface NetworkInformation {
  saveData?: boolean;
}

export function readMotionPrefs(win: Window): MotionPrefs {
  const connection = (win.navigator as Navigator & { connection?: NetworkInformation }).connection;
  return {
    reducedMotion: win.matchMedia?.(REDUCED).matches ?? false,
    saveData: connection?.saveData === true,
  };
}

/** Calls back when the reader switches reduced motion on or off. Returns a function that stops listening. */
export function onReducedMotionChange(win: Window, callback: (reduced: boolean) => void): () => void {
  const query = win.matchMedia?.(REDUCED);
  if (!query) return () => {};
  const listener = (event: MediaQueryListEvent) => callback(event.matches);
  query.addEventListener("change", listener);
  return () => query.removeEventListener("change", listener);
}
