/**
 * The sample test (home, section live-test): a JEE-style screen with a timer, a question palette,
 * mark for review, and a result with solutions. The section renders every question, the marking
 * and the labels; this module only keeps state.
 */
import { minutesAndSeconds } from "../lib/format.ts";

export interface Marking {
  right: number;
  wrong: number;
  blank: number;
}

export interface Score {
  right: number;
  wrong: number;
  left: number;
  marks: number;
  max: number;
}

/** answers[i] is the chosen option or null; key[i] is the right one. */
export function score(answers: (number | null)[], key: number[], marking: Marking): Score {
  let right = 0;
  let wrong = 0;
  key.forEach((correct, i) => {
    const chosen = answers[i];
    if (chosen === null || chosen === undefined) return;
    if (chosen === correct) right += 1;
    else wrong += 1;
  });
  const left = key.length - right - wrong;
  return { right, wrong, left, marks: right * marking.right + wrong * marking.wrong + left * marking.blank, max: key.length * marking.right };
}

export type PaletteState = "not-visited" | "not-answered" | "answered" | "marked" | "marked-answered";

export function paletteState(visited: boolean, answered: boolean, marked: boolean): PaletteState {
  if (marked) return answered ? "marked-answered" : "marked";
  if (answered) return "answered";
  return visited ? "not-answered" : "not-visited";
}

export function initLiveTest(root: HTMLElement, win: Window): void {
  const questions = Array.from(root.querySelectorAll<HTMLFieldSetElement>("[data-question]"));
  const palette = Array.from(root.querySelectorAll<HTMLButtonElement>("[data-palette]"));
  const tabs = Array.from(root.querySelectorAll<HTMLButtonElement>("[data-tab]"));
  const timer = root.querySelector<HTMLElement>("[data-timer]");
  const count = root.querySelector<HTMLElement>("[data-count]");
  const sheet = root.querySelector<HTMLElement>("[data-sheet]");
  const result = root.querySelector<HTMLElement>("[data-result]");
  const timeUp = root.querySelector<HTMLElement>("[data-time-up]");
  const marking: Marking = { right: Number(root.dataset.right), wrong: Number(root.dataset.wrong), blank: Number(root.dataset.blank) };
  const key = questions.map((q) => Number(q.dataset.answer));
  const seconds = Number(root.dataset.minutes) * 60;

  let current = 0;
  let marked = questions.map(() => false);
  let visited = questions.map((_, i) => i === 0);
  let left = seconds;
  let clock = 0;

  const chosen = (i: number): number | null => {
    const input = questions[i]?.querySelector<HTMLInputElement>("input:checked");
    return input ? Number(input.value) : null;
  };
  const render = () => {
    questions.forEach((q, i) => (q.hidden = i !== current));
    palette.forEach((p, i) => {
      p.dataset.state = paletteState(visited[i] ?? false, chosen(i) !== null, marked[i] ?? false);
      p.toggleAttribute("aria-current", i === current);
    });
    const subject = questions[current]?.dataset.subject;
    tabs.forEach((t) => t.setAttribute("aria-selected", String(t.dataset.tab === subject)));
    if (count) count.textContent = count.dataset.template?.replace("{n}", String(current + 1)) ?? "";
  };
  const go = (i: number) => {
    current = Math.max(0, Math.min(questions.length - 1, i));
    visited[current] = true;
    render();
  };
  const tick = () => {
    left -= 1;
    if (timer) timer.textContent = minutesAndSeconds(left);
    if (left <= 0) submit(true);
  };
  const start = () => {
    if (!clock) clock = win.setInterval(tick, 1000);
  };
  const submit = (outOfTime: boolean) => {
    win.clearInterval(clock);
    clock = 0;
    const answers = questions.map((_, i) => chosen(i));
    const s = score(answers, key, marking);
    for (const [name, value] of Object.entries(s)) {
      const out = root.querySelector<HTMLElement>(`[data-score="${name}"]`);
      if (out) out.textContent = String(value);
    }
    root.querySelectorAll<HTMLElement>("[data-review]").forEach((row, i) => {
      const a = answers[i];
      row.dataset.outcome = a === null || a === undefined ? "left" : a === key[i] ? "right" : "wrong";
      const mine = row.querySelector<HTMLElement>("[data-mine]");
      const letters = (row.dataset.letters ?? "").split(",");
      if (mine) mine.textContent = a === null || a === undefined ? "" : (letters[a] ?? "");
    });
    if (timeUp) timeUp.hidden = !outOfTime;
    if (sheet) sheet.hidden = true;
    if (result) {
      result.hidden = false;
      result.focus();
    }
  };
  const reset = () => {
    questions.forEach((q) => q.querySelectorAll<HTMLInputElement>("input").forEach((i) => (i.checked = false)));
    marked = questions.map(() => false);
    visited = questions.map((_, i) => i === 0);
    left = seconds;
    if (timer) timer.textContent = minutesAndSeconds(left);
    if (result) result.hidden = true;
    if (sheet) sheet.hidden = false;
    go(0);
  };

  root.addEventListener("change", () => {
    start();
    render();
  });
  root.addEventListener("click", (e) => {
    const target = (e.target as Element).closest<HTMLElement>("[data-action], [data-palette], [data-tab]");
    if (!target) return;
    start();
    if (target.dataset.palette !== undefined) return go(Number(target.dataset.palette));
    if (target.dataset.tab !== undefined) return go(questions.findIndex((q) => q.dataset.subject === target.dataset.tab));
    switch (target.dataset.action) {
      case "mark":
        marked[current] = true;
        return go(current + 1 < questions.length ? current + 1 : current);
      case "clear":
        questions[current]?.querySelectorAll<HTMLInputElement>("input").forEach((i) => (i.checked = false));
        marked[current] = false;
        return render();
      case "next":
        marked[current] = false;
        return go(current + 1 < questions.length ? current + 1 : current);
      case "submit":
        return submit(false);
      case "again":
        return reset();
    }
  });
  root.dataset.ready = "";
  if (timer) timer.textContent = minutesAndSeconds(left);
  render();
}
