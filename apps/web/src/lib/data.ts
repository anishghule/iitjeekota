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

export interface AreaGroup {
  name: string;
  path: string;
  areas: { name: string; path: string }[];
}

/** Each area hub page (Pune, Pimpri-Chinchwad) with the live area pages under it, for the footer. */
export function areaGroups(locale: Locale): AreaGroup[] {
  const groups: AreaGroup[] = [];
  for (const id of Object.keys(site.routes) as RouteId[]) {
    const hub = site.routes[id].areaHub;
    const path = routePath(id, locale);
    if (!hub || path === undefined) continue;
    const areas = site.areas
      .filter((a) => a.hub === hub)
      .flatMap((a) => (a.page && isRouteId(a.page) ? [{ name: localName(a.names, locale), path: routePath(a.page, locale) }] : []))
      .filter((a): a is { name: string; path: string } => a.path !== undefined);
    groups.push({ name: routeName(id, locale), path, areas });
  }
  return groups;
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

/** The brand name split where the wide header breaks it onto two lines. */
export function brandLines(locale: Locale): readonly string[] {
  return site.brand.nameLines[locale];
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

export function isMediaSlotId(id: string): id is MediaSlotId {
  return id in media.slots;
}

/** A media slot's file, or undefined while D-SAP has not supplied it (or the slot does not exist). */
export function mediaFile(id: MediaSlotId, locale: Locale): MediaFile | undefined {
  const slot: { url?: string; width?: number; height?: number; alt: Partial<Record<string, string>> } | undefined = media.slots[id];
  if (!slot?.url || !slot.width || !slot.height) return undefined;
  return { url: slot.url, width: slot.width, height: slot.height, alt: localName(slot.alt, locale) };
}

/** The centre a centre page is about. */
export function centreOfRoute(route: string): Centre | undefined {
  return site.centres.find((c) => c.page === route);
}

/** The area an area page is about. */
export function areaOfRoute(route: string): Area | undefined {
  return site.areas.find((a) => a.page === route);
}

const CENTRE_PHOTOS = ["entrance", "classroom", "digital-board"] as const;
const CENTRE_FILMS = ["walkthrough", "parent-meeting"] as const;

/** What a centre has to show, from the media slots D-SAP has filled: photos, and films each with its still. */
export function centreMedia(centre: string, locale: Locale): { photos: MediaFile[]; films: { film: MediaFile; poster?: MediaFile | undefined }[] } {
  const slot = (name: string) => mediaFile(`centres/${centre}/${name}` as MediaSlotId, locale);
  const photos = CENTRE_PHOTOS.map(slot).filter((m): m is MediaFile => m !== undefined);
  const films = CENTRE_FILMS.flatMap((name) => {
    const film = slot(name);
    return film ? [{ film, poster: slot(`${name}-poster`) }] : [];
  });
  return { photos, films };
}

/** A contact link pattern from packages/site/site.json (contactLinks) with its values filled. */
export function contactLink(pattern: keyof Site["contact"]["links"], values: Record<string, string | number>): string {
  return site.contact.links[pattern].replace(/\{(\w+)\}/g, (whole, key: string) => String(values[key] ?? whole));
}
