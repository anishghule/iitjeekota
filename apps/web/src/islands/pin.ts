/**
 * Pins animated sections at every width (plan C5). Which sections autoscroll is a separate choice
 * (config/autoscroll.json, applied by islands/autoscroll.ts).
 * From the pin-from breakpoint (tokens.json layout.pin-from) the whole stage holds still, text
 * beside the visual: data-pin="wide". Below it the text scrolls past first and only the part
 * marked data-pin-visual holds still: data-pin="narrow". A section marked data-pin-wide-only has
 * no narrow layout (its visual is hidden there), so below the breakpoint it does not pin at all:
 * data-pin="off", and it scrolls like any other. Such a section can name a larger breakpoint of its
 * own (data-pin-wide-from="lg"): its visual is too small to read in a narrower slot, so below that
 * width it is off too. Without JavaScript nothing pins.
 * The same breakpoint sets data-layout ("wide" or "narrow") on the page, for sections that only
 * need to know which side they are on.
 */
import { tokens } from "@dsap/tokens";

type Breakpoint = keyof typeof tokens.breakpoint;

/** Fired on the window when sections switch between the wide and the narrow layout. */
export const PIN_CHANGE = "pinchange";

export function initPinning(win: Window): void {
  const from = tokens.layout["pin-from"] as Breakpoint;
  const query = win.matchMedia(`(width >= ${tokens.breakpoint[from]}px)`);
  // A section may need more width than the pin breakpoint gives it: one query per breakpoint it names.
  const own = new Map<string, MediaQueryList>();
  for (const section of win.document.querySelectorAll<HTMLElement>("[data-pin-wide-from]")) {
    const name = section.dataset.pinWideFrom as Breakpoint;
    if (!own.has(name)) own.set(name, win.matchMedia(`(width >= ${tokens.breakpoint[name]}px)`));
  }
  const apply = () => {
    win.document.documentElement.dataset.layout = query.matches ? "wide" : "narrow";
    for (const section of win.document.querySelectorAll<HTMLElement>(".pinned")) {
      const wideEnough = section.dataset.pinWideFrom ? (own.get(section.dataset.pinWideFrom)?.matches ?? true) : query.matches;
      const off = !wideEnough && section.hasAttribute("data-pin-wide-only");
      section.dataset.pin = off ? "off" : query.matches ? "wide" : "narrow";
    }
    win.dispatchEvent(new Event(PIN_CHANGE));
  };
  apply();
  query.addEventListener("change", apply);
  own.forEach((q) => q.addEventListener("change", apply));
}
