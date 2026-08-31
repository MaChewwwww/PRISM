"use client";

import { ArrowUpRight, Check, Lightbulb, Search, Star, X } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

import type { ReactNode } from "react";

import { StateBadge } from "@/components/workspace/workspace-ui";
import {
  branchTakeaway,
  branchWhatIf,
  decisionLabel,
  formatDateTime,
  parseMoney,
} from "@/features/story/formatters";
import type { AlternativeSession } from "@/features/story/presentation-api";

const SECTION_CARD =
  "rounded-xl border border-white/8 border-t-white/16 bg-linear-to-b from-white/6 to-white/2 backdrop-blur-xl";

type Branch = AlternativeSession["branches"][number];

/** Tone a P&L string green (gain), red (loss), or muted (flat). */
function pnlTone(pnl: string): string {
  const value = parseMoney(pnl);
  if (!Number.isFinite(value) || value === 0) return "text-[#94A3B8]";
  return value > 0 ? "text-[#00D084]" : "text-[#FF6B6B]";
}

/** Pick the chosen branch and the best-performing alternative for a session. */
function chosenAndBest(branches: Branch[]): { chosen?: Branch; best?: Branch } {
  const chosen = branches.find((branch) => branch.branchKey === "chosen");
  const alternatives = branches.filter(
    (branch) => branch.branchKey !== "chosen" && Number.isFinite(parseMoney(branch.pnl)),
  );
  const best = alternatives.reduce<Branch | undefined>((leader, branch) => {
    if (!leader) return branch;
    return parseMoney(branch.pnl) > parseMoney(leader.pnl) ? branch : leader;
  }, undefined);
  return { chosen, best };
}

/** Build a lowercased haystack of the searchable fields for a session. */
function searchHaystack(session: AlternativeSession): string {
  return [
    session.symbol,
    session.title,
    session.summary,
    decisionLabel(session.symbol, session.chosenPathPnl).headline,
    formatDateTime(session.occurredAt),
    session.occurredAt,
  ]
    .join(" ")
    .toLowerCase();
}

export function AlternativesList({
  sessions,
  heading,
  rangeControl,
}: {
  sessions: AlternativeSession[];
  heading?: ReactNode;
  rangeControl?: ReactNode;
}) {
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const trimmed = query.trim().toLowerCase();
    if (!trimmed) return sessions;
    const terms = trimmed.split(/\s+/);
    return sessions.filter((session) => {
      const haystack = searchHaystack(session);
      return terms.every((term) => haystack.includes(term));
    });
  }, [query, sessions]);

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
              placeholder="Search decision, company, date, time"
              aria-label="Search shadow studies"
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

      {sessions.length === 0 ? (
        <div className={`${SECTION_CARD} p-6`}>
          <p className="text-[13px] text-[#94A3B8]">
            No completed ShadowFund alternative sessions fall inside this date range.
          </p>
        </div>
      ) : filtered.length === 0 ? (
        <div className={`${SECTION_CARD} p-6`}>
          <p className="text-[13px] text-[#94A3B8]">
            No shadow studies match &ldquo;{query}&rdquo;. Try a different company, date, or time.
          </p>
        </div>
      ) : (
        <ul className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {filtered.map((session) => {
            const { chosen, best } = chosenAndBest(session.branches);
            const isHistoricalSimulation = session.simulation?.kind === "historical_options";
            const takeaway = branchTakeaway(
              branchWhatIf(best?.branchKey ?? "", best?.label ?? session.bestBranch).plain,
              session.bestDelta,
            );
            return (
              <li key={session.id} className="flex">
                <Link
                  href={`/alternatives/${session.id}`}
                  className={`group flex w-full flex-col gap-4 ${SECTION_CARD} p-5 outline-none transition-all duration-200 hover:-translate-y-0.5 hover:border-[#818CF8]/40 hover:shadow-[0_0_24px_rgba(129,140,248,0.25)] focus-visible:ring-2 focus-visible:ring-[#547D83] focus-visible:ring-offset-2 focus-visible:ring-offset-[#080B10]`}
                >
                  {/* Kicker */}
                  <div className="flex flex-wrap items-center gap-x-2 gap-y-1 font-mono text-[11px] font-medium uppercase tracking-[0.07em] text-[#64748B]">
                    <span className="font-semibold text-[#C7D2FE]">
                      {isHistoricalSimulation ? "Historical simulation" : "Shadow study"}
                    </span>
                    <span aria-hidden="true" className="text-white/20">
                      |
                    </span>
                    <span className="font-semibold text-[#38BDF8]">{session.symbol}</span>
                    <span aria-hidden="true" className="text-white/20">
                      |
                    </span>
                    <time dateTime={session.occurredAt}>{formatDateTime(session.occurredAt)}</time>
                    <StateBadge state="simulated" />
                  </div>

                  {/* Decision headline + plain-language framing */}
                  <div>
                    <h3 className="text-[17px] font-semibold leading-snug tracking-tight text-[#F8FAFC] transition-colors group-hover:text-[#C7D2FE]">
                      {decisionLabel(session.symbol, session.chosenPathPnl).headline}
                    </h3>
                    <p className="mt-1 text-[13px] text-[#94A3B8]">
                      {decisionLabel(session.symbol, session.chosenPathPnl).question}
                    </p>
                  </div>

                  {/* Compact comparison: what we chose vs the best shadow path */}
                  <dl className="divide-y divide-white/8 overflow-hidden rounded-xl border border-white/8 bg-white/2">
                    {chosen && (
                      <div
                        className="flex items-center justify-between gap-4 px-4 py-2.5"
                        style={{ background: "rgba(84,125,131,0.12)" }}
                      >
                        <dt className="flex items-center gap-2 text-[13px]">
                          <Check
                            className="h-3.5 w-3.5 shrink-0 text-[#547D83]"
                            aria-hidden="true"
                          />
                          <span className="font-semibold text-[#F8FAFC]">
                            {isHistoricalSimulation ? "Chosen strategy" : "Active Portfolio"}
                          </span>
                        </dt>
                        <dd
                          className={`font-mono text-[14px] font-semibold tabular-nums ${pnlTone(chosen.pnl)}`}
                        >
                          {chosen.pnl}
                        </dd>
                      </div>
                    )}
                    {chosen?.simulatedFill?.status === "filled" && (
                      <div className="px-4 py-2 text-[11px] text-[#94A3B8]">
                        Simulated fill {chosen.simulatedFill.entryPrice ?? "—"} →{" "}
                        {chosen.simulatedFill.exitPrice ?? "open"}
                      </div>
                    )}
                    {best && (
                      <div className="flex items-center justify-between gap-4 px-4 py-2.5">
                        <dt className="flex items-center gap-2 text-[13px]">
                          <Star
                            className="h-3.5 w-3.5 shrink-0 text-[#F59E0B]"
                            aria-hidden="true"
                          />
                          <span className="text-[#CBD5E1]">
                            Best alternative: {branchWhatIf(best.branchKey, best.label).question}
                          </span>
                        </dt>
                        <dd
                          className={`font-mono text-[14px] font-semibold tabular-nums ${pnlTone(best.pnl)}`}
                        >
                          {best.pnl}
                        </dd>
                      </div>
                    )}
                  </dl>

                  {/* Human takeaway */}
                  {takeaway && (
                    <p className="flex items-start gap-2 text-[13px] leading-relaxed text-[#C7D2FE]">
                      <Lightbulb className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                      {takeaway}
                    </p>
                  )}

                  {/* Summary + open affordance */}
                  <div className="flex items-end justify-between gap-4 border-t border-white/8 pt-3">
                    <p className="min-w-0 text-[12px] leading-relaxed text-[#64748B]">
                      {session.summary}
                    </p>
                    <span className="inline-flex shrink-0 items-center gap-1.5 text-[13px] font-medium text-[#B2D8DC] transition-transform group-hover:translate-x-0.5">
                      Details
                      <ArrowUpRight className="h-4 w-4" aria-hidden="true" />
                    </span>
                  </div>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </>
  );
}
