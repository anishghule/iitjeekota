/** The one script every page loads. Each island starts only where its section is on the page. */
import { initAreaMap } from "./area-map.ts";
import { initAutoscroll } from "./autoscroll.ts";
import { initBoard } from "./board.ts";
import { initCostCalc } from "./cost-calc.ts";
import { initEnquiry } from "./enquiry.ts";
import { initLiveTest } from "./live-test.ts";
import { initMenu } from "./nav.ts";
import { initPinning } from "./pin.ts";
import { initPortal } from "./portal.ts";
import { initReport } from "./report.ts";
import { initScenes } from "./scenes.ts";
import { initAllSteps } from "./steps.ts";
import { initSyllabus } from "./syllabus.ts";

const doc = window.document;
const each = <T extends HTMLElement>(selector: string, init: (el: T) => void) => doc.querySelectorAll<T>(selector).forEach(init);

initPinning(window);
initMenu(window);
each("[data-report]", initReport);
initAllSteps(window);
initScenes(window);
initAutoscroll(window);
each("[data-live-test]", (el) => initLiveTest(el, window));
each("[data-syllabus]", initSyllabus);
each("[data-area-map]", initAreaMap);
each("[data-cost-calc]", initCostCalc);
each<HTMLFormElement>("form[data-enquiry]", (form) => initEnquiry(form, window));
each("[data-portal]", (el) => {
  initPortal(el, window);
  initBoard(el, window);
});
