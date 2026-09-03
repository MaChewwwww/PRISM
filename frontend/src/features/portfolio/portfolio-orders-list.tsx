"use client";

import { ArrowDownLeft, ArrowUpRight, ClipboardList } from "lucide-react";

import type { OrderReceipt } from "@/features/story/monitoring-api";

function formatOrderTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "UTC",
    timeZoneName: "short",
  });
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; cls: string }> = {
    filled: { label: "Filled", cls: "bg-[#00D084]/15 text-[#00D084] border-[#00D084]/30" },
    partial: { label: "Partial", cls: "bg-[#FBBF24]/15 text-[#FBBF24] border-[#FBBF24]/30" },
    rejected: { label: "Rejected", cls: "bg-[#F87171]/15 text-[#F87171] border-[#F87171]/30" },
    error: { label: "Error", cls: "bg-[#F87171]/15 text-[#F87171] border-[#F87171]/30" },
    pending: { label: "Pending", cls: "bg-white/10 text-[#94A3B8] border-white/15" },
  };
  const style = map[status] ?? map.pending;
  return (
    <span
      className={`inline-flex items-center rounded-md border px-1.5 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wider ${style.cls}`}
    >
      {style.label}
    </span>
  );
}

function SideBadge({ side }: { side: string }) {
  const isExit = side === "exit";
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wider ${
        isExit
          ? "border-[#F87171]/30 bg-[#F87171]/10 text-[#F87171]"
          : "border-[#00D084]/30 bg-[#00D084]/10 text-[#00D084]"
      }`}
    >
      {isExit ? (
        <ArrowDownLeft className="h-2.5 w-2.5" aria-hidden="true" />
      ) : (
        <ArrowUpRight className="h-2.5 w-2.5" aria-hidden="true" />
      )}
      {isExit ? "Exit" : "Entry"}
    </span>
  );
}

export function PortfolioOrdersList({ orders }: { orders: OrderReceipt[] }) {
  if (!orders || orders.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-14 text-center">
        <span className="grid h-12 w-12 place-items-center rounded-xl border border-white/8 bg-white/4">
          <ClipboardList className="h-5 w-5 text-[#547D83]" aria-hidden="true" />
        </span>
        <p className="text-[13px] text-[#64748B]">No paper orders submitted in this period.</p>
      </div>
    );
  }

  return (
    <ul className="divide-y divide-white/6" role="list">
      {orders.map((order, i) => (
        <li key={`${order.occurredAt}-${i}`} className="px-4 py-3">
          {/* Top row: time + symbol + side badge */}
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <time dateTime={order.occurredAt} className="font-mono text-[10px] text-[#64748B]">
              {formatOrderTime(order.occurredAt)}
            </time>
            <span aria-hidden="true" className="text-[10px] text-white/20">
              |
            </span>
            <span className="font-mono text-[11px] font-bold text-[#F8FAFC]">{order.symbol}</span>
            <SideBadge side={order.side} />
          </div>

          {/* Middle row: strategy name */}
          <p className="mt-1 text-[12px] font-medium text-[#CBD5E1]">{order.strategy}</p>

          {/* Bottom row: qty · fill price · status */}
          <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1">
            <span className="font-mono text-[11px] text-[#94A3B8]">{order.quantity}</span>
            {order.fillPrice !== "—" && (
              <span className="font-mono text-[11px] font-semibold text-[#00D084]">
                {order.fillPrice} avg
              </span>
            )}
            <StatusBadge status={order.status} />
          </div>
        </li>
      ))}
    </ul>
  );
}
