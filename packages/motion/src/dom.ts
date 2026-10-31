/**
 * Wires the autoscroll core to the page: sections that opt in with `data-autoscroll`, the reader's
 * input, things that must hold it still (a hovered control, a focused field, an open dialog, a
 * hidden tab), reduced motion, and the reader's own on/off choice, remembered in this browser only.
 */
import { tokens } from "@dsap/tokens";
import { Autoscroll, type AutoscrollSettings, type Section } from "./autoscroll.ts";
import { onReducedMotionChange, readMotionPrefs } from "./prefs.ts";

export const SECTION_SELECTOR = "[data-autoscroll]";
const CONTROL_SELECTOR = "a, button, input, select, textarea, summary, [role='button'], [role='slider'], [tabindex]";
const FIELD_SELECTOR = "input, select, textarea, [contenteditable='true']";
const DIALOG_SELECTOR = "dialog[open], [aria-modal='true']";
const STORAGE_KEY = "dsap.autoscroll";

export interface AutoscrollBinding {
  /** The reader's toggle (WCAG 2.2.2). Remembered in this browser. */
  setOn(on: boolean): void;
  isOn(): boolean;
  /** False while reduced motion is on: the toggle should say so and stay off. */
  isAvailable(): boolean;
  destroy(): void;
}

function readChoice(win: Window): boolean {
  try {
    return win.localStorage.getItem(STORAGE_KEY) !== "off";
  } catch {
    return true; // storage blocked: default on, choice lasts this visit
  }
}

function saveChoice(win: Window, on: boolean): void {
  try {
    win.localStorage.setItem(STORAGE_KEY, on ? "on" : "off");
  } catch {
    // storage blocked: the choice still applies for this visit
  }
}

export function bindAutoscroll(win: Window, settings: AutoscrollSettings = tokens.motion.autoscroll): AutoscrollBinding {
  const doc = win.document;
  const sections = (): Section[] =>
    Array.from(doc.querySelectorAll<HTMLElement>(SECTION_SELECTOR), (el) => {
      const box = el.getBoundingClientRect();
      const start = box.top + win.scrollY;
      return { start, end: start + box.height };
    });

  const auto = new Autoscroll(settings, {
    position: () => win.scrollY,
    viewportHeight: () => win.innerHeight,
    sectionAt: (y) => sections().find((s) => y >= s.start && y < s.end) ?? null,
    scrollBy: (px) => win.scrollBy(0, px),
  });

  let chosen = readChoice(win);
  let reduced = readMotionPrefs(win).reducedMotion;
  const apply = () => auto.setEnabled(chosen && !reduced);
  apply();

  const now = () => win.performance.now();
  const onInput = () => auto.input(now());
  const onScroll = () => auto.scrolled(now());
  const onOver = (e: Event) => {
    if ((e.target as Element | null)?.closest?.(CONTROL_SELECTOR)) auto.block("control-hover");
  };
  const onOut = (e: Event) => {
    if ((e.target as Element | null)?.closest?.(CONTROL_SELECTOR)) auto.release("control-hover");
  };
  const onFocusIn = (e: Event) => {
    if ((e.target as Element | null)?.matches?.(FIELD_SELECTOR)) auto.block("field-focus");
  };
  const onFocusOut = () => auto.release("field-focus");
  const onVisibility = () => (doc.hidden ? auto.block("hidden") : auto.release("hidden"));
  const dialogs = new MutationObserver(() =>
    doc.querySelector(DIALOG_SELECTOR) ? auto.block("dialog-open") : auto.release("dialog-open"),
  );
  dialogs.observe(doc.body, { subtree: true, attributes: true, childList: true, attributeFilter: ["open", "aria-modal"] });

  const inputs = ["wheel", "touchstart", "keydown", "pointerdown"] as const;
  inputs.forEach((type) => win.addEventListener(type, onInput, { passive: true }));
  win.addEventListener("scroll", onScroll, { passive: true });
  doc.addEventListener("pointerover", onOver);
  doc.addEventListener("pointerout", onOut);
  doc.addEventListener("focusin", onFocusIn);
  doc.addEventListener("focusout", onFocusOut);
  doc.addEventListener("visibilitychange", onVisibility);
  const stopReduced = onReducedMotionChange(win, (r) => {
    reduced = r;
    apply();
  });

  let frame = win.requestAnimationFrame(function loop(t) {
    auto.tick(t);
    frame = win.requestAnimationFrame(loop);
  });

  return {
    setOn(on) {
      chosen = on;
      saveChoice(win, on);
      apply();
    },
    isOn: () => chosen && !reduced,
    isAvailable: () => !reduced,
    destroy() {
      win.cancelAnimationFrame(frame);
      inputs.forEach((type) => win.removeEventListener(type, onInput));
      win.removeEventListener("scroll", onScroll);
      doc.removeEventListener("pointerover", onOver);
      doc.removeEventListener("pointerout", onOut);
      doc.removeEventListener("focusin", onFocusIn);
      doc.removeEventListener("focusout", onFocusOut);
      doc.removeEventListener("visibilitychange", onVisibility);
      dialogs.disconnect();
      stopReduced();
    },
  };
}
