/**
 * The camera rail: one canvas stays behind the whole page, and the camera travels from one scene
 * to the next as the reader scrolls (the v3.2 "vault" idea). This is the pure part: given where the
 * scene sections sit on the page and where the reader is, which two scenes the camera is between,
 * how far along, and how visible the canvas is. Nothing here touches the DOM.
 */

/** A scene's section, as page offsets in pixels. Sections are in page order. */
export interface Extent {
  start: number;
  end: number;
}

export interface RailState {
  /** The scene the camera is leaving and the one it is heading for; equal while it dwells on one. */
  from: number;
  to: number;
  /** How far between them, eased (0 to 1). */
  t: number;
  /** How visible the canvas is (0 to 1): full while scene sections fill the screen, gone over plain content. */
  opacity: number;
}

const ease = (t: number) => t * t * (3 - 2 * t);

/**
 * The camera dwells on a scene while its section holds the screen (its top at or above the viewport
 * top, its bottom at or below the viewport bottom), and travels to the next scene over the rest of
 * the scroll between the two dwells.
 */
export function railAt(extents: readonly Extent[], y: number, viewport: number): RailState {
  const last = extents.length - 1;
  const opacity = railOpacity(extents, y, viewport);
  const dwellEnd = (i: number) => Math.max(extents[i]!.start, extents[i]!.end - viewport);
  if (last < 0 || y <= extents[0]!.start) return { from: 0, to: 0, t: 0, opacity };
  for (let i = 0; i <= last; i++) {
    if (y <= dwellEnd(i)) return { from: i, to: i, t: 0, opacity };
    const next = extents[i + 1];
    if (next && y < next.start) {
      const t = (y - dwellEnd(i)) / (next.start - dwellEnd(i));
      return { from: i, to: i + 1, t: ease(t), opacity };
    }
  }
  return { from: last, to: last, t: 0, opacity };
}

/** The share of the viewport that scene sections cover. Adjacent sections add up to one, so there is no dip between them. */
export function railOpacity(extents: readonly Extent[], y: number, viewport: number): number {
  const covered = extents.reduce((sum, e) => sum + Math.max(0, Math.min(e.end, y + viewport) - Math.max(e.start, y)), 0);
  return Math.min(1, covered / viewport);
}
