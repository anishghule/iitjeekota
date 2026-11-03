/**
 * Autoscroll for pinned sections (plan C5).
 *
 * After the reader stops scrolling inside a section that opts in, the page keeps moving in the
 * same direction, at the speed they were scrolling (smoothed, then clamped), easing in. Any input
 * cancels it; it stops at the end of the section and waits for the reader to scroll again.
 *
 * This is pure logic: time, scroll position and sections come in through `tick` and the event
 * methods, and movement goes out through the port, so every rule is testable without a browser.
 */

export interface AutoscrollSettings {
  /** Quiet time after the last input before autoscroll starts. */
  pauseMs: number;
  /** Ease-in time from standing still to full speed. */
  rampMs: number;
  /** How far back scroll samples count towards the reader's speed. */
  velocityWindowMs: number;
  /** Slowest and fastest speed, in viewport heights per second. */
  minSpeed: number;
  maxSpeed: number;
}

/** A section that opted in (data-autoscroll), as page offsets in pixels. */
export interface Section {
  start: number;
  end: number;
}

export interface AutoscrollPort {
  /** Current scroll offset of the page, in pixels. */
  position(): number;
  /** Height of the viewport, in pixels. */
  viewportHeight(): number;
  /** The opted-in section the viewport is in, if any. */
  sectionAt(position: number): Section | null;
  /** Move the page by this many pixels. */
  scrollBy(pixels: number): void;
}

/** Why autoscroll may not run right now. Each holds until released. */
export type Blocker = "control-hover" | "field-focus" | "dialog-open" | "hidden";

export type AutoscrollState = "idle" | "armed" | "running";

interface Sample {
  t: number;
  y: number;
}

export class Autoscroll {
  private state: AutoscrollState = "idle";
  private enabled = true;
  private readonly blockers = new Set<Blocker>();
  private samples: Sample[] = [];
  private lastInputAt = Number.NEGATIVE_INFINITY;
  private direction: 1 | -1 = 1;
  private targetSpeed = 0; // pixels per millisecond
  private startedAt = 0;
  private lastTick: number | null = null;

  constructor(
    private readonly settings: AutoscrollSettings,
    private readonly port: AutoscrollPort,
  ) {}

  get current(): AutoscrollState {
    return this.state;
  }

  /** The reader's choice (the WCAG 2.2.2 toggle), and reduced motion: off means off. */
  setEnabled(on: boolean): void {
    this.enabled = on;
    if (!on) this.stop();
  }

  block(reason: Blocker): void {
    this.blockers.add(reason);
    this.stop();
  }

  release(reason: Blocker): void {
    this.blockers.delete(reason);
  }

  /** Wheel, touch, key, pointer down: the reader is driving. */
  input(t: number): void {
    this.lastInputAt = t;
    if (this.state === "running") this.stop();
  }

  /** A scroll event. While autoscroll is running the movement is ours, so it is not a sample. */
  scrolled(t: number): void {
    if (this.state === "running") return;
    const y = this.port.position();
    this.samples.push({ t, y });
    this.samples = this.samples.filter((s) => t - s.t <= this.settings.velocityWindowMs);
    this.lastInputAt = t;
    this.state = this.filling(y) && this.samples.length >= 2 ? "armed" : "idle";
  }

  /**
   * The section that fills the whole viewport at this position, if any. Only then does autoscroll
   * act: once the next section has come into view, the reader has left this one, and autoscroll
   * must not pull the page back to where the section ends.
   */
  private filling(y: number): Section | null {
    const section = this.port.sectionAt(y);
    return section && y >= section.start && y + this.port.viewportHeight() <= section.end ? section : null;
  }

  /** Call once per animation frame. */
  tick(t: number): void {
    const dt = this.lastTick === null ? 0 : t - this.lastTick;
    this.lastTick = t;
    if (!this.enabled || this.blockers.size > 0) return;
    if (this.state === "armed" && t - this.lastInputAt >= this.settings.pauseMs) this.start(t);
    if (this.state === "running") this.advance(t, dt);
  }

  private start(t: number): void {
    const first = this.samples[0];
    const last = this.samples[this.samples.length - 1];
    if (!first || !last || last.t === first.t || last.y === first.y) {
      this.state = "idle";
      return;
    }
    const pxPerMs = (last.y - first.y) / (last.t - first.t);
    const viewportsPerSecond = (Math.abs(pxPerMs) * 1000) / this.port.viewportHeight();
    const clamped = Math.min(this.settings.maxSpeed, Math.max(this.settings.minSpeed, viewportsPerSecond));
    this.direction = pxPerMs > 0 ? 1 : -1;
    this.targetSpeed = (clamped * this.port.viewportHeight()) / 1000;
    this.startedAt = t;
    this.state = "running";
  }

  private advance(t: number, dt: number): void {
    const y = this.port.position();
    const section = this.filling(y);
    if (!section) return this.stop();
    const ramp = Math.min(1, (t - this.startedAt) / this.settings.rampMs);
    const eased = ramp * ramp * (3 - 2 * ramp); // smoothstep: starts gently, arrives at full speed
    const step = this.direction * this.targetSpeed * eased * dt;
    // Stop where the section ends: its bottom meeting the viewport bottom, or its top meeting the viewport top.
    // Never against the reader's direction.
    const limit = this.direction > 0 ? Math.max(0, section.end - this.port.viewportHeight() - y) : Math.min(0, section.start - y);
    const bounded = this.direction > 0 ? Math.min(step, limit) : Math.max(step, limit);
    if (bounded !== 0) this.port.scrollBy(bounded);
    if (bounded !== step || limit === 0) this.stop();
  }

  private stop(): void {
    this.state = "idle";
    this.samples = [];
  }
}
