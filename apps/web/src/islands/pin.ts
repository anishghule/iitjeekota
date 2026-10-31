/**
 * Pins animated sections at every width (plan C5), and so gives them autoscroll everywhere.
 * From the pin-from breakpoint (tokens.json layout.pin-from) the whole stage holds still, text
 * beside the visual: data-pin="wide". Below it the text scrolls past first and only the part
 * marked data-pin-visual holds still: data-pin="narrow". Without JavaScript nothing pins.
 */
import { tokens } from "@dsap/tokens";

type Breakpoint = keyof typeof tokens.breakpoint;

/** Fired on the window when sections switch between the wide and the narrow layout. */
export const PIN_CHANGE = "pinchange";

export function initPinning(win: Window): void {
  const from = tokens.layout["pin-from"] as Breakpoint;
  const query = win.matchMedia(`(width >= ${tokens.breakpoint[from]}px)`);
  const apply = () => {
    for (const section of win.document.querySelectorAll<HTMLElement>(".pinned")) {
      section.dataset.pin = query.matches ? "wide" : "narrow";
      section.setAttribute("data-autoscroll", "");
    }
    win.dispatchEvent(new Event(PIN_CHANGE));
  };
  apply();
  query.addEventListener("change", apply);
}
