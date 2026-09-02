import { Newspaper } from "lucide-react";

import { PageHeader } from "@/components/workspace/workspace-ui";
import { RangePresets } from "@/components/workspace/range-presets";
import { MarketTrackerShell } from "@/features/market/market-tracker-shell";
import { NewsList } from "@/features/story/news-list";
import { readDateRange, type SearchValues } from "@/features/story/date-range";
import { listNews } from "@/features/story/monitoring-api";

export default async function MarketTrackerPage({
  searchParams,
}: {
  searchParams: Promise<SearchValues>;
}) {
  const range = readDateRange(await searchParams);
  const collection = await listNews(range);
  const news = collection.items;
  const nowUtc = new Date().toISOString().replace("T", " ").slice(0, 19);

  return (
    <>
      <PageHeader
        eyebrow="Market surface"
        title="Market Tracker"
        description="Price, decisions, verified paper activity, and the catalyst feed that drives them."
      />

      <MarketTrackerShell nowUtc={nowUtc} />

      {/* Catalyst feed — merged from the former News page, below the graph. */}
      <section aria-labelledby="catalyst-feed" className="mt-8">
        <NewsList
          news={news}
          rangeControl={<RangePresets range={range} />}
          heading={
            <div>
              <h2
                id="catalyst-feed"
                className="flex items-center gap-2.5 text-lg font-semibold tracking-tight text-[#F8FAFC]"
              >
                <span className="grid h-7 w-7 shrink-0 place-items-center rounded-md border border-[#818CF8]/30 bg-[#818CF8]/15 text-[#C7D2FE]">
                  <Newspaper className="h-3.5 w-3.5" aria-hidden="true" />
                </span>
                Catalyst Feed
              </h2>
              <p className="mt-1 text-[12px] text-[#64748B]">
                Source-timestamped signals linked to the decisions they influenced.
              </p>
            </div>
          }
        />
      </section>
    </>
  );
}
