/**
 * The Kota or Pune cost sum under the programmes. The parent types the amounts they were quoted;
 * nothing leaves the page and nothing is assumed.
 */
import { fill, rupees } from "../lib/format.ts";

export type Comparison = { kind: "empty" } | { kind: "same" } | { kind: "kotaMore" | "puneMore"; amount: number };

export function compare(kota: number, pune: number, filled: { kota: boolean; pune: boolean }): Comparison {
  if (!filled.kota || !filled.pune) return { kind: "empty" };
  if (kota === pune) return { kind: "same" };
  return kota > pune ? { kind: "kotaMore", amount: kota - pune } : { kind: "puneMore", amount: pune - kota };
}

export function initCostCalc(root: HTMLElement): void {
  const lang = root.ownerDocument.documentElement.lang;
  const out = root.querySelector<HTMLOutputElement>("[data-result]");
  const side = (name: string) => {
    const inputs = Array.from(root.querySelectorAll<HTMLInputElement>(`[data-side="${name}"]`));
    const values = inputs.map((i) => Math.max(0, Number(i.value) || 0));
    return { total: values.reduce((a, b) => a + b, 0), filled: inputs.some((i) => i.value.trim() !== "") };
  };
  const update = () => {
    const kota = side("kota");
    const pune = side("pune");
    root.querySelectorAll<HTMLOutputElement>("[data-total]").forEach((o) => {
      o.textContent = rupees(o.dataset.total === "kota" ? kota.total : pune.total, lang);
    });
    if (!out) return;
    const result = compare(kota.total, pune.total, { kota: kota.filled, pune: pune.filled });
    const template = out.dataset[result.kind] ?? "";
    out.textContent = "amount" in result ? fill(template, { amount: rupees(result.amount, lang) }) : template;
  };
  root.addEventListener("input", update);
  update();
}
