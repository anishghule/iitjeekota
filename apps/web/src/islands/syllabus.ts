/**
 * The syllabus (home teaser, and later /jee-syllabus/). Every chapter is already in the HTML twice:
 * as a row in the list (phones) and as a tile in the table (wide screens, with the topics in a side
 * panel). This module decides which show (subject, class, exam), opens the row named in the URL hash
 * (11-p-03), expands or collapses rows, and opens a tile's panel. The panel copies the row's topics,
 * so the text lives in one place; nothing here builds text.
 */
import { fill } from "../lib/format.ts";
import { PIN_CHANGE } from "./pin.ts";

export interface Filter {
  subject: string;
  class: string;
  exam: string;
}

export interface RowFacts {
  subject: string;
  classes: number[];
  inMain: boolean;
  inAdvanced: boolean;
}

export function matches(row: RowFacts, filter: Filter): boolean {
  const exam = filter.exam === "all" || (filter.exam === "main" ? row.inMain : row.inAdvanced);
  const klass = filter.class === "all" || row.classes.includes(Number(filter.class));
  return (filter.subject === "all" || row.subject === filter.subject) && klass && exam;
}

function facts(row: HTMLElement): RowFacts {
  return {
    subject: row.dataset.subject ?? "",
    classes: (row.dataset.classes ?? "").split(" ").map(Number),
    inMain: row.dataset.main !== undefined,
    inAdvanced: row.dataset.advanced !== undefined,
  };
}

export function initSyllabus(root: HTMLElement, win: Window): void {
  const doc = root.ownerDocument;
  const rows = Array.from(root.querySelectorAll<HTMLElement>("[data-chapter]"));
  const tiles = Array.from(root.querySelectorAll<HTMLButtonElement>("[data-tile]"));
  const buttons = Array.from(root.querySelectorAll<HTMLButtonElement>("[data-filter]"));
  const count = root.querySelector<HTMLElement>("[data-count]");
  const toggle = root.querySelector<HTMLButtonElement>("[data-expand]");
  const panel = root.querySelector<HTMLElement>("[data-panel]");
  const panelBody = panel?.querySelector<HTMLElement>("[data-panel-body]");
  const panelTitle = panel?.querySelector<HTMLElement>("[data-panel-title]");
  const panelMeta = panel?.querySelector<HTMLElement>("[data-panel-meta]");
  const isWide = () => doc.documentElement.dataset.layout === "wide";
  const rowOf = (id: string) => rows.find((r) => r.dataset.chapter === id);
  const pressed = (kind: string) => buttons.find((b) => b.dataset.filter?.startsWith(`${kind}:`) && b.getAttribute("aria-pressed") === "true");
  const filter: Filter = { subject: "", class: "all", exam: "all" };
  for (const kind of Object.keys(filter) as (keyof Filter)[]) filter[kind] = pressed(kind)?.dataset.filter?.split(":")[1] ?? filter[kind];
  // The table shows all three subjects at once, the list one at a time: each layout starts on its own, until the reader chooses.
  let chosen = false;
  const firstSubject = filter.subject;
  const startSubject = () => {
    if (!chosen) filter.subject = isWide() ? "all" : firstSubject;
  };

  const visibleRows = () => rows.filter((r) => !r.hidden);
  const details = () => visibleRows().flatMap((r) => Array.from(r.querySelectorAll("details")));
  const syncToggle = () => {
    const all = details();
    const open = all.length > 0 && all.every((d) => d.open);
    toggle?.setAttribute("aria-pressed", String(open));
    if (toggle) toggle.textContent = (open ? root.dataset.collapseLabel : root.dataset.expandLabel) ?? "";
  };
  const apply = () => {
    for (const row of rows) row.hidden = !matches(facts(row), filter);
    for (const tile of tiles) tile.toggleAttribute("data-dim", !matches(facts(tile), filter));
    root.querySelectorAll<HTMLElement>("[data-subject-block]").forEach((block) => {
      if (block.closest(".syllabus__index")) block.hidden = filter.subject !== "all" && block.dataset.subjectBlock !== filter.subject;
    });
    root.querySelectorAll<HTMLElement>("[data-class-group]").forEach((group) => (group.hidden = !group.querySelector("[data-chapter]:not([hidden])")));
    for (const b of buttons) {
      const [kind, value] = (b.dataset.filter ?? ":").split(":") as [keyof Filter, string];
      b.setAttribute("aria-pressed", String(filter[kind] === value));
    }
    if (count) count.textContent = fill(root.dataset.countTemplate ?? "{n}", { n: visibleRows().length });
    syncToggle();
  };

  const open = (tile: HTMLElement) => {
    const row = rowOf(tile.dataset.tile ?? "");
    if (!panel || !panelBody || !row) return;
    tiles.forEach((t) => t.setAttribute("aria-pressed", String(t === tile)));
    const name = row.querySelector(".row__name")?.textContent ?? "";
    const code = row.querySelector(".row__code")?.textContent ?? "";
    if (panelMeta) panelMeta.textContent = `${code} · ${row.querySelector(".row__unit")?.textContent ?? ""}`;
    if (panelTitle) panelTitle.textContent = name;
    const body = row.querySelector(".row__body");
    panelBody.replaceChildren(...(body ? Array.from(body.cloneNode(true).childNodes) : []));
    panel.hidden = false;
    panel.querySelector<HTMLElement>("[data-panel-close]")?.focus({ preventScroll: true });
  };
  const close = () => {
    if (!panel || panel.hidden) return;
    panel.hidden = true;
    const opener = tiles.find((t) => t.getAttribute("aria-pressed") === "true");
    tiles.forEach((t) => t.setAttribute("aria-pressed", "false"));
    opener?.focus({ preventScroll: true });
  };

  /** A link to 11-p-03 shows that chapter: its subject is selected, filters that hide it are cleared, and it opens. */
  const showHash = () => {
    const id = doc.location.hash.slice(1);
    const row = rows.find((r) => r.querySelector(`[id="${CSS.escape(id)}"]`));
    if (!row) return;
    chosen = true;
    Object.assign(filter, { subject: row.dataset.subject ?? filter.subject, class: "all", exam: "all" });
    apply();
    if (isWide()) {
      const tile = tiles.find((t) => t.dataset.tile === row.dataset.chapter);
      if (tile) {
        open(tile);
        tile.scrollIntoView({ block: "center" });
      }
      return;
    }
    row.querySelector("details")?.setAttribute("open", "");
    syncToggle();
    row.scrollIntoView({ block: "center" });
  };

  root.addEventListener("click", (e) => {
    const target = e.target as Element;
    const button = target.closest<HTMLButtonElement>("[data-filter]");
    if (button) {
      const [kind, value] = (button.dataset.filter ?? ":").split(":") as [keyof Filter, string];
      filter[kind] = value;
      if (kind === "subject") chosen = true;
      return apply();
    }
    if (target.closest("[data-expand]")) {
      const next = toggle?.getAttribute("aria-pressed") !== "true";
      details().forEach((d) => (d.open = next));
      return syncToggle();
    }
    const tile = target.closest<HTMLElement>("[data-tile]");
    if (tile) return open(tile);
  });
  panel?.querySelector("[data-panel-close]")?.addEventListener("click", close);
  doc.addEventListener("keydown", (e) => e.key === "Escape" && close());
  doc.addEventListener("click", (e) => {
    const target = e.target as Element;
    if (panel && !panel.hidden && !panel.contains(target) && !target.closest("[data-tile]")) close();
  });
  root.addEventListener("toggle", syncToggle, true);
  win.addEventListener("hashchange", showHash);
  win.addEventListener(PIN_CHANGE, () => {
    startSubject();
    apply();
  });
  startSubject();
  apply();
  showHash();
}
