/**
 * The area map (plan C4). Picking an area highlights its point and its route to the nearer
 * centre, and shows that area's card. The map, routes and cards are rendered by the section.
 */
export function initAreaMap(root: HTMLElement): void {
  const chips = Array.from(root.querySelectorAll<HTMLButtonElement>("[data-pick]"));
  const select = (area: string) => {
    chips.forEach((c) => c.setAttribute("aria-pressed", String(c.dataset.pick === area)));
    root.querySelectorAll<Element>("[data-area]").forEach((el) => el.toggleAttribute("data-active", el.getAttribute("data-area") === area));
    root.querySelectorAll<HTMLElement>("[data-card]").forEach((card) => (card.hidden = card.dataset.card !== area));
    root.dataset.picked = area;
  };
  root.addEventListener("click", (e) => {
    const target = (e.target as Element).closest<HTMLElement>("[data-pick]");
    if (target?.dataset.pick) select(target.dataset.pick);
  });
  const first = chips[0]?.dataset.pick;
  if (first) select(first);
}
