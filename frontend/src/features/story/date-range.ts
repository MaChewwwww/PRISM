import type { components } from "@/types/api.generated";

export type DateRange = components["schemas"]["DateRange"];
export type RangePreset = DateRange["preset"];
export type SearchValues = Record<string, string | string[] | undefined>;

const presets: Array<Exclude<RangePreset, "custom">> = ["7d", "1m", "3m", "ytd"];

function isoDate(date: Date) {
  return date.toISOString().slice(0, 10);
}

function dateOffset(date: string, days: number) {
  const parsed = new Date(`${date}T00:00:00.000Z`);
  parsed.setUTCDate(parsed.getUTCDate() + days);
  return isoDate(parsed);
}

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

function isIsoDate(value: string | undefined): value is string {
  if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  return !Number.isNaN(new Date(`${value}T00:00:00.000Z`).valueOf());
}

export function rangeForPreset(
  preset: Exclude<RangePreset, "custom">,
  anchor = isoDate(new Date()),
): DateRange {
  if (preset === "ytd") {
    return { preset, from: `${anchor.slice(0, 4)}-01-01`, to: anchor, timezone: "UTC" };
  }
  const days = preset === "7d" ? 7 : preset === "1m" ? 30 : 90;
  return { preset, from: dateOffset(anchor, -days), to: anchor, timezone: "UTC" };
}

export function readDateRange(values: SearchValues, anchor = isoDate(new Date())): DateRange {
  const requested = first(values.range);
  if (requested && presets.includes(requested as Exclude<RangePreset, "custom">)) {
    const expected = rangeForPreset(requested as Exclude<RangePreset, "custom">, anchor);
    const from = first(values.from);
    const to = first(values.to);
    return isIsoDate(from) && isIsoDate(to) && from <= to
      ? { preset: requested as Exclude<RangePreset, "custom">, from, to, timezone: "UTC" }
      : expected;
  }

  const from = first(values.from);
  const to = first(values.to);
  if (requested === "custom" && isIsoDate(from) && isIsoDate(to) && from <= to) {
    return { preset: "custom", from, to, timezone: "UTC" };
  }
  return rangeForPreset("1m", anchor);
}

export function rangeQuery(range: DateRange) {
  return new URLSearchParams({ range: range.preset, from: range.from, to: range.to }).toString();
}

export function apiRangeQuery(range: DateRange) {
  return {
    from: `${range.from}T00:00:00Z`,
    to: `${range.to}T23:59:59Z`,
  };
}
