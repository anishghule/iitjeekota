/**
 * Turns scroll progress through a section into steps. A section with data-steps="n" gets
 * data-step (0 to n-1) and the custom property --progress (0 to 1); items marked data-step-item
 * get aria-current on the current step. data-steps-from="0.3" starts the steps that far in (the
 * Kota prism assembles first); before it no item is current. A "stepchange" event tells other islands.
 */
import { observeProgress } from "@dsap/motion";

export interface StepChange {
  step: number;
  progress: number;
}

/** The nearest of n evenly spaced stops, the same rule the Kota prism uses to settle on a plate. */
export function stepAt(progress: number, steps: number): number {
  return Math.min(steps - 1, Math.max(0, Math.round(progress * (steps - 1))));
}

export function initSteps(section: HTMLElement, win: Window): () => void {
  const steps = Number(section.dataset.steps);
  const from = Number(section.dataset.stepsFrom ?? 0);
  const items = Array.from(section.querySelectorAll<HTMLElement>("[data-step-item]"));
  let current = -2;
  return observeProgress(section, (progress) => {
    section.style.setProperty("--progress", progress.toFixed(4));
    const step = progress < from ? -1 : stepAt((progress - from) / (1 - from), steps);
    if (step === current) return;
    current = step;
    section.dataset.step = String(step);
    items.forEach((item, i) => item.toggleAttribute("aria-current", i === step));
    section.dispatchEvent(new CustomEvent<StepChange>("stepchange", { detail: { step, progress } }));
  }, win);
}

export function initAllSteps(win: Window): void {
  for (const section of win.document.querySelectorAll<HTMLElement>("[data-steps]")) initSteps(section, win);
}
