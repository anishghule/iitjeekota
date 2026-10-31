/**
 * Progress through a pinned section, from 0 (its top reaches the viewport top) to 1 (its bottom
 * reaches the viewport bottom). The section is a tall box; its stage inside is `position: sticky`
 * and one viewport high, so the scroll length is the box height minus one viewport.
 */
export function pinnedProgress(top: number, height: number, viewport: number): number {
  const length = height - viewport;
  if (length <= 0) return top <= 0 ? 1 : 0;
  return Math.min(1, Math.max(0, -top / length));
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
