import { describe, expect, it } from "vitest";
import { tokens } from "@dsap/tokens";
import { Autoscroll, type AutoscrollPort, type AutoscrollSettings } from "../src/autoscroll.ts";

const settings: AutoscrollSettings = tokens.motion.autoscroll;
const VIEWPORT = 800;

/** A page with one opted-in section from 1000 to 5000 px. */
function page(start = 1000, end = 5000) {
  let y = 1200;
  const moves: number[] = [];
  const port: AutoscrollPort = {
    position: () => y,
    viewportHeight: () => VIEWPORT,
    sectionAt: (p) => (p >= start && p < end ? { start, end } : null),
    scrollBy: (px) => {
      y += px;
      moves.push(px);
    },
  };
  return { port, moves, set: (v: number) => (y = v), get: () => y };
}

/** The reader scrolls from y0 by `distance` pixels over `ms`, in 50 ms steps. */
function readerScrolls(auto: Autoscroll, p: ReturnType<typeof page>, t0: number, distance: number, ms: number) {
  const start = p.get();
  for (let t = 0; t <= ms; t += 50) {
    p.set(start + (distance * t) / ms);
    auto.scrolled(t0 + t);
  }
  return t0 + ms;
}

function frames(auto: Autoscroll, from: number, to: number) {
  for (let t = from; t <= to; t += 16) auto.tick(t);
}

describe("autoscroll", () => {
  it("waits for the pause, then keeps moving in the reader's direction", () => {
    const p = page();
    const auto = new Autoscroll(settings, p.port);
    const end = readerScrolls(auto, p, 0, 200, 200);
    frames(auto, end, end + settings.pauseMs - 20);
    expect(auto.current).toBe("armed");
    expect(p.moves).toHaveLength(0);
    frames(auto, end + settings.pauseMs, end + settings.pauseMs + 400);
    expect(auto.current).toBe("running");
    expect(p.moves.every((m) => m > 0)).toBe(true);
  });

  it("follows the reader upwards too", () => {
    const p = page();
    p.set(3000);
    const auto = new Autoscroll(settings, p.port);
    const end = readerScrolls(auto, p, 0, -150, 200);
    frames(auto, end, end + settings.pauseMs + 300);
    expect(p.moves.length).toBeGreaterThan(0);
    expect(p.moves.every((m) => m < 0)).toBe(true);
  });

  it("eases in, then holds a speed clamped between the token limits", () => {
    const p = page(1000, 40000);
    const auto = new Autoscroll(settings, p.port);
    const end = readerScrolls(auto, p, 0, 4000, 200); // far faster than maxSpeed
    frames(auto, end, end + settings.pauseMs + settings.rampMs + 500);
    const firstMove = p.moves[0] ?? 0;
    const lastMove = p.moves[p.moves.length - 1] ?? 0;
    expect(firstMove).toBeLessThan(lastMove);
    const maxPerFrame = (settings.maxSpeed * VIEWPORT * 16) / 1000;
    expect(lastMove).toBeCloseTo(maxPerFrame, 5);
  });

  it("is cancelled by any input and does not restart until the reader scrolls and pauses again", () => {
    const p = page();
    const auto = new Autoscroll(settings, p.port);
    const end = readerScrolls(auto, p, 0, 200, 200);
    frames(auto, end, end + settings.pauseMs + 100);
    expect(auto.current).toBe("running");
    auto.input(end + settings.pauseMs + 120);
    expect(auto.current).toBe("idle");
    const moves = p.moves.length;
    frames(auto, end + settings.pauseMs + 136, end + settings.pauseMs * 3);
    expect(p.moves).toHaveLength(moves);
  });

  it("stays still while a control is hovered, a field has focus or a dialog is open", () => {
    const p = page();
    const auto = new Autoscroll(settings, p.port);
    const end = readerScrolls(auto, p, 0, 200, 200);
    auto.block("field-focus");
    frames(auto, end, end + settings.pauseMs * 2);
    expect(p.moves).toHaveLength(0);
  });

  it("stops at the end of the section", () => {
    const p = page(1000, 2400);
    p.set(1500);
    const auto = new Autoscroll(settings, p.port);
    const end = readerScrolls(auto, p, 0, 100, 200);
    frames(auto, end, end + settings.pauseMs + 5000);
    expect(p.get()).toBeCloseTo(2400 - VIEWPORT, 5);
    expect(auto.current).toBe("idle");
  });

  it("leaves a section alone once the next one is coming into view, and never pulls the page back", () => {
    // Section 1000 to 2400: it fills the viewport only while y is between 1000 and 1600.
    const p = page(1000, 2400);
    p.set(1650);
    const auto = new Autoscroll(settings, p.port);
    const end = readerScrolls(auto, p, 0, 100, 200); // the reader is past 1600: the next section shows
    frames(auto, end, end + settings.pauseMs + 2000);
    expect(p.moves).toHaveLength(0);
    expect(p.get()).toBeCloseTo(1750, 5);
  });

  it("does nothing outside an opted-in section, or when switched off", () => {
    const outside = page(5000, 9000);
    const a = new Autoscroll(settings, outside.port);
    const end = readerScrolls(a, outside, 0, 200, 200);
    frames(a, end, end + settings.pauseMs * 2);
    expect(outside.moves).toHaveLength(0);

    const p = page();
    const b = new Autoscroll(settings, p.port);
    b.setEnabled(false);
    const end2 = readerScrolls(b, p, 0, 200, 200);
    frames(b, end2, end2 + settings.pauseMs * 2);
    expect(p.moves).toHaveLength(0);
  });
});
