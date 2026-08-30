import { DateRangeControl } from "@/components/workspace/date-range-control";
import { PageHeader } from "@/components/workspace/workspace-ui";
import { MarketTrackerShell } from "@/features/market/market-tracker-shell";
import { readDateRange, type SearchValues } from "@/features/story/date-range";

export default async function MarketTrackerPage({
  searchParams,
}: {
  searchParams: Promise<SearchValues>;
}) {
  const range = readDateRange(await searchParams);

  return (
    <>
      <PageHeader
        eyebrow="Market tracker"
        title="Read the market around every decision"
        description="A future server-owned market adapter will pair normalized price bars with verified paper activity and PRISM decision traces. This skeleton defines the interaction boundary without fabricating market data."
      />
      <DateRangeControl range={range} />
      <MarketTrackerShell range={range} />
    </>
  );
}
