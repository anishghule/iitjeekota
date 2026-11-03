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

/** A stored day (YYYY-MM-DD) as people read it in a page's language: 2 November 2026. Latin digits in every language, as the copy uses. */
export function formatDay(day: string, lang: string): string {
  const [year, month, date] = day.slice(0, 10).split("-").map(Number);
  return new Intl.DateTimeFormat(`${lang}-IN-u-nu-latn`, { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" })
    .format(new Date(Date.UTC(year ?? 1970, (month ?? 1) - 1, date ?? 1)));
}

/** A time of day written HH:MM in the facts, as it reads in a page's language: 7:00 am. */
export function clockLabel(time: string, lang: string): string {
  const [hour, minute] = time.split(":").map(Number);
  return new Intl.DateTimeFormat(`${lang}-IN-u-nu-latn`, { hour: "numeric", minute: "2-digit", timeZone: "UTC" })
    .format(new Date(Date.UTC(2024, 0, 1, hour ?? 0, minute ?? 0)));
}

const WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"] as const;

/** A day name from the opening-hours facts (Monday to Sunday) in a page's language. */
export function weekdayName(day: string, lang: string): string {
  const index = WEEK.indexOf(day as (typeof WEEK)[number]);
  return new Intl.DateTimeFormat(`${lang}-IN`, { weekday: "long", timeZone: "UTC" }).format(new Date(Date.UTC(2024, 0, 1 + Math.max(index, 0))));
}

/** Opening hours as lines: the days with the same times together, "Monday to Friday" where they run in a row. */
export function hoursLines(specs: { dayOfWeek: string[]; opens: string; closes: string }[], lang: string, to: string): { days: string; times: string }[] {
  return specs.map((s) => {
    const names = s.dayOfWeek.map((d) => weekdayName(d, lang));
    const days = s.dayOfWeek.length > 2 ? `${names[0]} ${to} ${names[names.length - 1]}` : names.join(", ");
    return { days, times: `${clockLabel(s.opens, lang)} ${to} ${clockLabel(s.closes, lang)}` };
  });
}
