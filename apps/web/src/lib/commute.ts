/** How long a trip takes, as the area pages say it. A range is a time measured at class hours; a single number is a time on empty roads. */
export interface Trip {
  km?: number;
  minutes?: number[];
  freeFlowMinutes?: number;
}

export function travelTime(trip: Trip, words: { range: string; freeFlow: string }): string | undefined {
  const fill = (template: string, values: Record<string, number>) => template.replace(/\{(\w+)\}/g, (whole, key: string) => String(values[key] ?? whole));
  if (trip.minutes && trip.minutes.length === 2) return fill(words.range, { from: trip.minutes[0] ?? 0, to: trip.minutes[1] ?? 0 });
  if (trip.freeFlowMinutes !== undefined) return fill(words.freeFlow, { min: trip.freeFlowMinutes });
  return undefined;
}
