import { ArrowUpRight, GitCompareArrows } from "lucide-react";
import Link from "next/link";

import { DateRangeControl } from "@/components/product/date-range-control";
import { DemoDataNotice, PageHeader, StateBadge } from "@/components/product/workspace-ui";
import { formatDate } from "@/features/story/formatters";
import { readDateRange, type SearchValues } from "@/features/story/date-range";
import { listAlternativeSessions } from "@/features/story/presentation-api";

function displayBranchLabel(label: string) {
  return label === "Illustrative governed path" ? "Active Portfolio" : label;
}

export default async function AlternativesPage({
  searchParams,
}: {
  searchParams: Promise<SearchValues>;
}) {
  const range = readDateRange(await searchParams);
  const sessions = await listAlternativeSessions(range);
  return (
    <>
      <PageHeader
        eyebrow="ShadowFund Multiverse"
        title="Compare the Paths Not Taken"
        description="Every major decision launches parallel non-executing Shadow Portfolios to stress-test alternate choices under identical market conditions."
      />
      <DemoDataNotice />
      <DateRangeControl range={range} />
      <div className="layer-map" aria-label="ShadowFund analysis layers">
        <div className="prism-glass-card p-4">
          <span className="text-[#818CF8] font-mono text-xs">Layer 01</span>
          <h2 className="text-white font-semibold mt-1">Decision Counterfactuals</h2>
          <p className="text-slate-300 text-xs mt-1">
            Active Portfolio path, Cash baseline, Reduced sizing (50%), and Unhedged alternatives.
          </p>
        </div>
        <div className="prism-glass-card p-4">
          <span className="text-[#818CF8] font-mono text-xs">Layer 02</span>
          <h2 className="text-white font-semibold mt-1">Agent Strategy Variations</h2>
          <p className="text-slate-300 text-xs mt-1">
            Divergent strikes, expirations, and contrarian perspectives generated simultaneously.
          </p>
        </div>
        <div className="prism-glass-card p-4">
          <span className="text-[#818CF8] font-mono text-xs">Layer 03</span>
          <h2 className="text-white font-semibold mt-1">AI Profile Adaptation</h2>
          <p className="text-slate-300 text-xs mt-1">
            Counterfactual regret and alpha generate explainable recommendations for the next
            profile.
          </p>
        </div>
      </div>
      {sessions.length > 0 ? (
        <ol className="alternative-list space-y-3 mt-6">
          {sessions.map((session) => (
            <li
              key={session.id}
              className="prism-glass-interactive p-4 rounded-xl transition-all hover:-translate-y-0.5"
            >
              <div className="alternative-mark text-[#818CF8]">
                <GitCompareArrows aria-hidden="true" />
              </div>
              <div>
                <div className="story-kicker">
                  <time>{formatDate(session.occurredAt)}</time>
                  <span className="font-semibold text-[#38BDF8]">{session.symbol}</span>
                  <StateBadge state="simulated" />
                </div>
                <h2>
                  <Link
                    href={`/alternatives/${session.id}`}
                    className="hover:text-[#818CF8] transition-colors"
                  >
                    {session.title}
                  </Link>
                </h2>
                <p className="text-slate-300 text-sm mt-1">{session.summary}</p>
              </div>
              <dl>
                <div>
                  <dt>Chosen Path</dt>
                  <dd className="font-mono tabular-nums font-semibold text-[#00D084]">
                    {session.chosenPathPnl}
                  </dd>
                </div>
                <div>
                  <dt>Best Shadow Path</dt>
                  <dd className="font-mono tabular-nums text-[#818CF8]">
                    {displayBranchLabel(session.bestBranch)}
                  </dd>
                </div>
                <div>
                  <dt>Shadow Delta</dt>
                  <dd className="font-mono tabular-nums">{session.bestDelta}</dd>
                </div>
                <div>
                  <dt>Coverage</dt>
                  <dd className="font-mono tabular-nums">{session.coverage}</dd>
                </div>
              </dl>
              <Link
                className="icon-link group"
                href={`/alternatives/${session.id}`}
                aria-label={`Open ${session.title}`}
              >
                <ArrowUpRight
                  aria-hidden="true"
                  className="transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
                />
              </Link>
            </li>
          ))}
        </ol>
      ) : (
        <p className="inline-empty">
          No completed ShadowFund alternative sessions fall inside this date range.
        </p>
      )}
    </>
  );
}
