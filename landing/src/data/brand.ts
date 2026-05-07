export const BRAND = "Klarmacher";
export const ACCENT = "#5e8a5f";

export type Lang = "de" | "en";

export function fillName(s: string, name: string = BRAND): string {
  return s.replace(/__NAME__/g, name);
}
