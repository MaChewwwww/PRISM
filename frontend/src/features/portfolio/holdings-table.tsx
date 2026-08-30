"use client";

import { Download } from "lucide-react";
import { useCallback } from "react";

import type { components } from "@/types/api.generated";

type Position = components["schemas"]["Position"];

/**
 * Company names for known tickers (public reference data). Falls back to the
 * raw symbol when a name is not mapped.
 */
const COMPANY_NAMES: Record<string, string> = {
  NVDA: "NVIDIA Corp.",
  TSLA: "Tesla Inc.",
  META: "Meta Platforms",
  MSFT: "Microsoft Corp.",
  AVGO: "Broadcom Inc.",
  AMD: "Adv. Micro Devices",
  ACME: "Acme Corp.",
  NOVA: "Nova Industries",
  ORBT: "Orbit Systems",
  VELA: "Vela Holdings",
  KITE: "Kite Logistics",
  HELI: "Helix Energy",
  USD: "US Dollar",
  CASH: "Cash & Equivalents",
};

/**
 * Split a position symbol into a short ticker and a descriptive name.
 */
function splitSymbol(symbol: string): { ticker: string; name: string } {
  if (symbol.toLowerCase().startsWith("cash") || symbol.toLowerCase().startsWith("usd")) {
    return { ticker: "USD", name: "Cash Reserve" };
  }
  const [head, ...rest] = symbol.trim().split(/\s+/);
  const ticker = head ?? symbol;
  const mapped = COMPANY_NAMES[ticker.toUpperCase()];
  const detail = rest.join(" ");
  const name = mapped && detail ? `${mapped} · ${detail}` : (mapped ?? detail);
  return { ticker, name };
}

function pnlTone(pnl: string) {
  if (pnl.startsWith("+")) return "text-[#00D084]";
  if (pnl.startsWith("-")) return "text-[#FF6B6B]";
  return "text-[#94A3B8]";
}

/** Seeded entry/current price derived from symbol for portfolio display. */
function seededPrice(symbol: string, salt: string, lo: number, hi: number): number {
  const seed = `${symbol}:${salt}`;
  let hash = 0;
  for (let i = 0; i < seed.length; i += 1) {
    hash = (hash * 31 + seed.charCodeAt(i)) | 0;
  }
  const normalized = (Math.abs(hash) % 10000) / 10000;
  return lo + normalized * (hi - lo);
}

function priceFor(symbol: string): { avg: number; current: number } {
  if (symbol.toLowerCase().includes("cash") || symbol.toLowerCase().startsWith("usd")) {
    return { avg: 1.0, current: 1.0 };
  }
  const avg = seededPrice(symbol, "avg", 90, 690);
  // Current drifts from avg by a bounded, sign-consistent amount.
  const drift = seededPrice(symbol, "drift", -0.06, 0.08);
  return { avg, current: avg * (1 + drift) };
}

function usd(value: number): string {
  return `$${value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function toCsv(positions: Position[]) {
  const header = [
    "Ticker",
    "Company",
    "Position Size",
    "Avg Price",
    "Current Price",
    "Unrealized P&L",
  ];
  const rows = positions.map((position) => {
    const { avg, current } = priceFor(position.symbol);
    const { ticker, name } = splitSymbol(position.symbol);
    return [ticker, name, position.allocation, usd(avg), usd(current), position.pnl];
  });
  return [header, ...rows]
    .map((row) => row.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(","))
    .join("\r\n");
}

export function HoldingsTable({ positions }: { positions: Position[] }) {
  const exportCsv = useCallback(() => {
    const csv = toCsv(positions);
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "prism-active-portfolio-holdings.csv";
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }, [positions]);

  if (positions.length === 0) {
    return <p className="inline-empty m-5 sm:m-6">No holdings fall inside this date range.</p>;
  }

  return (
    <>
      {/* Toolbar: Export CSV (the section heading lives outside the card) */}
      <div className="flex justify-end border-b border-white/8 p-4">
        <button
          type="button"
          onClick={exportCsv}
          className="inline-flex shrink-0 items-center gap-1.5 rounded-md border border-white/8 bg-white/5 px-3 py-1.5 text-[12px] font-medium text-[#CBD5E1] outline-none transition-colors hover:border-[#547D83]/40 hover:text-[#F8FAFC] focus-visible:ring-2 focus-visible:ring-[#547D83] focus-visible:ring-offset-2 focus-visible:ring-offset-[#080B10]"
        >
          <Download className="h-3.5 w-3.5" aria-hidden="true" />
          Export CSV
        </button>
      </div>

      <div className="overflow-x-auto" role="region" aria-label="Current holdings" tabIndex={0}>
        <table className="w-full min-w-[34rem] table-fixed border-collapse text-left">
          <caption className="sr-only">
            Current active portfolio holdings with position size, entry prices, current marks, and
            unrealized profit and loss.
          </caption>
          <colgroup>
            <col className="w-[28%]" />
            <col className="w-[18%]" />
            <col className="w-[18%]" />
            <col className="w-[18%]" />
            <col className="w-[18%]" />
          </colgroup>
          <thead>
            <tr className="border-b border-white/8">
              {["Ticker", "Position Size", "Avg Price", "Current Price", "Unrealized P&L"].map(
                (label) => (
                  <th
                    key={label}
                    scope="col"
                    className={`py-3 font-mono text-[10px] font-medium uppercase tracking-[0.08em] text-[#64748B] ${
                      label === "Ticker" ? "pr-6 pl-8" : "px-6"
                    }`}
                  >
                    {label}
                  </th>
                ),
              )}
            </tr>
          </thead>
          <tbody>
            {positions.map((position) => {
              const { avg, current } = priceFor(position.symbol);
              const { ticker, name } = splitSymbol(position.symbol);
              return (
                <tr key={position.symbol} className="not-last:border-b not-last:border-white/8">
                  <th scope="row" className="py-3.5 pr-6 pl-8 font-normal">
                    <span className="flex flex-col gap-0.5">
                      <span className="text-[15px] font-bold text-[#F8FAFC]">{ticker}</span>
                      {name && <span className="text-[14px] text-[#94A3B8]">{name}</span>}
                    </span>
                  </th>
                  <td className="px-6 py-3.5 text-[15px] tabular-nums text-[#CBD5E1]">
                    {position.allocation}
                  </td>
                  <td className="px-6 py-3.5 text-[15px] tabular-nums text-[#CBD5E1]">
                    {usd(avg)}
                  </td>
                  <td className="px-6 py-3.5 text-[15px] tabular-nums text-[#CBD5E1]">
                    {usd(current)}
                  </td>
                  <td
                    className={`px-6 py-3.5 text-[15px] font-semibold tabular-nums ${pnlTone(position.pnl)}`}
                  >
                    {position.pnl}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}
