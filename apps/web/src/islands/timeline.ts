/**
 * A timeline that fills as the reader scrolls it past (home, section journey). Unlike the pinned
 * sections nothing holds still: the list scrolls with the page and a reading line at the middle of
 * the screen decides how much of the rail is filled and which step is current.
 */
import { observeProgress } from "@dsap/motion";

/** Where the reading line sits, as a share of the viewport height. */
const READING_LINE = 0.5;

/** Share of the list above the reading line: 0 before the list reaches it, 1 once it has passed. */
export function railFill(top: number, height: number, viewport: number): number {
  if (height <= 0) return 0;
  return Math.min(1, Math.max(0, (viewport * READING_LINE - top) / height));
}

/** The last step whose centre is above the reading line, or -1 before the first. */
export function currentStep(centres: number[], viewport: number): number {
  return centres.reduce((found, centre, i) => (centre <= viewport * READING_LINE ? i : found), -1);
}

export function initTimeline(list: HTMLElement, win: Window): () => void {
  const items = Array.from(list.querySelectorAll<HTMLElement>("[data-step-item]"));
  let current = -2;
  return observeProgress(list, (fill) => {
    list.style.setProperty("--progress", fill.toFixed(4));
    const step = currentStep(items.map((item) => item.getBoundingClientRect().top + item.offsetHeight / 2), win.innerHeight);
    if (step === current) return;
    current = step;
    items.forEach((item, i) => item.toggleAttribute("aria-current", i === step));
  }, win, (top, height, viewport) => railFill(top, height, viewport));
}
