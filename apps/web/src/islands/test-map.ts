/**
 * The test map (home, under the report). The section draws every subject's bars and every
 * question's detail; this module shows one subject at a time and the detail of the bar picked.
 */

export function initTestMap(root: HTMLElement): void {
  const tabs = Array.from(root.querySelectorAll<HTMLButtonElement>("[data-map-tab]"));
  const panels = Array.from(root.querySelectorAll<HTMLElement>("[data-map-panel]"));

  const showSubject = (id: string) => {
    tabs.forEach((t) => t.setAttribute("aria-pressed", String(t.dataset.mapTab === id)));
    panels.forEach((p) => (p.hidden = p.dataset.mapPanel !== id));
  };
  const pick = (bar: Element) => {
    const panel = bar.closest<HTMLElement>("[data-map-panel]");
    if (!panel) return;
    panel.querySelectorAll("[data-q]").forEach((q) => q.toggleAttribute("data-selected", q === bar));
    panel.querySelectorAll<HTMLElement>("[data-detail]").forEach((d) => (d.hidden = d.dataset.detail !== (bar as HTMLElement).dataset.q));
    panel.querySelector<HTMLElement>("[data-detail-hint]")?.setAttribute("hidden", "");
  };

  root.addEventListener("click", (e) => {
    const target = e.target as Element;
    const tab = target.closest<HTMLElement>("[data-map-tab]");
    if (tab) return showSubject(tab.dataset.mapTab ?? "");
    const bar = target.closest("[data-q]");
    if (bar) pick(bar);
  });
  root.addEventListener("keydown", (e) => {
    const bar = (e.target as Element).closest("[data-q]");
    if (bar && (e.key === "Enter" || e.key === " ")) {
      e.preventDefault();
      pick(bar);
    }
  });
}
