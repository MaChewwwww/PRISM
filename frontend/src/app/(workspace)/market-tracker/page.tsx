import { PageHeader } from "@/components/workspace/workspace-ui";
import { MarketTrackerShell } from "@/features/market/market-tracker-shell";

export default function MarketTrackerPage() {
  const nowUtc = new Date().toISOString().replace("T", " ").slice(0, 19);

  return (
    <>
      <PageHeader
        eyebrow="Market surface"
        title="Market Tracker"
        description="Price, decisions, and verified paper activity."
      />
      <MarketTrackerShell nowUtc={nowUtc} />
    </>
  );
}
