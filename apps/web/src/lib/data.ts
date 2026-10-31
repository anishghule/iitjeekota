/**
 * The site's data, as make web-data wrote it. Pages and layouts read data only through here;
 * islands never do (they read what a section renders into the page).
 */
import site from "../generated/data/site.json";
import media from "../generated/data/media.json";
import areaMap from "../generated/data/area-map.json";
import { locales, type Locale } from "../i18n/index.ts";
import type { PageData, SyllabusData } from "./types.ts";

const pageFiles = import.meta.glob<PageData>("../generated/data/pages/*/*.json", { eager: true, import: "default" });
const syllabusFiles = import.meta.glob<SyllabusData>("../generated/data/syllabus/*.json", { eager: true, import: "default" });

const siteLocales = site.locales.map((l) => l.code);
if (siteLocales.join() !== locales.join()) {
  throw new Error(`packages/site/site.json locales (${siteLocales.join()}) and apps/web/src/i18n (${locales.join()}) differ`);
}

export type Site = typeof site;
export type RouteId = keyof Site["routes"];
export type Centre = Site["centres"][number];
export type Area = Site["areas"][number];
export type MediaSlotId = keyof typeof media.slots;
export type AreaMap = typeof areaMap;

export { site, areaMap };

export function pages(): PageData[] {
  return Object.values(pageFiles);
}

export function page(locale: Locale, route: string): PageData | undefined {
  return pageFiles[`../generated/data/pages/${locale}/${route}.json`];
}

export function syllabus(locale: Locale): SyllabusData {
  const data = syllabusFiles[`../generated/data/syllabus/${locale}.json`];
  if (!data) throw new Error(`no syllabus for ${locale}: run make web-data`);
  return data;
}

/** The path of a page in a language, or undefined when that page is not live there. */
export function routePath(id: RouteId, locale: Locale): string | undefined {
  const paths: Partial<Record<string, string>> = site.routes[id].paths;
  return paths[locale];
}

export function routeName(id: RouteId, locale: Locale): string {
  const names: Partial<Record<string, string>> = site.routes[id].names;
  return names[locale] ?? names[site.defaultLocale] ?? id;
}

export function isRouteId(id: string): id is RouteId {
  return id in site.routes;
}

/** Live pages with a nav number, in that order, with their short link text (packages/site/routes.json). */
export function navRoutes(locale: Locale): { id: RouteId; path: string; name: string }[] {
  return (Object.keys(site.routes) as RouteId[])
    .map((id) => ({ id, nav: site.routes[id].nav as number | null, path: routePath(id, locale) }))
    .filter((r): r is { id: RouteId; nav: number; path: string } => r.nav !== null && r.path !== undefined)
    .sort((a, b) => a.nav - b.nav)
    .map(({ id, path }) => ({ id, path, name: localName(site.routes[id].navNames, locale) }));
}

type Facts = Site["facts"]["en"];

/** A confirmed fact as it reads in a language; undefined while pending or untranslated. */
export function fact<K extends keyof Facts>(locale: Locale, id: K): Facts[K] | undefined {
  const facts: Partial<Facts> = site.facts[locale];
  return facts[id];
}

export function brandName(locale: Locale): string {
  return site.brand.names[locale];
}

export function localName(names: Partial<Record<string, string>>, locale: Locale): string {
  return names[locale] ?? names[site.defaultLocale] ?? "";
}

export interface MediaFile {
  url: string;
  width: number;
  height: number;
  alt: string;
}

/** A media slot's file, or undefined while D-SAP has not supplied it. */
export function mediaFile(id: MediaSlotId, locale: Locale): MediaFile | undefined {
  const slot: { url?: string; width?: number; height?: number; alt: Partial<Record<string, string>> } = media.slots[id];
  if (!slot.url || !slot.width || !slot.height) return undefined;
  return { url: slot.url, width: slot.width, height: slot.height, alt: localName(slot.alt, locale) };
}

/** A contact link pattern from packages/site/site.json (contactLinks) with its values filled. */
export function contactLink(pattern: keyof Site["contact"]["links"], values: Record<string, string | number>): string {
  return site.contact.links[pattern].replace(/\{(\w+)\}/g, (whole, key: string) => String(values[key] ?? whole));
}
