import en from "./en.json";
import hi from "./hi.json";
import mr from "./mr.json";

/** English defines the keys; the type check fails when another language misses one. */
export type UiStrings = typeof en;

const ui = { en, hi: hi satisfies UiStrings, mr: mr satisfies UiStrings } as const;

export type Locale = keyof typeof ui;
export const locales = Object.keys(ui) as Locale[];

export function isLocale(value: string | undefined): value is Locale {
  return value !== undefined && value in ui;
}

export function strings(locale: Locale): UiStrings {
  return ui[locale];
}

export { fill } from "../lib/format.ts";
