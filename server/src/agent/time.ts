/** Utilidades de fuso horário sem dependências externas. */
export function tzOffsetMinutes(date: Date, tz: string): number {
  const parts = new Intl.DateTimeFormat("en-US", { timeZone: tz, hourCycle: "h23", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit" }).formatToParts(date);
  const g = (t: string) => Number(parts.find((p) => p.type === t)!.value);
  const asUtc = Date.UTC(g("year"), g("month") - 1, g("day"), g("hour"), g("minute"), g("second"));
  return Math.round((asUtc - date.getTime()) / 60000);
}
/** Converte "YYYY-MM-DD" + "HH:MM" no fuso `tz` para Date UTC. */
export function zonedToUtc(day: string, time: string, tz: string): Date {
  const [y, m, d] = day.split("-").map(Number);
  const [hh, mm] = time.split(":").map(Number);
  const guess = Date.UTC(y, m - 1, d, hh, mm);
  let off = tzOffsetMinutes(new Date(guess), tz);
  let res = guess - off * 60000;
  const off2 = tzOffsetMinutes(new Date(res), tz);
  if (off2 !== off) res = guess - off2 * 60000;
  return new Date(res);
}
export function formatInTz(date: Date, tz: string, locale = "pt-BR") {
  return new Intl.DateTimeFormat(locale, { timeZone: tz, dateStyle: "full", timeStyle: "short" }).format(date);
}
export function weekdayKey(day: string, tz: string): string {
  const d = zonedToUtc(day, "12:00", tz);
  return new Intl.DateTimeFormat("en-US", { timeZone: tz, weekday: "short" }).format(d).toLowerCase().slice(0, 3);
}
export const DAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"] as const;
export type OpeningHours = Partial<Record<(typeof DAY_KEYS)[number], [string, string][]>>;
