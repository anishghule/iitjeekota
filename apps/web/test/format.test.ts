import { describe, expect, it } from "vitest";
import { clockLabel, formatDay, hoursLines, weekdayName } from "../src/lib/format.ts";

describe("dates and times as people read them", () => {
  it("writes a day in the page's language with Latin digits", () => {
    expect(formatDay("2026-11-02", "en")).toBe("2 November 2026");
    expect(formatDay("2026-11-02", "hi")).toMatch(/^2 .+ 2026$/);
    expect(formatDay("2026-11-02", "mr")).toMatch(/^2 .+ 2026$/);
    expect(formatDay("2026-11-02T09:00", "en")).toBe("2 November 2026");
  });

  it("writes a time of day", () => {
    expect(clockLabel("07:00", "en").toLowerCase()).toBe("7:00 am");
    expect(clockLabel("20:00", "en").toLowerCase()).toBe("8:00 pm");
    expect(clockLabel("18:30", "en").toLowerCase()).toBe("6:30 pm");
  });

  it("names the days", () => {
    expect(weekdayName("Monday", "en")).toBe("Monday");
    expect(weekdayName("Saturday", "en")).toBe("Saturday");
    expect(weekdayName("Monday", "hi")).not.toBe("Monday");
  });

  it("joins days that run in a row and keeps the times beside them", () => {
    const lines = hoursLines([
      { dayOfWeek: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], opens: "07:00", closes: "20:00" },
      { dayOfWeek: ["Saturday"], opens: "07:00", closes: "18:00" },
    ], "en", "to");
    expect(lines.map((l) => l.days)).toEqual(["Monday to Friday", "Saturday"]);
    expect(lines[0]?.times.toLowerCase()).toBe("7:00 am to 8:00 pm");
    expect(lines[1]?.times.toLowerCase()).toBe("7:00 am to 6:00 pm");
  });
});
