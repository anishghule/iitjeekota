/**
 * The example report (home, section report). Every week's panel is rendered by the section; this
 * shows one at a time. While the section is pinned, scrolling steps through the weeks; a click
 * on a week takes over until the reader leaves the section.
 */
import type { StepChange } from "./steps.ts";

export function initReport(section: HTMLElement): void {
  const panels = Array.from(section.querySelectorAll<HTMLElement>("[data-week]"));
  const buttons = Array.from(section.querySelectorAll<HTMLButtonElement>("[data-week-button]"));
  const points = Array.from(section.querySelectorAll<SVGElement>("[data-trend-point]"));
  let manual = false;

  const show = (week: number) => {
    panels.forEach((p, i) => (p.hidden = i !== week));
    buttons.forEach((b, i) => b.setAttribute("aria-pressed", String(i === week)));
    points.forEach((p, i) => p.toggleAttribute("data-active", i === week));
  };
  section.addEventListener("stepchange", (e) => {
    if (!manual) show((e as CustomEvent<StepChange>).detail.step);
  });
  buttons.forEach((b, i) =>
    b.addEventListener("click", () => {
      manual = true;
      show(i);
    }),
  );
  new IntersectionObserver(([entry]) => {
    if (!entry?.isIntersecting) manual = false;
  }).observe(section);
  show(0);
}
