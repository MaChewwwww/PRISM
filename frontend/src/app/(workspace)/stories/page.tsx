import { Filter, RotateCcw } from "lucide-react";
import Link from "next/link";

import { DateRangeControl } from "@/components/product/date-range-control";
import { DemoDataNotice, PageHeader } from "@/components/product/workspace-ui";
import { rangeQuery, readDateRange, type SearchValues } from "@/features/story/date-range";
import { listStories } from "@/features/story/presentation-api";
import { StoryList } from "@/features/story/story-list";

function value(values: SearchValues, key: string) {
  const found = values[key];
  return Array.isArray(found) ? found[0] : found;
}

export default async function StoriesPage({
  searchParams,
}: {
  searchParams: Promise<SearchValues>;
}) {
  const values = await searchParams;
  const range = readDateRange(values);
  const outcome = value(values, "outcome") ?? "all";
  const symbol = value(values, "symbol") ?? "all";
  const collection = await listStories(range, { outcome, symbol });
  const stories = collection.stories;

  return (
    <>
      <PageHeader
        eyebrow="Decision log"
        title="Decision Stories"
        description="A scannable feed of the narrative takeaway and the counterfactual impact behind every call the agent stack made."
      />
      <DemoDataNotice />
      <DateRangeControl range={range} />
      <form className="filter-bar" method="get">
        <Filter aria-hidden="true" />
        <input type="hidden" name="range" value={range.preset} />
        <input type="hidden" name="from" value={range.from} />
        <input type="hidden" name="to" value={range.to} />
        <label>
          <span>Outcome</span>
          <select name="outcome" defaultValue={outcome}>
            <option value="all">All outcomes</option>
            <option value="pass">Pass</option>
            <option value="modify">Modify</option>
            <option value="fail">Fail</option>
            <option value="no_trade">No trade</option>
            <option value="degraded">Degraded</option>
          </select>
        </label>
        <label>
          <span>Symbol</span>
          <select name="symbol" defaultValue={symbol}>
            <option value="all">All symbols</option>
            {collection.symbols.map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </label>
        <button type="submit">Apply filters</button>
        <Link href={`/stories?${rangeQuery(range)}`}>
          <RotateCcw aria-hidden="true" /> Clear
        </Link>
      </form>
      <div className="result-count" role="status">
        {stories.length} illustrative {stories.length === 1 ? "story" : "stories"}
      </div>
      <StoryList stories={stories} />
    </>
  );
}
