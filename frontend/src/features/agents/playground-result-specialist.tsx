import type { AgentAction, NewsArticleData, ObjectReportData } from "./playground-types";

/* ------------------------------------------------------------------ */
/*  Fundamental Agent (#3)                                            */
/* ------------------------------------------------------------------ */

function FundamentalResult({ data }: { data: ObjectReportData }) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-3 text-center">
          <span className="text-[10px] text-slate-400 block">Piotroski F-Score</span>
          <span className="text-2xl font-bold text-emerald-400">
            {data.piotroski_f_score ?? "—"}
            <span className="text-xs font-normal text-slate-400">/9</span>
          </span>
        </div>
        <div className="rounded-xl border border-cyan-500/30 bg-cyan-950/20 p-3 text-center">
          <span className="text-[10px] text-slate-400 block">Altman Z-Score</span>
          <span className="text-2xl font-bold text-cyan-400">{data.altman_z_score ?? "—"}</span>
          <span className="text-[10px] uppercase font-semibold text-slate-300 block">
            Zone: {data.altman_zone ?? "Safe"}
          </span>
        </div>
        <div className="rounded-xl border border-white/5 bg-[#0F151D] p-3 text-center">
          <span className="text-[10px] text-slate-400 block">Health Stance</span>
          <span className="text-sm font-bold text-white uppercase mt-1 block">
            {data.fundamental_health}
          </span>
        </div>
        <div className="rounded-xl border border-white/5 bg-[#0F151D] p-3 text-center">
          <span className="text-[10px] text-slate-400 block">Valuation</span>
          <span className="text-sm font-bold text-white uppercase mt-1 block">
            {data.valuation_stance}
          </span>
        </div>
      </div>

      {data.profitability && (
        <div className="rounded-xl border border-white/5 bg-[#0F151D] p-4">
          <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
            Margins & Capital Efficiency
          </h4>
          <div className="grid grid-cols-3 sm:grid-cols-5 gap-2 text-xs font-mono">
            {[
              {
                label: "Gross Margin",
                value: data.profitability.gross_margin_pct,
                color: "text-white",
              },
              {
                label: "Operating Margin",
                value: data.profitability.operating_margin_pct,
                color: "text-white",
              },
              {
                label: "Net Margin",
                value: data.profitability.net_margin_pct,
                color: "text-white",
              },
              { label: "ROE", value: data.profitability.roe_pct, color: "text-emerald-400" },
              { label: "ROA", value: data.profitability.roa_pct, color: "text-emerald-400" },
            ].map((m) => (
              <div key={m.label}>
                <span className="text-slate-400 block text-[10px]">{m.label}</span>
                <span className={`font-bold ${m.color}`}>{m.value}%</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {data.balance_sheet_red_flags && data.balance_sheet_red_flags.length > 0 && (
        <div className="rounded-xl border border-amber-500/20 bg-amber-950/10 p-3 text-xs text-amber-200">
          <span className="font-semibold text-amber-300">Balance Sheet Flags: </span>
          {data.balance_sheet_red_flags.join(", ")}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Quantitative Agent (#2)                                           */
/* ------------------------------------------------------------------ */

function QuantResult({ data }: { data: ObjectReportData }) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="rounded-xl border border-indigo-500/30 bg-indigo-950/20 p-3 text-center">
          <span className="text-[10px] text-slate-400 block">Momentum Score</span>
          <span className="text-2xl font-bold text-indigo-400">{data.momentum_score}/100</span>
        </div>
        <div className="rounded-xl border border-white/5 bg-[#0F151D] p-3 text-center">
          <span className="text-[10px] text-slate-400 block">RSI (14)</span>
          <span className="text-xl font-bold text-white">{data.rsi_14}</span>
          <span className="text-[10px] uppercase text-slate-400 block">{data.rsi_condition}</span>
        </div>
        <div className="rounded-xl border border-white/5 bg-[#0F151D] p-3 text-center">
          <span className="text-[10px] text-slate-400 block">Trend</span>
          <span className="text-sm font-bold text-white uppercase mt-1 block">{data.trend}</span>
          <span className="text-[10px] text-slate-400 block">{data.trend_confirmation}</span>
        </div>
        <div className="rounded-xl border border-white/5 bg-[#0F151D] p-3 text-center">
          <span className="text-[10px] text-slate-400 block">Realized Volatility</span>
          <span className="text-xl font-bold text-cyan-400">{data.volatility_annualized_pct}%</span>
          <span className="text-[10px] text-slate-400 block">ATR: ${data.atr_14}</span>
        </div>
      </div>

      {data.bollinger_bands && (
        <div className="rounded-xl border border-white/5 bg-[#0F151D] p-4 text-xs font-mono">
          <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2 font-sans">
            Bollinger Bands (20, 2)
          </h4>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {[
              { label: "Upper Band", value: `$${data.bollinger_bands.upper}`, color: "text-white" },
              {
                label: "Middle (SMA20)",
                value: `$${data.bollinger_bands.middle}`,
                color: "text-white",
              },
              { label: "Lower Band", value: `$${data.bollinger_bands.lower}`, color: "text-white" },
              {
                label: "Percent %B",
                value: data.bollinger_bands.percent_b,
                color: "text-cyan-400",
              },
            ].map((b) => (
              <div key={b.label}>
                <span className="text-slate-400 block text-[10px]">{b.label}</span>
                <span className={`font-bold ${b.color}`}>{b.value}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Industry Agent (#4)                                               */
/* ------------------------------------------------------------------ */

function IndustryResult({ data }: { data: ObjectReportData }) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="rounded-xl border border-amber-500/30 bg-amber-950/20 p-3 text-center">
          <span className="text-[10px] text-slate-400 block">Stock vs SPY (20d)</span>
          <span className="text-xl font-bold text-amber-400">
            {data.stock_vs_spy_20d_pct ? `${data.stock_vs_spy_20d_pct}%` : "—"}
          </span>
        </div>
        <div className="rounded-xl border border-white/5 bg-[#0F151D] p-3 text-center">
          <span className="text-[10px] text-slate-400 block">Competitive Moat</span>
          <span className="text-sm font-bold text-white uppercase mt-1 block">
            {data.competitive_moat}
          </span>
        </div>
        <div className="rounded-xl border border-white/5 bg-[#0F151D] p-3 text-center">
          <span className="text-[10px] text-slate-400 block">Sector Sentiment</span>
          <span className="text-sm font-bold text-white uppercase mt-1 block">
            {data.overall_sentiment}
          </span>
        </div>
        <div className="rounded-xl border border-white/5 bg-[#0F151D] p-3 text-center">
          <span className="text-[10px] text-slate-400 block">Peer Dispersion</span>
          <span className="text-sm font-bold text-white mt-1 block">
            {data.peer_dispersion_pct ? `${data.peer_dispersion_pct}%` : "—"}
          </span>
        </div>
      </div>
      <div className="rounded-xl border border-white/5 bg-[#0F151D] p-4 text-xs text-slate-300">
        <h4 className="font-semibold text-white mb-1">Industry Thesis</h4>
        <p>{data.thesis}</p>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Macro Agent (#5)                                                  */
/* ------------------------------------------------------------------ */

function MacroResult({ data }: { data: ObjectReportData }) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="rounded-xl border border-pink-500/30 bg-pink-950/20 p-3 text-center">
          <span className="text-[10px] text-slate-400 block">Macro Regime</span>
          <span className="text-sm font-bold text-pink-400 uppercase mt-1 block">
            {data.macro_regime}
          </span>
        </div>
        <div className="rounded-xl border border-white/5 bg-[#0F151D] p-3 text-center">
          <span className="text-[10px] text-slate-400 block">Rate Environment</span>
          <span className="text-sm font-bold text-white uppercase mt-1 block">
            {data.rate_environment?.replaceAll("_", " ")}
          </span>
        </div>
        <div className="rounded-xl border border-white/5 bg-[#0F151D] p-3 text-center">
          <span className="text-[10px] text-slate-400 block">Stress Direction</span>
          <span className="text-sm font-bold text-white uppercase mt-1 block">
            {data.stress_direction}
          </span>
        </div>
        <div className="rounded-xl border border-white/5 bg-[#0F151D] p-3 text-center">
          <span className="text-[10px] text-slate-400 block">Event Proximity</span>
          <span className="text-xs font-bold text-cyan-400 uppercase mt-1 block">
            {data.economic_event_proximity?.replaceAll("_", " ")}
          </span>
        </div>
      </div>
      <div className="rounded-xl border border-white/5 bg-[#0F151D] p-4 text-xs text-slate-300">
        <h4 className="font-semibold text-white mb-1">Macro Sensitivity Thesis</h4>
        <p>{data.thesis}</p>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Reaction Agent (#6)                                               */
/* ------------------------------------------------------------------ */

function ReactionResult({ data }: { data: ObjectReportData }) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="rounded-xl border border-cyan-500/30 bg-cyan-950/20 p-3 text-center">
          <span className="text-[10px] text-slate-400 block">Reaction Gap</span>
          <span className="text-2xl font-bold text-cyan-400">
            {data.direction_adjusted_gap_pct}%
          </span>
        </div>
        <div className="rounded-xl border border-white/5 bg-[#0F151D] p-3 text-center">
          <span className="text-[10px] text-slate-400 block">Classification</span>
          <span className="text-sm font-bold text-white uppercase mt-1 block">
            {data.classification}
          </span>
        </div>
        <div className="rounded-xl border border-white/5 bg-[#0F151D] p-3 text-center">
          <span className="text-[10px] text-slate-400 block">IV / HV Ratio</span>
          <span className="text-xl font-bold text-indigo-400">{data.iv_hv_ratio}x</span>
        </div>
        <div className="rounded-xl border border-white/5 bg-[#0F151D] p-3 text-center">
          <span className="text-[10px] text-slate-400 block">Catalyst Decay</span>
          <span className="text-xs font-bold text-emerald-400 uppercase mt-1 block">
            {data.catalyst_decay_status?.replaceAll("_", " ")}
          </span>
          <span className="text-[10px] text-slate-400 block">
            Factor: {data.catalyst_decay_factor}
          </span>
        </div>
      </div>
      <div className="rounded-xl border border-white/5 bg-[#0F151D] p-4 text-xs text-slate-300">
        <h4 className="font-semibold text-white mb-1">Mispricing Thesis</h4>
        <p>{data.thesis}</p>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  News Agent (#1)                                                   */
/* ------------------------------------------------------------------ */

function NewsResult({ data }: { data: NewsArticleData[] }) {
  return (
    <div className="space-y-3">
      <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
        Analyzed Articles ({data.length})
      </h4>
      {data.map((article, idx) => (
        <div
          key={idx}
          className="rounded-xl border border-white/5 bg-[#0F151D] p-3 space-y-2 text-xs"
        >
          <div className="flex items-start justify-between gap-2">
            <h5 className="font-semibold text-white">{String(article.headline ?? "")}</h5>
            <span className="text-[10px] uppercase px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30 whitespace-nowrap">
              {String(article.event_category ?? "").replaceAll("_", " ")}
            </span>
          </div>
          <p className="text-slate-400">{String(article.rationale ?? "")}</p>
          <div className="flex items-center gap-4 text-[11px] font-mono text-slate-400">
            <span>
              Sentiment:{" "}
              <strong className="text-white uppercase">{String(article.sentiment ?? "")}</strong>
            </span>
            <span>
              Materiality:{" "}
              <strong className="text-white uppercase">
                {String(article.catalyst_materiality ?? "")}
              </strong>
            </span>
            {article.expected_reaction_pct != null && (
              <span>
                Expected Move:{" "}
                <strong className="text-cyan-400">+{String(article.expected_reaction_pct)}%</strong>
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Router: pick the right sub-component by agent action              */
/* ------------------------------------------------------------------ */

export function SpecialistResult({
  agent,
  data,
}: {
  agent: AgentAction;
  data: ObjectReportData | NewsArticleData[];
}) {
  if (agent === "news" && Array.isArray(data)) return <NewsResult data={data} />;
  if (Array.isArray(data)) return null;

  switch (agent) {
    case "fundamental":
      return <FundamentalResult data={data} />;
    case "quant":
      return <QuantResult data={data} />;
    case "industry":
      return <IndustryResult data={data} />;
    case "macro":
      return <MacroResult data={data} />;
    case "reaction":
      return <ReactionResult data={data} />;
    default:
      return null;
  }
}
