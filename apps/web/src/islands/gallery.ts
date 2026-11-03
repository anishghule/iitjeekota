/**
 * The photo strip (components/sections/home/Gallery.astro) is an ordinary horizontal scroller: a
 * finger swipes it sideways, a trackpad scrolls it, the arrow keys move it, and a vertical swipe
 * still scrolls the page. This only adds Previous and Next buttons for a mouse.
 */

/** How much of the strip's width one button press moves, as a share. */
const STEP_SHARE = 0.8;

export type Direction = -1 | 1;

/** Where the strip should scroll to for one press, kept inside the strip. */
export function stepTarget(left: number, viewport: number, scrollable: number, direction: Direction): number {
  return Math.min(Math.max(left + direction * viewport * STEP_SHARE, 0), Math.max(scrollable, 0));
}

/** Whether the strip is at its first or last photo. A half pixel of rounding does not count as room left. */
export function edges(left: number, viewport: number, total: number): { atStart: boolean; atEnd: boolean } {
  return { atStart: left < 1, atEnd: left + viewport > total - 1 };
}

export function initGallery(root: HTMLElement, win: Window): void {
  const track = root.querySelector<HTMLElement>("[data-gallery-track]");
  const nav = root.querySelector<HTMLElement>("[data-gallery-nav]");
  const buttons = Array.from(root.querySelectorAll<HTMLButtonElement>("[data-gallery-step]"));
  if (!track || !nav || buttons.length === 0) return;

  const sync = () => {
    const { atStart, atEnd } = edges(track.scrollLeft, track.clientWidth, track.scrollWidth);
    buttons.forEach((b) => (b.disabled = Number(b.dataset.galleryStep) < 0 ? atStart : atEnd));
  };
  buttons.forEach((b) =>
    b.addEventListener("click", () => {
      const direction: Direction = Number(b.dataset.galleryStep) < 0 ? -1 : 1;
      const behavior = win.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth";
      track.scrollTo({ left: stepTarget(track.scrollLeft, track.clientWidth, track.scrollWidth - track.clientWidth, direction), behavior });
    }),
  );
  track.addEventListener("scroll", sync, { passive: true });
  win.addEventListener("resize", sync);
  nav.hidden = false;
  sync();
}
