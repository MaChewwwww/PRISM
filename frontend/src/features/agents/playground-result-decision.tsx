import { ShieldCheck } from "lucide-react";

import type { ObjectReportData } from "./playground-types";

/** Renders the full CIO Master Agent (#7) decision synthesis result. */
export function DecisionResult({ data }: { data: ObjectReportData }) {
  return (
    <div className="space-y-4">
      {/* Verdict Banner */}
      <div
        className={`rounded-xl border p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 ${
          data.verdict === "proceed_to_options_proposal"
            ? "border-emerald-500/30 bg-emerald-950/20"
            : "border-amber-500/30 bg-amber-950/20"
        }`}
      >
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-white/10 text-white">
              Verdict
            </span>
            <span
              className={`text-sm font-bold uppercase ${
                data.verdict === "proceed_to_options_proposal"
                  ? "text-emerald-400"
                  : "text-amber-400"
              }`}
            >
              {data.verdict?.replaceAll("_", " ")}
            </span>
          </div>
          <p className="text-xs text-slate-300 mt-1">
            Structure:{" "}
            <span className="font-semibold text-white uppercase">
              {data.recommended_structure?.replaceAll("_", " ")}
            </span>{" "}
            | Direction:{" "}
            <span className="font-semibold text-white uppercase">{data.direction}</span>
          </p>
        </div>

        <div className="flex flex-wrap gap-4 text-xs font-mono">
          <div>
            <span className="text-slate-400 block text-[10px]">Net EV</span>
            <span className="font-bold text-emerald-400">+{data.net_ev_r}R</span>
          </div>
          <div>
            <span className="text-slate-400 block text-[10px]">Reward / Risk</span>
            <span className="font-bold text-cyan-400">{data.reward_risk_ratio}:1</span>
          </div>
          <div>
            <span className="text-slate-400 block text-[10px]">Composite Score</span>
            <span className="font-bold text-white">{data.composite_opportunity_score}/100</span>
          </div>
        </div>
      </div>

      {/* Specialist Scores Grid */}
      {data.specialist_scores && (
        <div>
          <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
            Synthesized 6-Specialist Scores
          </h4>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2">
            {[
              {
                label: "Reaction",
                value: data.specialist_scores.reaction_opportunity_score,
                color: "text-cyan-400",
              },
              {
                label: "Quant",
                value: data.specialist_scores.quant_momentum_score,
                color: "text-indigo-400",
              },
              {
                label: "Fundamental",
                value: data.specialist_scores.fundamental_quality_score,
                color: "text-emerald-400",
              },
              {
                label: "Industry",
                value: data.specialist_scores.sector_health_score,
                color: "text-amber-400",
              },
              {
                label: "Macro",
                value: data.specialist_scores.macro_climate_score,
                color: "text-pink-400",
              },
              {
                label: "News",
                value: data.specialist_scores.news_sentiment_score,
                color: "text-purple-400",
              },
            ].map((s) => (
              <div
                key={s.label}
                className="rounded-lg border border-white/5 bg-[#0F151D] p-2.5 text-center"
              >
                <span className="text-[10px] text-slate-400 block">{s.label}</span>
                <span className={`text-sm font-bold ${s.color}`}>{s.value}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Evidence Summary */}
      {data.evidence_summary && data.evidence_summary.length > 0 && (
        <div className="rounded-xl border border-white/5 bg-[#0F151D] p-4">
          <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
            Cross-Agent Evidence Summary
          </h4>
          <ul className="space-y-1.5 text-xs text-slate-300 list-disc list-inside">
            {data.evidence_summary.map((point, idx) => (
              <li key={idx}>{point}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Contradictions Breakdown */}
      {data.contradictions && data.contradictions.length > 0 && (
        <div className="rounded-xl border border-amber-500/20 bg-amber-950/10 p-4">
          <h4 className="text-xs font-semibold text-amber-400 uppercase tracking-wider mb-2">
            Identified Contradictions
          </h4>
          <ul className="space-y-1 text-xs text-amber-200 list-disc list-inside">
            {data.contradictions.map((c, idx) => (
              <li key={idx}>{c}</li>
            ))}
          </ul>
          {data.contradiction_analysis && (
            <p className="text-xs text-slate-300 mt-2 pt-2 border-t border-amber-500/20">
              <span className="font-semibold text-white">Reconciliation: </span>
              {data.contradiction_analysis}
            </p>
          )}
        </div>
      )}

      {/* Portfolio Fit & Invariants */}
      {data.portfolio_fit && (
        <div className="rounded-xl border border-white/5 bg-[#0F151D] p-4 text-xs text-slate-300">
          <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
            Portfolio Fit & Options Constraint
          </h4>
          <p>{data.portfolio_fit}</p>
          <div className="flex items-center gap-2 mt-2 text-emerald-400 font-medium">
            <ShieldCheck className="h-4 w-4" />
            Options-Only Paper Invariant Acknowledged & Enforced
          </div>
        </div>
      )}
    </div>
  );
}
