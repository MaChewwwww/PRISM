"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { rangeForPreset, type DateRange, type RangePreset } from "@/features/story/date-range";

const PRESETS: Array<{ value: Exclude<RangePreset, "custom">; label: string }> = [
  { value: "7d", label: "7D" },
  { value: "1m", label: "1M" },
  { value: "3m", label: "3M" },
  { value: "ytd", label: "YTD" },
];

/**
 * Compact preset-only range switcher (7D / 1M / 3M / YTD) intended to sit inline
 * with a section subheading. Unlike DateRangeControl it exposes no custom date
 * inputs or Apply button — it simply updates the range query on click.
 */
export function RangePresets({ range }: { range: DateRange }) {
  const pathname = usePathname();
  const router = useRouter();
  const currentSearch = useSearchParams();

  function selectPreset(preset: Exclude<RangePreset, "custom">) {
    const next = rangeForPreset(preset, range.to);
    const params = new URLSearchParams(currentSearch.toString());
    params.set("range", next.preset);
    params.set("from", next.from);
    params.set("to", next.to);
    router.replace(`${pathname}?${params.toString()}`);
  }

  return (
    <div
      className="inline-flex items-center gap-1 rounded-full border border-white/8 bg-white/5 p-1"
      role="group"
      aria-label="Date range presets"
    >
      {PRESETS.map((preset) => {
        const isActive = range.preset === preset.value;
        return (
          <button
            key={preset.value}
            type="button"
            aria-pressed={isActive}
            onClick={() => selectPreset(preset.value)}
            className="rounded-full px-3 py-1 font-mono text-[11px] font-semibold uppercase tracking-wide outline-none transition-colors focus-visible:ring-2 focus-visible:ring-[#547D83] focus-visible:ring-offset-2 focus-visible:ring-offset-[#080B10]"
            style={{
              color: isActive ? "#B2D8DC" : "#64748B",
              background: isActive ? "rgba(84,125,131,0.2)" : "transparent",
            }}
          >
            {preset.label}
          </button>
        );
      })}
    </div>
  );
}
