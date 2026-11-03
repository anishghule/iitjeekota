/**
 * The autoscroll toggle (plan C5, WCAG 2.2.2). The button carries both labels; the reader's
 * choice is remembered by @dsap/motion. Only the sections in config/autoscroll.json autoscroll. The
 * toggle shows on pages that have one of them, and not under reduced motion, where autoscroll stays off.
 */
import { bindAutoscroll, SECTION_SELECTOR } from "@dsap/motion";
import config from "../config/autoscroll.json";
import { PIN_CHANGE } from "./pin.ts";

/** Marks the listed sections as autoscroll units (the section ids in each unit share its name). Returns how many were found. */
export function markUnits(doc: Document, units: Readonly<Record<string, readonly string[]>>): number {
  let found = 0;
  for (const [unit, ids] of Object.entries(units)) {
    for (const id of ids) {
      const section = doc.getElementById(id);
      if (!section) continue;
      section.setAttribute("data-autoscroll", unit);
      found += 1;
    }
  }
  return found;
}

export function initAutoscroll(win: Window): void {
  const doc = win.document;
  const toggle = doc.querySelector<HTMLButtonElement>("[data-autoscroll-toggle]");
  if (!toggle || markUnits(doc, config.units) === 0) return;
  const autoscroll = bindAutoscroll(win);
  const label = toggle.querySelector<HTMLElement>("[data-label]");
  const show = () => {
    const on = autoscroll.isOn();
    toggle.hidden = !autoscroll.isAvailable() || !doc.querySelector(SECTION_SELECTOR);
    toggle.setAttribute("aria-pressed", String(on));
    if (label) label.textContent = (on ? toggle.dataset.on : toggle.dataset.off) ?? "";
  };
  toggle.addEventListener("click", () => {
    autoscroll.setOn(!autoscroll.isOn());
    show();
  });
  win.addEventListener(PIN_CHANGE, show);
  show();
}
