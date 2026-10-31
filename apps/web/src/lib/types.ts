/**
 * Shapes of the data make web-data writes (tools/dsapkit/src/dsapkit/web/export.py) and of the
 * widget data in packages/content/widgets. site.json, media.json and area-map.json are typed by
 * their JSON imports; pages, syllabi and widgets are typed here.
 */

/** A run of text; a link to a live page carries its path. */
export interface Part {
  text: string;
  path?: string;
}
export type Rich = Part[];

export type ActionKind = "page" | "call" | "whatsapp" | "enquire" | "directions";

export interface Action {
  to: ActionKind;
  label: string;
  path?: string;
}

export interface Question {
  q: string;
  a: Rich;
}

export interface SectionData {
  id: string;
  kind: "prose" | "list" | "faq";
  component?: string;
  heading: string;
  body: Rich[];
  points?: Rich[];
  questions?: Question[];
  action?: Action;
  widget?: unknown;
}

export interface Crumb {
  name: string;
  path: string;
}

export interface PageData {
  route: string;
  locale: string;
  template: string;
  status: "draft" | "ready";
  meta: { title: string; description: string; canonical: string; alternates: Record<string, string> };
  h1: string;
  intro: Rich[];
  breadcrumbs: Crumb[];
  sections: SectionData[];
  jsonld: unknown[];
}

export type SubjectId = "physics" | "chemistry" | "maths";

export interface Chapter {
  id: string;
  subject: SubjectId;
  symbol: string;
  classes: number[];
  name: string;
  main: number | null;
  advanced: string[];
  advancedOnly: boolean;
  topics?: string[];
  advancedAlso?: string[];
}

export interface SyllabusData {
  subjects: { id: SubjectId; name: string }[];
  chapters: Chapter[];
}

/* Widget data (packages/content/widgets/{locale}/{name}.json), resolved. */

export interface LiveTestData {
  minutes: number;
  marking: { right: number; wrong: number; blank: number };
  markingNote: string;
  questions: { subject: SubjectId; text: string; options: string[]; answer: number; solution: string }[];
}

export interface ReportWeek {
  test: string;
  marks: Record<SubjectId, number>;
  accuracy: number;
  minutesPerQuestion: number;
  lost: { careless: number; concept: number; time: number };
  focus: string[];
}

export interface ReportData {
  label: string;
  maxPerSubject: number;
  weeks: ReportWeek[];
}

export interface TimelineData {
  steps: { when: string; title: string; detail: string }[];
  rhythm: { every: string; what: string }[];
}

export interface ProgrammesData {
  rows: { route: string; for: string; length: string; exams: string }[];
}

/** One AI digital board demonstration; its maths is drawn by islands/board.ts, keyed by id. */
export interface BoardDemo {
  id: "area" | "volume" | "quiz" | "steps";
  tab: string;
  title: string;
  equation: string;
  words: Record<string, string>;
  seats?: string;
  options?: { key: string; text: string; share: number; right: boolean }[];
  steps?: { label: string; math: string }[];
}

export interface PortalData {
  title: string;
  label: string;
  live: { label: string; status: string; subject: string; sharing: string; joined: string };
  board: { label: string; demos: BoardDemo[] };
  tabs: { id: string; label: string; items: { title: string; meta: string }[] }[];
}
