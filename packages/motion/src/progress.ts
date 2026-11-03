/**
 * Progress through a pinned section, from 0 (its top reaches the viewport top) to 1 (its bottom
 * reaches the viewport bottom). The section is a tall box; its stage inside is `position: sticky`
 * and one viewport high, so the scroll length is the box height minus one viewport.
 * `lead` is how far the reader scrolls before anything holds still: in the narrow layout the text
 * scrolls past first, and the progress starts when the held part sticks, not before.
 */
export function pinnedProgress(top: number, height: number, viewport: number, lead = 0): number {
  const length = height - viewport - lead;
  if (length <= 0) return top + lead <= 0 ? 1 : 0;
  return Math.min(1, Math.max(0, -(top + lead) / length));
}

/**
 * How far into a narrow-layout section (data-pin="narrow") its held part (data-pin-visual) begins
 * to stick: the distance from the section's top to where the part sits in the flow, less the
 * offset it sticks at. Zero in any other layout. Read from layout, so it follows the text's height.
 */
export function holdLead(section: HTMLElement, win: Window): number {
  const held = section.querySelector<HTMLElement>("[data-pin-visual]");
  const parent = held?.parentElement;
  if (!held || !parent || section.dataset.pin !== "narrow") return 0;
  const before = held.previousElementSibling as HTMLElement | null;
  const gap = Number.parseFloat(win.getComputedStyle(parent).rowGap) || 0;
  const inFlow = before ? before.offsetTop + before.offsetHeight + gap : parent.offsetTop;
  const sticksAt = Number.parseFloat(win.getComputedStyle(held).top) || 0;
  return Math.max(0, inFlow - sticksAt);
}

/** Pinned progress for a section whose held part may start part way in (see holdLead). */
export function holdProgress(section: HTMLElement, win: Window): ProgressMeasure {
  return (top, height, viewport) => pinnedProgress(top, height, viewport, holdLead(section, win));
}

/**
 * Progress through a section that scrolls normally, from 0 (its top enters at the bottom of the
 * viewport) to 1 (its bottom leaves at the top). A section at the very top of the page starts part
 * way through.
 */
export function passageProgress(top: number, height: number, viewport: number): number {
  return Math.min(1, Math.max(0, (viewport - top) / (viewport + height)));
}

export type ProgressMeasure = (top: number, height: number, viewport: number) => number;

/**
 * Calls back with the section's progress while it is near the viewport, at most once per frame.
 * Returns a function that stops watching.
 */
export function observeProgress(
  el: HTMLElement,
  onProgress: (progress: number) => void,
  win: Window = window,
  measureBy: ProgressMeasure = pinnedProgress,
): () => void {
  let frame = 0;
  let last = Number.NaN;
  const measure = () => {
    frame = 0;
    const box = el.getBoundingClientRect();
    const progress = measureBy(box.top, box.height, win.innerHeight);
    if (progress !== last) {
      last = progress;
      onProgress(progress);
    }
  };
  const schedule = () => {
    if (!frame) frame = win.requestAnimationFrame(measure);
  };
  const listen = (on: boolean) => {
    const method = on ? "addEventListener" : "removeEventListener";
    win[method]("scroll", schedule, { passive: true } as AddEventListenerOptions);
    win[method]("resize", schedule);
  };
  const observer = new IntersectionObserver(([entry]) => {
    listen(entry?.isIntersecting ?? false);
    if (entry?.isIntersecting) schedule();
  });
  observer.observe(el);
  return () => {
    observer.disconnect();
    listen(false);
    if (frame) win.cancelAnimationFrame(frame);
  };
}
