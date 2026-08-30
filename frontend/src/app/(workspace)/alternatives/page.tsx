import { ArrowUpRight, GitCompareArrows, Layers } from "lucide-react";
import Link from "next/link";

import { PageHeader, StateBadge } from "@/components/workspace/workspace-ui";
import { RangePresets } from "@/components/workspace/range-presets";
import { formatDate } from "@/features/story/formatters";
import { readDateRange, type SearchValues } from "@/features/story/date-range";
import { listAlternativeSessions } from "@/features/story/presentation-api";

const SECTION_CARD =
  "rounded-xl border border-white/8 border-t-white/16 bg-linear-to-b from-white/6 to-white/2 backdrop-blur-xl";

const LAYERS = [
  {
    tag: "Layer 01",
    title: "Decision Counterfactuals",
    detail:
      "Active Portfolio path, Cash baseline, Reduced sizing (50%), and Unhedged alternatives.",
  },
  {
    tag: "Layer 02",
    title: "Agent Strategy Variations",
    detail: "Divergent strikes, expirations, and contrarian perspectives generated simultaneously.",
  },
  {
    tag: "Layer 03",
    title: "AI Profile Adaptation",
    detail:
      "Counterfactual regret and alpha generate explainable recommendations for the next profile.",
  },
];

function displayBranchLabel(label: string) {
  return label === "Illustrative governed path" ? "Active Portfolio" : label;
}

/** Section heading rendered above the card: icon + title + subtitle, left aligned. */
function SectionHeading({
  id,
  icon: Icon,
  title,
  subtitle,
}: {
  id: string;
  icon: typeof Layers;
  title: string;
  subtitle: string;
}) {
  return (
    <div className="mb-4">
      <h2
        id={id}
        className="flex items-center gap-2.5 text-lg font-semibold tracking-tight text-[#F8FAFC]"
      >
        <span className="grid h-7 w-7 shrink-0 place-items-center rounded-md border border-[#818CF8]/30 bg-[#818CF8]/15 text-[#C7D2FE]">
          <Icon className="h-3.5 w-3.5" aria-hidden="true" />
        </span>
        {title}
      </h2>
      <p className="mt-1 text-[12px] text-[#64748B]">{subtitle}</p>
    </div>
  );
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
        title="Shadow Portfolios"
        description="Every major decision launches parallel non-executing Shadow Portfolios to stress-test alternate choices under identical market conditions."
      >
        <RangePresets range={range} />
      </PageHeader>

      {/* Analysis layers */}
      <section aria-labelledby="layers" className="mt-6">
        <SectionHeading
          id="layers"
          icon={Layers}
          title="How ShadowFund Analyzes"
          subtitle="Three layers of counterfactual analysis run on every decision."
        />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {LAYERS.map((layer) => (
            <div key={layer.tag} className={`${SECTION_CARD} p-5`}>
              <span className="font-mono text-[11px] uppercase tracking-[0.09em] text-[#818CF8]">
                {layer.tag}
              </span>
              <h3 className="mt-2 text-[15px] font-semibold text-[#F8FAFC]">{layer.title}</h3>
              <p className="mt-1.5 text-[13px] leading-relaxed text-[#94A3B8]">{layer.detail}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ShadowFund sessions */}
      <section aria-labelledby="sessions" className="mt-6">
        <SectionHeading
          id="sessions"
          icon={GitCompareArrows}
          title="ShadowFund Sessions"
          subtitle="Simulated multiverse comparisons for each recorded decision."
        />

        {sessions.length === 0 ? (
          <div className={`${SECTION_CARD} p-6`}>
            <p className="text-[13px] text-[#94A3B8]">
              No completed ShadowFund alternative sessions fall inside this date range.
            </p>
          </div>
        ) : (
          <ul className="space-y-4">
            {sessions.map((session) => (
              <li key={session.id}>
                <Link
                  href={`/alternatives/${session.id}`}
                  className={`group flex flex-col gap-4 ${SECTION_CARD} p-5 outline-none transition-all duration-200 hover:-translate-y-0.5 hover:border-[#818CF8]/40 hover:shadow-[0_0_24px_rgba(129,140,248,0.25)] focus-visible:ring-2 focus-visible:ring-[#547D83] focus-visible:ring-offset-2 focus-visible:ring-offset-[#080B10] sm:p-6`}
                >
                  {/* Kicker */}
                  <div className="flex flex-wrap items-center gap-x-2 gap-y-1 font-mono text-[12px] font-medium uppercase tracking-[0.08em] text-[#64748B]">
                    <time dateTime={session.occurredAt}>{formatDate(session.occurredAt)}</time>
                    <span aria-hidden="true" className="text-white/20">
                      |
                    </span>
                    <span className="font-semibold text-[#38BDF8]">{session.symbol}</span>
                    <span aria-hidden="true" className="text-white/20">
                      |
                    </span>
                    <StateBadge state="simulated" />
                  </div>

                  {/* Title + summary */}
                  <div>
                    <h3 className="text-[17px] font-semibold leading-snug tracking-tight text-[#F8FAFC] transition-colors group-hover:text-[#C7D2FE]">
                      {session.title}
                    </h3>
                    <p className="mt-1.5 text-[13px] leading-relaxed text-[#94A3B8]">
                      {session.summary}
                    </p>
                  </div>

                  {/* Metrics + open affordance */}
                  <div className="flex items-end justify-between gap-4 border-t border-white/8 pt-4">
                    <dl className="grid grid-cols-2 gap-x-8 gap-y-3 sm:grid-cols-4">
                      <div>
                        <dt className="font-mono text-[10px] uppercase tracking-[0.08em] text-[#64748B]">
                          Chosen Path
                        </dt>
                        <dd className="mt-1 font-mono text-[14px] font-semibold tabular-nums text-[#00D084]">
                          {session.chosenPathPnl}
                        </dd>
                      </div>
                      <div>
                        <dt className="font-mono text-[10px] uppercase tracking-[0.08em] text-[#64748B]">
                          Best Shadow Path
                        </dt>
                        <dd className="mt-1 text-[14px] font-semibold text-[#818CF8]">
                          {displayBranchLabel(session.bestBranch)}
                        </dd>
                      </div>
                      <div>
                        <dt className="font-mono text-[10px] uppercase tracking-[0.08em] text-[#64748B]">
                          Shadow Delta
                        </dt>
                        <dd className="mt-1 font-mono text-[14px] font-semibold tabular-nums text-[#CBD5E1]">
                          {session.bestDelta}
                        </dd>
                      </div>
                      <div>
                        <dt className="font-mono text-[10px] uppercase tracking-[0.08em] text-[#64748B]">
                          Coverage
                        </dt>
                        <dd className="mt-1 font-mono text-[14px] font-semibold tabular-nums text-[#CBD5E1]">
                          {session.coverage}
                        </dd>
                      </div>
                    </dl>
                    <span
                      aria-hidden="true"
                      className="grid h-9 w-9 shrink-0 place-items-center rounded-md border border-white/8 text-[#64748B] transition-colors group-hover:border-[#818CF8]/40 group-hover:text-[#C7D2FE]"
                    >
                      <ArrowUpRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                    </span>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}
