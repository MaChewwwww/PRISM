"use client";

import { PaginatedList } from "@/components/workspace/paginated-list";
import { formatDateTime } from "@/features/story/formatters";
import type { Activity } from "@/features/story/monitoring-api";

function amountTone(amount: string) {
  if (amount.startsWith("+")) return "text-[#00D084]";
  if (amount.startsWith("-")) return "text-[#FF6B6B]";
  return "text-[#94A3B8]";
}

const SECTION_CARD =
  "rounded-xl border border-white/8 border-t-white/16 bg-linear-to-b from-white/6 to-white/2 backdrop-blur-xl";

export function PortfolioActivityList({ activities }: { activities: Activity[] }) {
  if (activities.length === 0) {
    return (
      <div className={SECTION_CARD}>
        <p className="inline-empty m-5 sm:m-6">No decision activity falls inside this range.</p>
      </div>
    );
  }

  return (
    <PaginatedList
      items={activities}
      itemLabel="events"
      getKey={(activity) => `${activity.occurredAt}-${activity.label}`}
      className={`${SECTION_CARD} overflow-hidden`}
      renderItem={(activity) => (
        <div className="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)] items-center gap-4 px-5 py-3.5 not-last:border-b not-last:border-white/8 sm:px-6">
          <time
            dateTime={activity.occurredAt}
            className="font-mono text-[13px] tabular-nums text-[#64748B]"
          >
            {formatDateTime(activity.occurredAt)}
          </time>
          <span className="text-[14px] text-[#CBD5E1]">{activity.label}</span>
          <span
            className={`text-right text-[14px] font-semibold tabular-nums ${amountTone(activity.amount)}`}
          >
            {activity.amount}
          </span>
        </div>
      )}
    />
  );
}
