import { Newspaper } from "lucide-react";

import { PageHeader } from "@/components/workspace/workspace-ui";
import { RangePresets } from "@/components/workspace/range-presets";
import { NewsList } from "@/features/story/news-list";
import { readDateRange, type SearchValues } from "@/features/story/date-range";
import { listNews } from "@/features/story/monitoring-api";

export default async function NewsPage({ searchParams }: { searchParams: Promise<SearchValues> }) {
  const values = await searchParams;
  const range = readDateRange(values);
  const collection = await listNews(range);
  const news = collection.items;

  return (
    <>
      <PageHeader
        eyebrow="News and catalysts"
        title="See the evidence before the interpretation"
        description="Recorded backend news analysis connects source timestamps and symbols to decisions when evidence exists."
      />

      <section aria-labelledby="news-feed" className="mt-6">
        <NewsList
          news={news}
          rangeControl={<RangePresets range={range} />}
          heading={
            <div>
              <h2
                id="news-feed"
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
