"use client";

import { Download } from "lucide-react";
import { useCallback } from "react";

import type { components } from "@/types/api.generated";

type Position = components["schemas"]["Position"];

const provenanceLabels: Record<Position["provenance"], string> = {
  illustrative_fixture: "Illustrative fixture",
  alpaca_paper: "Alpaca paper",
  shadow: "ShadowFund",
  benchmark: "Benchmark",
  simulated: "Simulated",
  planned_integration: "Planned integration",
};

function pnlTone(pnl: string) {
  if (pnl.startsWith("+")) return "text-[#00D084]";
  if (pnl.startsWith("-")) return "text-[#FF6B6B]";
  return "text-slate-300";
}

function toCsv(positions: Position[]) {
  const header = ["Ticker", "Position Size", "Value", "Unrealized P&L", "Provenance"];
  const rows = positions.map((position) => [
    position.symbol,
    position.allocation,
    position.value,
    position.pnl,
    provenanceLabels[position.provenance] ?? position.provenance,
  ]);
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
    return <p className="inline-empty">No holdings fall inside this date range.</p>;
  }

  return (
    <div className="holdings-panel">
      <div className="holdings-panel-toolbar">
        <button type="button" className="csv-button" onClick={exportCsv}>
          <Download aria-hidden="true" /> Export CSV
        </button>
      </div>
      <div
        className="holdings-table-scroll"
        role="region"
        aria-label="Current holdings"
        tabIndex={0}
      >
        <table className="holdings-table">
          <caption className="sr-only">
            Current backend holdings with position size, value, and unrealized profit and loss. All
            figures are an illustrative fixture; no account was contacted.
          </caption>
          <thead>
            <tr>
              <th scope="col">Ticker</th>
              <th scope="col">Position Size</th>
              <th scope="col">Value</th>
              <th scope="col" className="holdings-num">
                Unrealized P&amp;L
              </th>
            </tr>
          </thead>
          <tbody>
            {positions.map((position) => (
              <tr key={position.symbol}>
                <th scope="row">
                  <span className="holdings-ticker">{position.symbol}</span>
                  <span className="holdings-provenance">
                    {provenanceLabels[position.provenance] ?? position.provenance}
                  </span>
                </th>
                <td className="font-mono tabular-nums">{position.allocation}</td>
                <td className="font-mono tabular-nums">{position.value}</td>
                <td
                  className={`holdings-num font-mono tabular-nums font-semibold ${pnlTone(position.pnl)}`}
                >
                  {position.pnl}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
