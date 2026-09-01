"use client";

import { RefreshCw } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

const REFRESH_INTERVAL_MS = 3 * 60 * 1000;

/** Refreshes server-rendered monitoring data only while the tab is visible. */
export function MonitoringRefresh() {
  const router = useRouter();
  const [refreshing, setRefreshing] = useState(false);

  const refresh = useCallback(() => {
    setRefreshing(true);
    router.refresh();
    window.setTimeout(() => setRefreshing(false), 500);
  }, [router]);

  useEffect(() => {
    const interval = window.setInterval(() => {
      if (document.visibilityState === "visible") refresh();
    }, REFRESH_INTERVAL_MS);
    return () => window.clearInterval(interval);
  }, [refresh]);

  return (
    <button
      type="button"
      className="fixed bottom-4 right-4 z-20 inline-flex min-h-10 items-center gap-2 rounded-full border border-white/10 bg-[#0F151D]/95 px-3 text-xs text-[#CBD5E1] shadow-lg backdrop-blur-xl outline-none transition hover:border-[#547D83]/60 focus-visible:ring-2 focus-visible:ring-[#547D83]"
      onClick={refresh}
      disabled={refreshing}
      aria-label="Refresh recorded monitoring data"
    >
      <RefreshCw className={refreshing ? "h-3.5 w-3.5 animate-spin" : "h-3.5 w-3.5"} />
      {refreshing ? "Refreshing" : "Refresh data"}
    </button>
  );
}
