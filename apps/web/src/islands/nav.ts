/**
 * The phone menu (docs/design/navigation.md): a full-screen dialog opened by the menu button.
 * While open, focus stays inside, Esc or the button closes it and focus returns to the button,
 * the page behind does not scroll, and autoscroll holds still (it pauses for aria-modal).
 */
import { tokens } from "@dsap/tokens";

const FOCUSABLE = "a[href], button:not([disabled]), summary, [tabindex]:not([tabindex='-1'])";

export function initMenu(win: Window): void {
  const doc = win.document;
  const button = doc.querySelector<HTMLButtonElement>("[data-menu-button]");
  const menu = button ? doc.getElementById(button.getAttribute("aria-controls") ?? "") : null;
  if (!button || !menu) return;
  const label = button.querySelector<HTMLElement>("[data-label]");

  const setOpen = (open: boolean) => {
    button.setAttribute("aria-expanded", String(open));
    if (label) label.textContent = (open ? button.dataset.close : button.dataset.open) ?? "";
    menu.hidden = !open;
    menu.toggleAttribute("aria-modal", open);
    doc.documentElement.toggleAttribute("data-menu-open", open);
    if (open) menu.querySelector<HTMLElement>(FOCUSABLE)?.focus();
  };
  const close = () => {
    if (button.getAttribute("aria-expanded") !== "true") return;
    setOpen(false);
    button.focus();
  };

  button.addEventListener("click", () => (button.getAttribute("aria-expanded") === "true" ? close() : setOpen(true)));
  menu.addEventListener("click", (e) => {
    if ((e.target as Element).closest("a")) close();
  });
  doc.addEventListener("keydown", (e) => {
    if (button.getAttribute("aria-expanded") !== "true") return;
    if (e.key === "Escape") {
      close();
      return;
    }
    if (e.key !== "Tab") return;
    // Keep focus inside the open menu and its button.
    const stops = [button, ...menu.querySelectorAll<HTMLElement>(FOCUSABLE)];
    const first = stops[0];
    const last = stops[stops.length - 1];
    if (e.shiftKey && doc.activeElement === first) {
      e.preventDefault();
      last?.focus();
    } else if (!e.shiftKey && doc.activeElement === last) {
      e.preventDefault();
      first?.focus();
    }
  });
  // The menu is for narrow screens; if the window widens past nav.menu-from while it is open, close it.
  const from = tokens.nav["menu-from"] as keyof typeof tokens.breakpoint;
  win.matchMedia(`(width >= ${tokens.breakpoint[from]}px)`).addEventListener("change", (e) => {
    if (e.matches) setOpen(false);
  });
}
