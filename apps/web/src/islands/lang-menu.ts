/**
 * The language dropdown (components/blocks/LangSwitch.astro) is a <details> of links, so it opens
 * and navigates without this script. This only adds what a menu should do: close on Esc (focus
 * returns to its button) and close on a click or focus outside it.
 */

/** Whether an event target lies outside the menu. A missing target counts as outside. */
export function isOutside(menu: Pick<Node, "contains">, target: EventTarget | null): boolean {
  return !(target instanceof Node) || !menu.contains(target);
}

export function initLangMenus(win: Window): void {
  const doc = win.document;
  const menus = [...doc.querySelectorAll<HTMLDetailsElement>("details[data-lang-menu]")];
  if (menus.length === 0) return;

  const closeOthers = (keep: HTMLDetailsElement | null) =>
    menus.forEach((m) => {
      if (m !== keep) m.open = false;
    });

  menus.forEach((menu) => menu.addEventListener("toggle", () => menu.open && closeOthers(menu)));
  doc.addEventListener("pointerdown", (e) => menus.forEach((m) => m.open && isOutside(m, e.target) && (m.open = false)));
  doc.addEventListener("focusin", (e) => menus.forEach((m) => m.open && isOutside(m, e.target) && (m.open = false)));
  doc.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    const open = menus.find((m) => m.open);
    if (!open) return;
    open.open = false;
    open.querySelector<HTMLElement>("summary")?.focus();
  });
}
