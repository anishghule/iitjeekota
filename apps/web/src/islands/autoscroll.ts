/**
 * The autoscroll toggle (plan C5, WCAG 2.2.2). The button carries both labels; the reader's
 * choice is remembered by @dsap/motion. The toggle shows only while some section is pinned (and
 * so takes autoscroll), and not under reduced motion, where autoscroll stays off.
 */
import { bindAutoscroll, SECTION_SELECTOR } from "@dsap/motion";
import { PIN_CHANGE } from "./pin.ts";

export function initAutoscroll(win: Window): void {
  const doc = win.document;
  const toggle = doc.querySelector<HTMLButtonElement>("[data-autoscroll-toggle]");
  if (!toggle || !doc.querySelector(".pinned")) return;
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
