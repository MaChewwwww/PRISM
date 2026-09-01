"use client";

import { ArrowRight, Search, X } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";
import { useMemo, useState } from "react";

import { ProvenanceLabel, StateBadge } from "@/components/workspace/workspace-ui";
import { SECTION_CARD } from "@/components/workspace/section-heading";
import { formatDateTime } from "@/features/story/formatters";
import type { NewsRecord } from "@/features/story/monitoring-api";

/** Lowercased haystack of the searchable fields for a news item. */
function searchHaystack(item: NewsRecord): string {
  return [
    item.headline,
    item.summary,
    item.source,
    item.category,
    item.significance,
    ...item.symbols,
    formatDateTime(item.publishedAt),
    item.publishedAt,
  ]
    .join(" ")
    .toLowerCase();
}

export function NewsList({
  news,
  heading,
  rangeControl,
}: {
  news: NewsRecord[];
  heading?: ReactNode;
  rangeControl?: ReactNode;
}) {
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const trimmed = query.trim().toLowerCase();
    if (!trimmed) return news;
    const terms = trimmed.split(/\s+/);
    return news.filter((item) => {
      const haystack = searchHaystack(item);
      return terms.every((term) => haystack.includes(term));
    });
  }, [query, news]);

  return (
    <>
      {/* Toolbar row: heading (left), search + range picker (right) */}
      <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        {heading && <div className="min-w-0 shrink-0">{heading}</div>}
        <div className="flex flex-1 flex-col gap-3 sm:flex-row sm:items-center lg:justify-end">
          <div className="relative w-full sm:max-w-xs">
            <Search
              className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#64748B]"
              aria-hidden="true"
            />
            <input
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search headline, company, date, time"
              aria-label="Search news"
              className="w-full rounded-md border border-white/8 bg-white/2 py-2 pl-9 pr-9 text-[13px] text-[#F8FAFC] outline-none transition-colors placeholder:text-[#64748B] focus-visible:border-[#547D83]/50 focus-visible:ring-2 focus-visible:ring-[#547D83]/40"
            />
            {query && (
              <button
                type="button"
                onClick={() => setQuery("")}
                aria-label="Clear search"
                className="absolute right-2 top-1/2 grid h-6 w-6 -translate-y-1/2 place-items-center rounded-md text-[#64748B] outline-none transition-colors hover:text-[#F8FAFC] focus-visible:ring-2 focus-visible:ring-[#547D83]"
              >
                <X className="h-3.5 w-3.5" aria-hidden="true" />
              </button>
            )}
          </div>
          {rangeControl && <div className="shrink-0">{rangeControl}</div>}
        </div>
      </div>

      {news.length === 0 ? (
        <div className={`${SECTION_CARD} p-6`}>
          <p className="text-[13px] text-[#94A3B8]">
            No recorded news analysis falls inside this range.
          </p>
        </div>
      ) : filtered.length === 0 ? (
        <div className={`${SECTION_CARD} p-6`}>
          <p className="text-[13px] text-[#94A3B8]">
            No news matches &ldquo;{query}&rdquo;. Try a different company, date, or time.
          </p>
        </div>
      ) : (
        <ul className="space-y-4">
          {filtered.map((item) => (
            <li key={item.id} className={`${SECTION_CARD} p-5 sm:p-6`}>
              {/* Kicker: time · source · symbols · significance */}
              <div className="flex flex-wrap items-center gap-x-2 gap-y-1 font-mono text-[12px] font-medium uppercase tracking-[0.08em] text-[#64748B]">
                <time dateTime={item.publishedAt}>{formatDateTime(item.publishedAt)}</time>
                <span aria-hidden="true" className="text-white/20">
                  |
                </span>
                <span className="text-[#CBD5E1]">{item.source}</span>
                {item.symbols.map((symbol) => (
                  <span key={symbol} className="font-semibold text-[#38BDF8]">
                    {symbol}
                  </span>
                ))}
                <StateBadge state={item.significance} />
                <span>{item.category}</span>
              </div>

              <h3 className="mt-3 text-[17px] font-semibold leading-snug tracking-tight text-[#F8FAFC]">
                {item.headline}
              </h3>
              <p className="mt-1.5 max-w-3xl text-[14px] leading-relaxed text-[#CBD5E1]">
                {item.summary}
              </p>

              <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-white/8 pt-4">
                <ProvenanceLabel provenance={item.provenance} />
                {item.storyId && (
                  <Link
                    href={`/stories/${item.storyId}`}
                    className="inline-flex items-center gap-1.5 text-[13px] font-medium text-[#B2D8DC] outline-none transition-colors hover:text-[#F8FAFC] focus-visible:ring-2 focus-visible:ring-[#547D83] focus-visible:ring-offset-2 focus-visible:ring-offset-[#080B10]"
                  >
                    Read linked decision story
                    <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
                  </Link>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
