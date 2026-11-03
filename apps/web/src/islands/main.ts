/** The one script every page loads. Each island starts only where its section is on the page. */
import { initAreaMap } from "./area-map.ts";
import { initAutoscroll } from "./autoscroll.ts";
import { initBoard } from "./board.ts";
import { initFilm } from "./film.ts";
import { initGallery } from "./gallery.ts";
import { initCostCalc } from "./cost-calc.ts";
import { initEnquiry } from "./enquiry.ts";
import { initLiveTest } from "./live-test.ts";
import { initLangMenus } from "./lang-menu.ts";
import { initMenu } from "./nav.ts";
import { initPinning } from "./pin.ts";
import { initPortal } from "./portal.ts";
import { initReport } from "./report.ts";
import { initScenes } from "./scenes.ts";
import { initAllSteps } from "./steps.ts";
import { initSyllabus } from "./syllabus.ts";
import { initTestMap } from "./test-map.ts";
import { initTimeline } from "./timeline.ts";

const doc = window.document;
const each = <T extends HTMLElement>(selector: string, init: (el: T) => void) => doc.querySelectorAll<T>(selector).forEach(init);

initPinning(window);
initMenu(window);
initLangMenus(window);
each("[data-report]", initReport);
each("[data-film-player]", initFilm);
initAllSteps(window);
initScenes(window);
initAutoscroll(window);
each("[data-live-test]", (el) => initLiveTest(el, window));
each("[data-test-map]", initTestMap);
each("[data-syllabus]", (el) => initSyllabus(el, window));
each("[data-timeline]", (el) => initTimeline(el, window));
each("[data-area-map]", initAreaMap);
each("[data-cost-calc]", initCostCalc);
each("[data-gallery]", (el) => initGallery(el, window));
each<HTMLFormElement>("form[data-enquiry]", (form) => initEnquiry(form, window));
each("[data-portal]", (el) => {
  initPortal(el, window);
  initBoard(el, window);
});
