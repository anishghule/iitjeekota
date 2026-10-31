/**
 * The syllabus table (home teaser, and later /jee-syllabus/). Filters dim the chapters that do
 * not match, so the table keeps its shape. A chapter opens its details in the panel beside the
 * table. Chapter data comes from the JSON block the section renders; text goes in as text.
 */
import { fill, readJson } from "../lib/format.ts";
import type { Chapter } from "../lib/types.ts";

interface Labels {
  advancedOnly: string;
  unit: string;
  class: string;
  classes: string;
  covers: string;
  advancedAlso: string;
  subjects: Record<string, string>;
}

export type Filter = { subject: string; exam: string };

export function matches(chapter: Pick<Chapter, "subject" | "main" | "advanced">, filter: Filter): boolean {
  const subject = filter.subject === "all" || chapter.subject === filter.subject;
  const exam = filter.exam === "all" || (filter.exam === "main" ? chapter.main !== null : chapter.advanced.length > 0);
  return subject && exam;
}

function element<K extends keyof HTMLElementTagNameMap>(doc: Document, tag: K, text?: string): HTMLElementTagNameMap[K] {
  const el = doc.createElement(tag);
  if (text !== undefined) el.textContent = text;
  return el;
}

export function initSyllabus(root: HTMLElement): void {
  const doc = root.ownerDocument;
  const chapters = readJson<Chapter[]>(root, "script[data-chapters]") ?? [];
  const labels = readJson<Labels>(root, "script[data-labels]");
  const byId = new Map(chapters.map((c) => [c.id, c]));
  const tiles = Array.from(root.querySelectorAll<HTMLButtonElement>("[data-chapter]"));
  const panel = root.querySelector<HTMLElement>("[data-panel]");
  const filter: Filter = { subject: "all", exam: "all" };

  const apply = () => {
    for (const tile of tiles) {
      const chapter = byId.get(tile.dataset.chapter ?? "");
      tile.toggleAttribute("data-dim", !chapter || !matches(chapter, filter));
    }
    root.querySelectorAll<HTMLButtonElement>("[data-filter]").forEach((b) => {
      const [kind, value] = (b.dataset.filter ?? ":").split(":") as [keyof Filter, string];
      b.setAttribute("aria-pressed", String(filter[kind] === value));
    });
  };

  const body = panel?.querySelector<HTMLElement>("[data-panel-body]");
  const title = panel?.querySelector<HTMLElement>("[data-panel-title]");
  const meta = panel?.querySelector<HTMLElement>("[data-panel-meta]");
  let opener: HTMLElement | null = null;

  const open = (chapter: Chapter, from: HTMLElement) => {
    if (!panel || !body || !labels) return;
    opener = from;
    tiles.forEach((t) => t.setAttribute("aria-pressed", String(t.dataset.chapter === chapter.id)));
    const classes = chapter.classes.length > 1
      ? fill(labels.classes, { a: chapter.classes[0] ?? "", b: chapter.classes[1] ?? "" })
      : fill(labels.class, { n: chapter.classes[0] ?? "" });
    if (meta) meta.textContent = `${labels.subjects[chapter.subject] ?? ""} · ${classes}`;
    if (title) title.textContent = chapter.name;
    const facts = element(doc, "p", chapter.main === null ? labels.advancedOnly : fill(labels.unit, { n: chapter.main }));
    facts.className = "syllabus-panel__facts";
    const parts: HTMLElement[] = [facts];
    for (const [heading, items] of [[labels.covers, chapter.topics], [labels.advancedAlso, chapter.advancedAlso]] as const) {
      if (!items?.length) continue;
      parts.push(element(doc, "h4", heading));
      const list = element(doc, "ul");
      for (const item of items) list.append(element(doc, "li", item));
      parts.push(list);
    }
    body.replaceChildren(...parts);
    panel.hidden = false;
    panel.querySelector<HTMLElement>("[data-panel-close]")?.focus({ preventScroll: true });
  };
  const close = () => {
    if (!panel || panel.hidden) return;
    panel.hidden = true;
    tiles.forEach((t) => t.setAttribute("aria-pressed", "false"));
    opener?.focus({ preventScroll: true });
  };

  // Esc, the Close button, or a tap outside the panel closes it.
  doc.addEventListener("keydown", (e) => e.key === "Escape" && close());
  doc.addEventListener("click", (e) => {
    const target = e.target as Element;
    if (panel && !panel.hidden && !panel.contains(target) && !target.closest("[data-chapter]")) close();
  });
  panel?.querySelector("[data-panel-close]")?.addEventListener("click", close);

  root.addEventListener("click", (e) => {
    const target = e.target as Element;
    const filterButton = target.closest<HTMLButtonElement>("[data-filter]");
    if (filterButton) {
      const [kind, value] = (filterButton.dataset.filter ?? ":").split(":") as [keyof Filter, string];
      filter[kind] = value;
      apply();
      return;
    }
    const tile = target.closest<HTMLButtonElement>("[data-chapter]");
    const chapter = tile ? byId.get(tile.dataset.chapter ?? "") : undefined;
    if (tile && chapter) open(chapter, tile);
  });
  apply();
}
