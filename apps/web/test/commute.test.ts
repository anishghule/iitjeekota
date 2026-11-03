import { describe, expect, it } from "vitest";
import { travelTime } from "../src/lib/commute.ts";

const words = { range: "{from} to {to} minutes", freeFlow: "about {min} minutes on empty roads" };

describe("how long a trip takes", () => {
  it("says a time measured at class hours as a range", () => {
    expect(travelTime({ km: 8.6, minutes: [12, 16] }, words)).toBe("12 to 16 minutes");
  });

  it("says a free-flow time as what it is, never as a class-hour time", () => {
    expect(travelTime({ km: 3.4, freeFlowMinutes: 6 }, words)).toBe("about 6 minutes on empty roads");
  });

  it("says nothing when no time is known", () => {
    expect(travelTime({ km: 1 }, words)).toBeUndefined();
    expect(travelTime({ minutes: [5] }, words)).toBeUndefined();
  });
});
