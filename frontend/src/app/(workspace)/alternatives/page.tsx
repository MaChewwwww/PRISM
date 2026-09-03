import { GitCompareArrows } from "lucide-react";

import { PageHeader } from "@/components/workspace/workspace-ui";
import { RangePresets } from "@/components/workspace/range-presets";
import { AlternativesList } from "@/features/story/alternatives-list";
import { ShadowMultiverseChart } from "@/features/story/shadow-multiverse-chart";
import { readDateRange, type SearchValues } from "@/features/story/date-range";
import { listAlternativeSessions } from "@/features/story/monitoring-api";

export default async function AlternativesPage({
  searchParams,
}: {
  searchParams: Promise<SearchValues>;
}) {
  const range = readDateRange(await searchParams);
  const alternatives = await listAlternativeSessions(range);

  return (
    <>
      <PageHeader
        eyebrow="ShadowFund Multiverse"
        title="Shadow Portfolios"
        description={"Alternative decisions simulated without placing trades."}
      />

      {/* Multiverse Trajectory Chart */}
      <div className="mt-6">
        <ShadowMultiverseChart
          aggregatePath={alternatives.aggregatePath}
          sessions={alternatives.sessions}
        />
      </div>

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
                {"Recorded alternative decisions from each simulation."}
              </p>
            </div>
          }
        />
      </section>
    </>
  );
}
