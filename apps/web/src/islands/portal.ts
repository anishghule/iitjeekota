/**
 * The example portal window (home, section portal): tabs that follow the ARIA tabs pattern, and a
 * slight tilt towards the pointer. The tilt is skipped under reduced motion.
 */
import { readMotionPrefs } from "@dsap/motion";

export function initPortal(root: HTMLElement, win: Window): void {
  const tabs = Array.from(root.querySelectorAll<HTMLButtonElement>("[role='tab']"));
  const select = (index: number, focus: boolean) => {
    tabs.forEach((tab, i) => {
      const on = i === index;
      tab.setAttribute("aria-selected", String(on));
      tab.tabIndex = on ? 0 : -1;
      const panel = root.querySelector<HTMLElement>(`#${tab.getAttribute("aria-controls")}`);
      if (panel) panel.hidden = !on;
      if (on && focus) tab.focus();
    });
  };
  tabs.forEach((tab, i) => {
    tab.addEventListener("click", () => select(i, false));
    tab.addEventListener("keydown", (e) => {
      const step = e.key === "ArrowDown" || e.key === "ArrowRight" ? 1 : e.key === "ArrowUp" || e.key === "ArrowLeft" ? -1 : 0;
      if (!step) return;
      e.preventDefault();
      select((i + step + tabs.length) % tabs.length, true);
    });
  });
  select(0, false);

  if (readMotionPrefs(win).reducedMotion) return;
  const frame = root.querySelector<HTMLElement>("[data-tilt]");
  if (!frame) return;
  root.addEventListener("pointermove", (e) => {
    const box = frame.getBoundingClientRect();
    frame.style.setProperty("--tilt-x", ((e.clientX - box.left) / box.width - 0.5).toFixed(3));
    frame.style.setProperty("--tilt-y", ((e.clientY - box.top) / box.height - 0.5).toFixed(3));
  });
  root.addEventListener("pointerleave", () => {
    frame.style.setProperty("--tilt-x", "0");
    frame.style.setProperty("--tilt-y", "0");
  });
}
