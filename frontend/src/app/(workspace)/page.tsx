import { OverviewDashboard } from "@/features/overview/overview-dashboard";
import { readDateRange, type SearchValues } from "@/features/story/date-range";
import { loadDashboard } from "@/features/story/presentation-api";

export default async function OverviewPage({
  searchParams,
}: {
  searchParams: Promise<SearchValues>;
}) {
  const range = readDateRange(await searchParams);
  const overview = await loadDashboard(range);
  return <OverviewDashboard overview={overview} range={range} />;
}
