import { ArrowRight, Filter, Newspaper } from "lucide-react";
import Link from "next/link";

import { DateRangeControl } from "@/components/product/date-range-control";
import {
  DemoDataNotice,
  PageHeader,
  ProvenanceLabel,
  StateBadge,
} from "@/components/product/workspace-ui";
import { formatDateTime } from "@/features/story/formatters";
import { readDateRange, type SearchValues } from "@/features/story/date-range";
import { listNews } from "@/features/story/presentation-api";

function value(values: SearchValues, key: string) {
  const found = values[key];
  return Array.isArray(found) ? found[0] : found;
}

export default async function NewsPage({ searchParams }: { searchParams: Promise<SearchValues> }) {
  const values = await searchParams;
  const range = readDateRange(values);
  const symbol = value(values, "symbol") ?? "all";
  const significance = value(values, "significance") ?? "all";
  const collection = await listNews(range, { symbol, significance });
  const news = collection.items;
  return (
    <>
      <PageHeader
        eyebrow="News and catalysts"
        title="See the evidence before the interpretation"
        description="A backend-owned illustrative feed connects source timestamps and symbols to the decision stories they influenced."
      />
      <DemoDataNotice />
      <DateRangeControl range={range} />
      <div className="source-contract">
        <Newspaper aria-hidden="true" />
        <div>
          <strong>Illustrative source boundary</strong>
          <p>
            Fields mirror the intended read-only adapter, but this response came only from the
            versioned PRISM fixture.
          </p>
        </div>
        <ProvenanceLabel provenance="illustrative_fixture" />
      </div>
      <form className="filter-bar" method="get">
        <Filter aria-hidden="true" />
        <input type="hidden" name="range" value={range.preset} />
        <input type="hidden" name="from" value={range.from} />
        <input type="hidden" name="to" value={range.to} />
        <label>
          <span>Symbol</span>
          <select name="symbol" defaultValue={symbol}>
            <option value="all">All symbols</option>
            {collection.symbols.map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </label>
        <label>
          <span>Significance</span>
          <select name="significance" defaultValue={significance}>
            <option value="all">All significance</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </label>
        <button type="submit">Apply filters</button>
      </form>
      {news.length > 0 ? (
        <ol className="news-feed">
          {news.map((item) => (
            <li key={item.id}>
              <div className="news-time">
                <time dateTime={item.publishedAt}>{formatDateTime(item.publishedAt)}</time>
                <span>{item.source}</span>
              </div>
              <article>
                <div className="story-kicker">
                  {item.symbols.map((itemSymbol) => (
                    <span key={itemSymbol}>{itemSymbol}</span>
                  ))}
                  <StateBadge state={item.significance} />
                  <span>{item.category}</span>
                </div>
                <h2>{item.headline}</h2>
                <p>{item.summary}</p>
                <div className="news-footer">
                  <ProvenanceLabel provenance={item.provenance} />
                  {item.storyId && (
                    <Link href={`/stories/${item.storyId}`}>
                      Read linked decision story <ArrowRight aria-hidden="true" />
                    </Link>
                  )}
                </div>
              </article>
            </li>
          ))}
        </ol>
      ) : (
        <p className="inline-empty">No illustrative news falls inside these filters.</p>
      )}
    </>
  );
}
