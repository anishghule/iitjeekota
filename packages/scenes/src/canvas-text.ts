/** Text drawn into scene textures, in the brand fonts from the tokens. */
import { tokens } from "@dsap/tokens";

export type FontRole = "display" | "body";

const DEVANAGARI = /[ऀ-ॿ]/;

/** A canvas font string. Devanagari text uses the Devanagari stack whatever the role. */
export function canvasFont(role: FontRole, weight: number, sizePx: number, text = ""): string {
  const stack = DEVANAGARI.test(text) ? tokens.font.family.devanagari : tokens.font.family[role];
  const families = stack.map((f) => (f.includes(" ") ? `"${f}"` : f)).join(", ");
  return `${weight} ${sizePx}px ${families}`;
}

/** Splits text into lines that fit a width, word by word. */
export function wrapLines(g: CanvasRenderingContext2D, text: string, maxWidth: number): string[] {
  const lines: string[] = [];
  let line = "";
  for (const word of text.split(/\s+/)) {
    const next = line ? `${line} ${word}` : word;
    if (line && g.measureText(next).width > maxWidth) {
      lines.push(line);
      line = word;
    } else {
      line = next;
    }
  }
  if (line) lines.push(line);
  return lines;
}
