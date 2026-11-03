/**
 * The test map under the report (home, section report): one test read question by question. The
 * data is the report widget's testMap; everything the diagram shows (counts, chapter accuracy,
 * difficulty against result, bar sizes) is worked out here, so the component only draws.
 */

export const statuses = ["right", "slow", "wrong", "left"] as const;
export const difficulties = ["easy", "medium", "hard"] as const;

export type Status = (typeof statuses)[number];
export type Difficulty = (typeof difficulties)[number];

export interface MapQuestion {
  subject: string;
  chapter: string;
  difficulty: Difficulty;
  status: Status;
  /** The student's time on the question, and the class's average, in seconds. */
  seconds: number;
  average: number;
  /** How many times the student opened the question. */
  visits: number;
}

export interface TestMapData {
  test: string;
  questions: MapQuestion[];
}

export function tally(questions: readonly MapQuestion[]): Record<Status, number> {
  const counts: Record<Status, number> = { right: 0, slow: 0, wrong: 0, left: 0 };
  for (const q of questions) counts[q.status] += 1;
  return counts;
}

export interface ChapterAccuracy {
  chapter: string;
  total: number;
  attempted: number;
  correct: number;
}

/** Per chapter, in the order they first appear: how many questions, how many tried, how many right (slow ones count). */
export function chapterAccuracy(questions: readonly MapQuestion[]): ChapterAccuracy[] {
  const byChapter = new Map<string, ChapterAccuracy>();
  for (const q of questions) {
    const row = byChapter.get(q.chapter) ?? { chapter: q.chapter, total: 0, attempted: 0, correct: 0 };
    row.total += 1;
    if (q.status !== "left") row.attempted += 1;
    if (q.status === "right" || q.status === "slow") row.correct += 1;
    byChapter.set(q.chapter, row);
  }
  return [...byChapter.values()];
}

/** How many questions of each difficulty ended each way. */
export function difficultyMatrix(questions: readonly MapQuestion[]): Record<Difficulty, Record<Status, number>> {
  const matrix = Object.fromEntries(difficulties.map((d) => [d, { right: 0, slow: 0, wrong: 0, left: 0 }])) as Record<Difficulty, Record<Status, number>>;
  for (const q of questions) matrix[q.difficulty][q.status] += 1;
  return matrix;
}

/** The top of the seconds axis: the longest time on the chart, rounded up to a whole step. */
export function axisTop(questions: readonly MapQuestion[], step = 30): number {
  const longest = Math.max(1, ...questions.flatMap((q) => [q.seconds, q.average]));
  return Math.ceil(longest / step) * step;
}

export interface Chart {
  /** Width of one question's slot, and of its bar inside it; height of the bars' area; the room above it for revisit dots. */
  slot: number;
  bar: number;
  height: number;
  dots: number;
}

export interface Box {
  x: number;
  y: number;
  width: number;
  height: number;
}

/** Where question i's bar sits: standing on the baseline, as tall as its time is of the axis. */
export function barBox(i: number, seconds: number, top: number, chart: Chart): Box {
  const height = (Math.min(seconds, top) / top) * chart.height;
  return { x: i * chart.slot + (chart.slot - chart.bar) / 2, y: chart.dots + chart.height - height, width: chart.bar, height };
}

/** The y of the class-average mark for a question. */
export function averageY(average: number, top: number, chart: Chart): number {
  return chart.dots + chart.height - (Math.min(average, top) / top) * chart.height;
}
