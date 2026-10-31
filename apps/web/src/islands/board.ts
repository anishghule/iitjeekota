/**
 * The AI digital board demonstrations (home, section portal), after v3.2's board: area under a
 * curve, a solid of revolution, a live quiz and the AI step solver. Each plays for its duration,
 * then the next; picking one holds it for a while. Under reduced motion each shows its finished
 * frame. Words come from the portal widget (a JSON block the section renders), sizes and timings
 * from config/board.json, colours and fonts from the surface roles of the page.
 */
import board from "../config/board.json";
import { readMotionPrefs } from "@dsap/motion";
import { readJson } from "../lib/format.ts";
import type { BoardDemo } from "../lib/types.ts";

type G = CanvasRenderingContext2D;
type Size = keyof typeof board.type;

interface Paint {
  bg: string;
  line: string;
  axis: string;
  text: string;
  muted: string;
  accent: string;
  strong: string;
  fill: string;
  ok: string;
  body: string;
  display: string;
}

const ease = (x: number) => {
  const c = Math.max(0, Math.min(1, x));
  return c * c * (3 - 2 * c);
};
/** Where t is between a and b, from 0 to 1. */
const seg = (t: number, a: number, b: number) => Math.max(0, Math.min(1, (t - a) / (b - a)));

function readPaint(el: Element): Paint {
  const css = getComputedStyle(el);
  const v = (name: string) => css.getPropertyValue(name).trim();
  return {
    bg: v("--bg-sunken"), line: v("--bg-raised"), axis: v("--text-muted"), text: v("--text"), muted: v("--text-muted"),
    accent: v("--accent"), strong: v("--accent-text"), fill: v("--river"), ok: v("--ok"),
    body: v("--font-body"), display: v("--font-display"),
  };
}

class Painter {
  constructor(readonly g: G, readonly p: Paint) {}

  font(size: Size, weight = 500, family: "body" | "display" = "body"): string {
    return `${weight} ${board.type[size]}px ${family === "body" ? this.p.body : this.p.display}`;
  }

  text(s: string, x: number, y: number, font: string, colour: string, align: CanvasTextAlign = "left"): void {
    const { g } = this;
    g.font = font;
    g.fillStyle = colour;
    g.textAlign = align;
    g.fillText(s, x, y);
  }

  background(): void {
    const { g, p } = this;
    g.clearRect(0, 0, board.width, board.height);
    g.fillStyle = p.bg;
    g.fillRect(0, 0, board.width, board.height);
    g.strokeStyle = p.line;
    g.lineWidth = 1;
    g.beginPath();
    for (let x = 0; x < board.width; x += board.grid) {
      g.moveTo(x, 0);
      g.lineTo(x, board.height);
    }
    for (let y = 0; y < board.height; y += board.grid) {
      g.moveTo(0, y);
      g.lineTo(board.width, y);
    }
    g.stroke();
  }

  faded(alpha: number, draw: () => void): void {
    const before = this.g.globalAlpha;
    this.g.globalAlpha = before * alpha;
    draw();
    this.g.globalAlpha = before;
  }
}

/* Area under a curve: Riemann strips that narrow towards the integral. */
const f = (x: number) => 1 + 0.55 * Math.sin(1.3 * x) + 0.07 * x * x;
const trueArea = (() => {
  const n = 4000;
  const h = 5 / n;
  let s = f(0) + f(5);
  for (let i = 1; i < n; i++) s += f(i * h) * (i % 2 ? 4 : 2);
  return (s * h) / 3; // Simpson's rule
})();

function area(d: Painter, t: number, demo: BoardDemo): void {
  const { g, p } = d;
  const w = demo.words;
  const ox = 150, oy = 600, pw = 760, ph = 400;
  const X = (x: number) => ox + (x / 5) * pw;
  const Y = (y: number) => oy - (y / 3.6) * ph;
  d.background();
  g.strokeStyle = p.axis;
  g.lineWidth = 2;
  g.beginPath();
  g.moveTo(ox, oy + 10);
  g.lineTo(ox, oy - ph - 20);
  g.moveTo(ox - 10, oy);
  g.lineTo(ox + pw + 30, oy);
  g.stroke();
  for (let i = 1; i <= 5; i++) d.text(String(i), X(i), oy + 34, d.font("small"), p.muted, "center");
  const drawn = ease(seg(t, 0, 0.16));
  const n = Math.round(4 + ease(seg(t, 0.16, 0.7)) * 44);
  const strips = seg(t, 0.12, 0.2);
  const finish = ease(seg(t, 0.72, 0.9));
  const dx = 5 / n;
  let sum = 0;
  for (let k = 0; k < n; k++) {
    const x = k * dx;
    const h = f(x);
    sum += h * dx;
    if (strips <= 0) continue;
    d.faded(0.3 * strips * (1 - finish * 0.55), () => {
      g.fillStyle = p.fill;
      g.fillRect(X(x), Y(h), X(dx) - ox - 0.5, oy - Y(h));
    });
    d.faded(0.9 * strips, () => {
      g.strokeStyle = p.fill;
      g.lineWidth = n > 30 ? 0.6 : 1.2;
      g.strokeRect(X(x), Y(h), X(dx) - ox, oy - Y(h));
    });
  }
  if (finish > 0) {
    g.beginPath();
    g.moveTo(X(0), oy);
    for (let s = 0; s <= 200; s++) g.lineTo(X((s / 200) * 5), Y(f((s / 200) * 5)));
    g.lineTo(X(5), oy);
    g.closePath();
    d.faded(0.32 * finish, () => {
      g.fillStyle = p.accent;
      g.fill();
    });
  }
  g.beginPath();
  const last = Math.floor(drawn * 200);
  for (let s = 0; s <= last; s++) {
    const x = (s / 200) * 5;
    if (s) g.lineTo(X(x), Y(f(x)));
    else g.moveTo(X(x), Y(f(x)));
  }
  g.strokeStyle = p.accent;
  g.lineWidth = 4;
  g.stroke();
  d.text(w.function ?? "", ox + 20, oy - ph - 4, d.font("body"), p.strong);
  const px = 960;
  d.text(w.sum ?? "", px, 190, d.font("label", 700), p.strong);
  d.text(`n = ${n}`, px, 250, d.font("number", 800, "display"), p.text);
  d.text(`Σ f(xᵢ)Δx ≈ ${sum.toFixed(3)}`, px, 300, d.font("equation"), p.muted);
  d.text(`${w.error ?? ""}  ${Math.abs(sum - trueArea).toFixed(3)}`, px, 336, d.font("small"), p.muted);
  if (finish > 0.2) {
    d.faded(finish, () => {
      d.text(w.limit ?? "", px, 410, d.font("equation"), p.ok);
      d.text(`∫ f(x) dx = ${trueArea.toFixed(3)}`, px, 460, d.font("equation", 600), p.strong);
      d.text(w.note ?? "", 90, 680, d.font("small"), p.muted);
    });
  }
}

/* Solid of revolution: discs under y = √x turned about the x-axis. */
function volume(d: Painter, t: number, demo: BoardDemo): void {
  const { g, p } = d;
  const w = demo.words;
  const oy = 400, ox = 140, sx = 190, sy = 150;
  const fx = (x: number) => Math.sqrt(x);
  const X = (x: number) => ox + x * sx;
  const shift = 440;
  d.background();
  g.strokeStyle = p.axis;
  g.lineWidth = 2;
  g.beginPath();
  g.moveTo(ox - 20, oy);
  g.lineTo(X(4) + 60, oy);
  g.moveTo(ox, oy + 190);
  g.lineTo(ox, oy - 220);
  g.stroke();
  const drawn = ease(seg(t, 0, 0.22));
  const shown = ease(seg(t, 0.25, 0.8));
  const discs = Math.round(2 + shown * 38);
  const N = Math.floor(drawn * 160);
  g.beginPath();
  g.moveTo(X(0), oy);
  for (let i = 0; i <= N; i++) g.lineTo(X((i / 160) * 4), oy - fx((i / 160) * 4) * sy);
  g.lineTo(X((N / 160) * 4), oy);
  g.closePath();
  d.faded(0.14, () => {
    g.fillStyle = p.accent;
    g.fill();
  });
  g.beginPath();
  for (let i = 0; i <= N; i++) {
    const x = (i / 160) * 4;
    if (i) g.lineTo(X(x), oy - fx(x) * sy);
    else g.moveTo(X(x), oy - fx(x) * sy);
  }
  g.strokeStyle = p.accent;
  g.lineWidth = 4;
  g.stroke();
  d.text(w.function ?? "", X(3.3), oy - 2.1 * sy, d.font("equation"), p.strong);
  const dx = 4 / discs;
  let vol = 0;
  for (let k = 0; k < discs; k++) {
    const xc = (k + 0.5) * dx;
    const r = fx(xc) * sy;
    vol += Math.PI * xc * dx; // f(x)² = x
    if (k / discs > shown + 0.001) continue;
    g.beginPath();
    g.ellipse(X(xc) + shift, oy, 0.2 * r + 4, r, 0, 0, 2 * Math.PI);
    d.faded(0.08 + 0.12 * (k / discs), () => {
      g.fillStyle = p.fill;
      g.fill();
    });
    d.faded(discs > 25 ? 0.35 : 0.8, () => {
      g.strokeStyle = p.accent;
      g.lineWidth = 1;
      g.stroke();
    });
  }
  const rr = fx(4) * sy;
  const a = t * 2 * Math.PI * 3;
  g.beginPath();
  g.arc(X(4) + shift + Math.cos(a) * 0.2 * rr, oy + Math.sin(a) * rr, 7, 0, 2 * Math.PI);
  g.fillStyle = p.strong;
  g.fill();
  g.setLineDash([6, 6]);
  g.strokeStyle = p.muted;
  g.beginPath();
  g.moveTo(X(0) + shift, oy);
  g.lineTo(X(4) + shift + 60, oy);
  g.stroke();
  g.setLineDash([]);
  d.text(w.rotate ?? "", X(2) + shift, oy + 230, d.font("body"), p.muted, "center");
  d.text(`${w.discs ?? ""}  ${discs}`, 160, 130, d.font("label", 700), p.strong);
  d.text(`V ≈ ${vol.toFixed(2)}`, 160, 190, d.font("number", 800, "display"), p.text);
  if (t > 0.82) d.faded(ease(seg(t, 0.82, 0.95)), () => d.text(w.exact ?? "", 160, 236, d.font("equation"), p.ok));
}

/* Live quiz: the class answers a poll, then the right option is shown. */
function quiz(d: Painter, t: number, demo: BoardDemo): void {
  const { g, p } = d;
  const w = demo.words;
  const seats = Number(demo.seats) || 0;
  d.background();
  d.text(w.poll ?? "", 90, 100, d.font("label", 700), p.strong);
  d.text(w.question ?? "", 90, 170, d.font("number", 600), p.text);
  const grow = ease(seg(t, 0.1, 0.7));
  const reveal = ease(seg(t, 0.72, 0.85));
  (demo.options ?? []).forEach((o, i) => {
    const y = 240 + i * 92;
    d.faded(0.6, () => {
      g.fillStyle = p.line;
      g.fillRect(90, y, 700, 62);
    });
    d.faded(o.right && reveal > 0 ? 0.5 + 0.4 * reveal : 0.45, () => {
      g.fillStyle = o.right && reveal > 0 ? p.ok : p.accent;
      g.fillRect(90, y, 700 * (o.share / 100) * grow, 62);
    });
    d.text(o.key, 112, y + 41, d.font("label", 600), p.strong);
    d.text(o.text, 160, y + 42, d.font("equation"), p.text);
    d.text(`${Math.round(o.share * grow)}%`, 770, y + 41, d.font("label", 600), p.muted, "right");
    if (o.right && reveal > 0.2) {
      g.strokeStyle = p.ok;
      g.lineWidth = 3;
      g.strokeRect(90, y, 700, 62);
    }
  });
  const answered = Math.round(seats * ease(seg(t, 0.05, 0.65)) * 0.9);
  d.text(`${w.answered ?? ""}  ${answered} / ${seats}`, 900, 250, d.font("label", 700), p.strong);
  for (let s = 0; s < seats; s++) {
    g.beginPath();
    g.arc(910 + (s % 6) * 52, 300 + Math.floor(s / 6) * 52, 16, 0, 2 * Math.PI);
    g.fillStyle = s < answered ? p.ok : p.line;
    g.fill();
  }
  if (reveal > 0.5) d.faded(reveal, () => d.text(w.rule ?? "", 90, 640, d.font("body"), p.muted));
  d.text(w.note ?? "", 90, 690, d.font("small"), p.muted);
}

/* AI step solver: the substitution, one step at a time, then a check. */
function steps(d: Painter, t: number, demo: BoardDemo): void {
  const { g, p } = d;
  const w = demo.words;
  const list = demo.steps ?? [];
  d.background();
  d.text(w.solver ?? "", 90, 100, d.font("label", 700), p.strong);
  d.text(demo.equation, 90, 190, d.font("problem", 600), p.text);
  list.forEach((s, i) => {
    const start = 0.12 + i * (0.7 / Math.max(1, list.length));
    const shown = ease(seg(t, start, start + 0.1));
    if (shown <= 0) return;
    const y = 290 + i * 76;
    d.faded(shown, () => {
      d.faded(0.25, () => {
        g.fillStyle = p.accent;
        g.fillRect(90, y - 38, 760, 58);
      });
      d.text(String(i + 1), 112, y, d.font("label", 600), p.strong);
      d.text(s.label, 160, y - 18, d.font("small", 600), p.muted);
      d.text(s.math.slice(0, Math.ceil(s.math.length * shown)), 160, y + 8, d.font("equation"), p.text);
    });
  });
  const check = ease(seg(t, 0.88, 0.97));
  if (check > 0) {
    d.faded(check, () => {
      g.strokeStyle = p.ok;
      g.lineWidth = 3;
      g.strokeRect(90, 650, 760, 46);
      d.text(w.check ?? "", 112, 683, d.font("body"), p.ok);
    });
  }
  const pulse = 0.5 + 0.5 * Math.sin(t * 2 * Math.PI * 6);
  g.beginPath();
  g.arc(1010, 230, 46, 0, 2 * Math.PI);
  d.faded(0.3 + 0.4 * pulse, () => {
    g.strokeStyle = p.accent;
    g.lineWidth = 2;
    g.stroke();
  });
  g.beginPath();
  g.arc(1010, 230, 28, 0, 2 * Math.PI);
  g.fillStyle = p.accent;
  g.fill();
  d.text(w.badge ?? "", 1010, 240, d.font("label", 700), p.bg, "center");
  d.text(w.steers ?? "", 960, 330, d.font("body"), p.muted);
  d.text(w.shows ?? "", 960, 362, d.font("body"), p.muted);
}

const DRAW: Record<string, (d: Painter, t: number, demo: BoardDemo) => void> = { area, volume, quiz, steps };

export function initBoard(root: HTMLElement, win: Window): void {
  const demos = readJson<BoardDemo[]>(root, "script[data-board]") ?? [];
  const canvas = root.querySelector<HTMLCanvasElement>("[data-board-canvas]");
  const g = canvas?.getContext("2d");
  if (!canvas || !g || demos.length === 0) return;
  const tabs = Array.from(root.querySelectorAll<HTMLButtonElement>("[data-demo]"));
  const title = root.querySelector<HTMLElement>("[data-board-title]");
  const equation = root.querySelector<HTMLElement>("[data-board-equation]");
  const bar = root.querySelector<HTMLElement>("[data-board-progress]");
  const still = readMotionPrefs(win).reducedMotion;
  const durations: Record<string, number> = board.durationMs;
  let painter: Painter | null = null;
  let current = 0;
  let startedAt = win.performance.now();
  let heldUntil = 0;
  let visible = false;
  let frame = 0;

  const draw = (t: number) => {
    painter ??= new Painter(g, readPaint(canvas));
    const demo = demos[current];
    if (demo) DRAW[demo.id]?.(painter, t, demo);
    bar?.style.setProperty("--progress", t.toFixed(3));
  };
  const select = (i: number) => {
    current = (i + demos.length) % demos.length;
    startedAt = win.performance.now();
    const demo = demos[current];
    tabs.forEach((tab, k) => tab.setAttribute("aria-pressed", String(k === current)));
    if (title) title.textContent = demo?.title ?? "";
    if (equation) equation.textContent = demo?.equation ?? "";
    if (still) draw(1);
  };
  const tick = (now: number) => {
    frame = 0;
    if (!visible || still) return;
    const demo = demos[current];
    const t = (now - startedAt) / (durations[demo?.id ?? ""] ?? board.durationMs.area);
    if (t >= 1 && now >= heldUntil) select(current + 1);
    else draw(Math.min(1, t));
    frame = win.requestAnimationFrame(tick);
  };

  tabs.forEach((tab, i) =>
    tab.addEventListener("click", () => {
      heldUntil = win.performance.now() + board.pauseAfterPickMs;
      select(i);
    }),
  );
  new IntersectionObserver(([entry]) => {
    visible = entry?.isIntersecting ?? false;
    if (visible && !frame && !still) frame = win.requestAnimationFrame(tick);
  }).observe(canvas);
  win.document.fonts?.ready.then(() => {
    painter = null; // fonts are in: measure again with the real faces
    if (still) draw(1);
  });
  select(0);
}
