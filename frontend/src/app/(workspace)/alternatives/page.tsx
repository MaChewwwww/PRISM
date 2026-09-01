import { GitCompareArrows } from "lucide-react";

import { PageHeader } from "@/components/workspace/workspace-ui";
import { RangePresets } from "@/components/workspace/range-presets";
import { AlternativesList } from "@/features/story/alternatives-list";
import { readDateRange, type SearchValues } from "@/features/story/date-range";
import { listAlternativeSessions } from "@/features/story/monitoring-api";

export default async function AlternativesPage({
  searchParams,
}: {
  searchParams: Promise<SearchValues>;
}) {
  const range = readDateRange(await searchParams);
  const alternatives = await listAlternativeSessions(range);
  const isProduction = alternatives.dataMode === "recorded";

  return (
    <>
      <PageHeader
        eyebrow="ShadowFund Multiverse"
        title="Shadow Portfolios"
        description={
          isProduction
            ? "Recorded non-trade counterfactuals for autonomous decisions. These branches never submit or change an order."
            : "For every decision, PRISM asks &ldquo;what if it had chosen differently?&rdquo; and replays the alternatives, not trading, trading smaller, going unhedged, on the same market conditions. None of these are real orders."
        }
      />

      {/* ShadowFund sessions */}
      <section aria-labelledby="sessions" className="mt-6">
        <AlternativesList
          sessions={alternatives.sessions}
          dataMode={alternatives.dataMode}
          rangeControl={<RangePresets range={range} />}
          heading={
            <div>
              <h2
                id="sessions"
                className="flex items-center gap-2.5 text-lg font-semibold tracking-tight text-[#F8FAFC]"
              >
                <span className="grid h-7 w-7 shrink-0 place-items-center rounded-md border border-[#818CF8]/30 bg-[#818CF8]/15 text-[#C7D2FE]">
                  <GitCompareArrows className="h-3.5 w-3.5" aria-hidden="true" />
                </span>
                ShadowFund Sessions
              </h2>
              <p className="mt-1 text-[12px] text-[#64748B]">
                {isProduction
                  ? "Recorded non-trade counterfactuals from autonomous decisions."
                  : "Simulated multiverse comparisons for each recorded decision."}
              </p>
            </div>
          }
        />
      </section>
    </>
  );
}
