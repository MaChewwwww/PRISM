"use client";

import { CalendarDays } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useState, type FormEvent } from "react";

import { rangeForPreset, type DateRange, type RangePreset } from "@/features/story/story-data";

const presets: Array<{ value: Exclude<RangePreset, "custom">; label: string }> = [
  { value: "7d", label: "7D" },
  { value: "1m", label: "1M" },
  { value: "3m", label: "3M" },
  { value: "ytd", label: "YTD" },
];

export function DateRangeControl({ range }: { range: DateRange }) {
  const pathname = usePathname();
  const router = useRouter();
  const currentSearch = useSearchParams();
  const [from, setFrom] = useState(range.from);
  const [to, setTo] = useState(range.to);
  const [error, setError] = useState<string | null>(null);

  function navigate(nextRange: DateRange) {
    const params = new URLSearchParams(currentSearch.toString());
    params.set("range", nextRange.preset);
    params.set("from", nextRange.from);
    params.set("to", nextRange.to);
    router.replace(`${pathname}?${params.toString()}`);
  }

  function selectPreset(preset: Exclude<RangePreset, "custom">) {
    const nextRange = rangeForPreset(preset);
    setFrom(nextRange.from);
    setTo(nextRange.to);
    setError(null);
    navigate(nextRange);
  }

  function submitCustom(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!from || !to) {
      setError("Choose both a start and end date.");
      return;
    }
    if (from > to) {
      setError("Start date must be on or before the end date.");
      return;
    }
    setError(null);
    navigate({ preset: "custom", from, to });
  }

  return (
    <div className="range-control" aria-label="Story date range">
      <div className="range-presets" role="group" aria-label="Date range presets">
        {presets.map((preset) => (
          <button
            key={preset.value}
            type="button"
            aria-pressed={range.preset === preset.value}
            onClick={() => selectPreset(preset.value)}
          >
            {preset.label}
          </button>
        ))}
      </div>
      <form className="custom-range" onSubmit={submitCustom} noValidate>
        <CalendarDays aria-hidden="true" />
        <label>
          <span>From</span>
          <input
            type="date"
            value={from}
            max={to}
            onChange={(event) => setFrom(event.target.value)}
          />
        </label>
        <span aria-hidden="true">—</span>
        <label>
          <span>To</span>
          <input
            type="date"
            value={to}
            min={from}
            onChange={(event) => setTo(event.target.value)}
          />
        </label>
        <button type="submit" className="range-apply">
          Apply
        </button>
      </form>
      {error && (
        <p className="range-error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
