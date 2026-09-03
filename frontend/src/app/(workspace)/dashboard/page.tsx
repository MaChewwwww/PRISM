import { OverviewDashboard } from "@/features/overview/overview-dashboard";
import { readDateRange, type SearchValues } from "@/features/story/date-range";
import { getWeeklySummary, loadDashboard } from "@/features/story/monitoring-api";

export default async function OverviewPage({
  searchParams,
}: {
  searchParams: Promise<SearchValues>;
}) {
  const range = readDateRange(await searchParams);
  const [overview, weeklySummary] = await Promise.all([
    loadDashboard(range),
    getWeeklySummary().catch(() => undefined),
  ]);
  return <OverviewDashboard overview={overview} range={range} weeklySummary={weeklySummary} />;
}
