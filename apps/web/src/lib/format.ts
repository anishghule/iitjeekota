/** Text helpers shared by pages and islands. No data imports, so islands stay small. */

/** Fills {name} placeholders in a UI string. */
export function fill(template: string, values: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (whole, key: string) => {
    const value = values[key];
    return value === undefined ? whole : String(value);
  });
}

/** Splits a UI string at its {name} placeholders, so a page can put an element where each goes. */
export function templateParts(template: string): ({ text: string } | { key: string })[] {
  return template
    .split(/(\{\w+\})/)
    .filter((s) => s !== "")
    .map((s) => (/^\{\w+\}$/.test(s) ? { key: s.slice(1, -1) } : { text: s }));
}

/** Indian number grouping for a page's language (en-IN, hi-IN, mr-IN). */
export function rupees(amount: number, lang: string): string {
  return new Intl.NumberFormat(`${lang}-IN`, { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(amount);
}

export function minutesAndSeconds(seconds: number): string {
  const s = Math.max(0, Math.round(seconds));
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

/** Reads a JSON block a section rendered for its island (type="application/json"). */
export function readJson<T>(root: ParentNode, selector: string): T | undefined {
  const text = root.querySelector(selector)?.textContent;
  return text ? (JSON.parse(text) as T) : undefined;
}
