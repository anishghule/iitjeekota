import { fill, type UiStrings } from "../i18n/index.ts";
import type { HeadData } from "./types.ts";

/** The not-found page is no page of the site: it has no route, no address of its own and no language versions. */
export const NOT_FOUND_ROUTE = "not-found";

export function notFoundHead(t: UiStrings["notFound"], brand: string): HeadData {
  return {
    route: NOT_FOUND_ROUTE,
    meta: { title: fill(t.title, { brand }), description: fill(t.description, { brand }) },
    jsonld: [],
  };
}
