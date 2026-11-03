/**
 * Turns scroll progress through a section into steps. A section with data-steps="n" gets
 * data-step (0 to n-1) and the custom property --progress (0 to 1); items marked data-step-item
 * get aria-current on the current step. data-steps-from="0.3" starts the steps that far in (the
 * Kota prism assembles first); before it no item is current. A "stepchange" event tells other islands.
 */
import { holdLead, holdProgress, observeProgress } from "@dsap/motion";

export interface StepChange {
  step: number;
  progress: number;
}

/** The nearest of n evenly spaced stops, the same rule the Kota prism uses to settle on a plate. */
export function stepAt(progress: number, steps: number): number {
  return Math.min(steps - 1, Math.max(0, Math.round(progress * (steps - 1))));
}

/**
 * The progress (0 to 1) through a section at which step i of n is the current one, given the share
 * the section holds back before its steps begin (data-steps-from). The inverse of stepAt.
 */
export function progressForStep(i: number, steps: number, from = 0): number {
  return from + (1 - from) * (steps <= 1 ? 0 : i / (steps - 1));
}

/** Where to scroll the page (px) so that step i is the current one: the section's hold begins `lead` in and ends a viewport before its bottom. */
export function scrollForStep(i: number, steps: number, from: number, top: number, height: number, viewport: number, lead: number): number {
  return top + lead + progressForStep(i, steps, from) * Math.max(0, height - viewport - lead);
}

export function initSteps(section: HTMLElement, win: Window): () => void {
  const steps = Number(section.dataset.steps);
  const from = Number(section.dataset.stepsFrom ?? 0);
  const items = Array.from(section.querySelectorAll<HTMLElement>("[data-step-item]"));
  let current = -2;
  // Items of a section marked data-steps-goto can be clicked (or Entered) to scroll to their step.
  if (section.hasAttribute("data-steps-goto")) {
    const goto = (item: HTMLElement) => {
      const i = items.indexOf(item);
      if (i < 0) return;
      const box = section.getBoundingClientRect();
      const top = scrollForStep(i, steps, from, box.top + win.scrollY, box.height, win.innerHeight, holdLead(section, win));
      const reduced = win.matchMedia("(prefers-reduced-motion: reduce)").matches;
      win.scrollTo({ top, behavior: reduced ? "auto" : "smooth" });
    };
    section.addEventListener("click", (e) => {
      const item = (e.target as Element).closest<HTMLElement>("[data-step-goto]");
      if (item && !(e.target as Element).closest("a")) goto(item);
    });
    section.addEventListener("keydown", (e) => {
      const item = (e.target as Element).closest<HTMLElement>("[data-step-goto]");
      if (item && item === e.target && (e.key === "Enter" || e.key === " ")) {
        e.preventDefault();
        goto(item);
      }
    });
  }
  return observeProgress(section, (progress) => {
    section.style.setProperty("--progress", progress.toFixed(4));
    const step = progress < from ? -1 : stepAt((progress - from) / (1 - from), steps);
    if (step === current) return;
    current = step;
    section.dataset.step = String(step);
    items.forEach((item, i) => item.toggleAttribute("aria-current", i === step));
    section.dispatchEvent(new CustomEvent<StepChange>("stepchange", { detail: { step, progress } }));
  }, win, holdProgress(section, win));
}

export function initAllSteps(win: Window): void {
  for (const section of win.document.querySelectorAll<HTMLElement>("[data-steps]")) initSteps(section, win);
}
