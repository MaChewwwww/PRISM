import { ArrowRight, Newspaper } from "lucide-react";
import Link from "next/link";

import { PageHeader, ProvenanceLabel, StateBadge } from "@/components/workspace/workspace-ui";
import { RangePresets } from "@/components/workspace/range-presets";
import { SECTION_CARD, SectionHeading } from "@/components/workspace/section-heading";
import { formatDateTime } from "@/features/story/formatters";
import { readDateRange, type SearchValues } from "@/features/story/date-range";
import { listNews } from "@/features/story/presentation-api";

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
        description="A backend-owned illustrative feed connects source timestamps and symbols to the decision stories they influenced."
      >
        <RangePresets range={range} />
      </PageHeader>

      <section aria-labelledby="news-feed" className="mt-6">
        <SectionHeading
          id="news-feed"
          icon={Newspaper}
          title="Catalyst Feed"
          subtitle="Source-timestamped signals linked to the decisions they influenced."
        />

        {news.length === 0 ? (
          <div className={`${SECTION_CARD} p-6`}>
            <p className="text-[13px] text-[#94A3B8]">
              No illustrative news falls inside this range.
            </p>
          </div>
        ) : (
          <ul className="space-y-4">
            {news.map((item) => (
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
      </section>
    </>
  );
}
