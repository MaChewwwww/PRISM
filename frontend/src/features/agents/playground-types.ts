import type { LucideIcon } from "lucide-react";
import {
  Activity,
  BrainCircuit,
  Building2,
  FileSpreadsheet,
  Globe2,
  LineChart,
  Newspaper,
} from "lucide-react";

/* ------------------------------------------------------------------ */
/*  Agent action union and registry                                   */
/* ------------------------------------------------------------------ */

export type AgentAction =
  "decision" | "news" | "quant" | "fundamental" | "industry" | "macro" | "reaction";

export interface AgentOption {
  id: AgentAction;
  name: string;
  shortName: string;
  role: string;
  icon: LucideIcon;
  badge: string;
  accent: string;
  isAllAgents?: boolean;
}

export const AGENTS: AgentOption[] = [
  {
    id: "decision",
    name: "Trading Decision Synthesizer (CIO Master Agent #7)",
    shortName: "CIO Master Synthesizer",
    role: "Runs all 6 research specialists concurrently and executes governed multi-agent synthesis.",
    icon: BrainCircuit,
    badge: "All 7 Agents",
    accent: "#38bdf8",
    isAllAgents: true,
  },
  {
    id: "fundamental",
    name: "Fundamental Analysis Agent (#3)",
    shortName: "Fundamental Analysis",
    role: "Piotroski F-Score (0-9), Altman Z-Score distress zones, valuation multiples, and margin surprises.",
    icon: FileSpreadsheet,
    badge: "Specialist #3",
    accent: "#10b981",
  },
  {
    id: "quant",
    name: "Quantitative Analysis Agent (#2)",
    shortName: "Quantitative Engine",
    role: "RSI conditions, MACD crossovers, Bollinger Bands %B, ATR, Realized Volatility, and price gaps.",
    icon: LineChart,
    badge: "Specialist #2",
    accent: "#818cf8",
  },
  {
    id: "industry",
    name: "Industry Intelligence Agent (#4)",
    shortName: "Industry Intelligence",
    role: "Stock-vs-SPY 20d alpha, sector momentum, peer dispersion, and regime confirmation.",
    icon: Building2,
    badge: "Specialist #4",
    accent: "#f59e0b",
  },
  {
    id: "macro",
    name: "Macroeconomic Intelligence Agent (#5)",
    shortName: "Macro Intelligence",
    role: "8-benchmark regime registry (TLT, VXX, SPY), stress direction, and economic event proximity.",
    icon: Globe2,
    badge: "Specialist #5",
    accent: "#ec4899",
  },
  {
    id: "reaction",
    name: "Market Reaction Agent (#6)",
    shortName: "Market Reaction",
    role: "Direction-adjusted mispricing gap, historical analogs, options IV/HV ratio, and catalyst decay.",
    icon: Activity,
    badge: "Specialist #6",
    accent: "#06b6d4",
  },
  {
    id: "news",
    name: "News Intelligence Agent (#1)",
    shortName: "News Intelligence",
    role: "Live multi-source catalyst extraction, event categorization, materiality, and earnings surprises.",
    icon: Newspaper,
    badge: "Specialist #1",
    accent: "#a855f7",
  },
];

export const PRESET_TICKERS = ["NVDA", "AAPL", "MSFT", "TSLA", "AMZN", "GOOGL", "META"];

/* ------------------------------------------------------------------ */
/*  Report data shapes returned from FastAPI                          */
/* ------------------------------------------------------------------ */

export interface DecisionReportData {
  schema_version?: string;
  verdict?: string;
  recommended_structure?: string;
  direction?: string;
  net_ev_r?: string;
  reward_risk_ratio?: string;
  composite_opportunity_score?: string;
  specialist_scores?: {
    reaction_opportunity_score?: string;
    quant_momentum_score?: string;
    fundamental_quality_score?: string;
    sector_health_score?: string;
    macro_climate_score?: string;
    news_sentiment_score?: string;
  };
  evidence_summary?: string[];
  contradictions?: string[];
  contradiction_analysis?: string;
  portfolio_fit?: string;
}

export interface FundamentalReportData {
  schema_version?: string;
  piotroski_f_score?: number;
  altman_z_score?: string;
  altman_zone?: string;
  fundamental_health?: string;
  valuation_stance?: string;
  profitability?: {
    gross_margin_pct?: string;
    operating_margin_pct?: string;
    net_margin_pct?: string;
    roe_pct?: string;
    roa_pct?: string;
  };
  balance_sheet_red_flags?: string[];
}

export interface QuantReportData {
  schema_version?: string;
  momentum_score?: string;
  rsi_14?: string;
  rsi_condition?: string;
  trend?: string;
  trend_confirmation?: string;
  volatility_annualized_pct?: string;
  atr_14?: string;
  bollinger_bands?: {
    upper?: string;
    middle?: string;
    lower?: string;
    percent_b?: string;
  };
}

export interface IndustryReportData {
  schema_version?: string;
  stock_vs_spy_20d_pct?: string;
  competitive_moat?: string;
  overall_sentiment?: string;
  peer_dispersion_pct?: string;
  thesis?: string;
}

export interface MacroReportData {
  schema_version?: string;
  macro_regime?: string;
  rate_environment?: string;
  stress_direction?: string;
  economic_event_proximity?: string;
  thesis?: string;
}

export interface ReactionReportData {
  schema_version?: string;
  direction_adjusted_gap_pct?: string;
  classification?: string;
  iv_hv_ratio?: string;
  options_implied_move_pct?: string;
  catalyst_decay_status?: string;
  catalyst_decay_factor?: string;
  thesis?: string;
}

export interface NewsArticleData {
  headline?: string;
  event_category?: string;
  rationale?: string;
  sentiment?: string;
  catalyst_materiality?: string;
  expected_reaction_pct?: string;
}

/** Non-array report shape: every specialist shares a single flat object. */
export type ObjectReportData = DecisionReportData &
  FundamentalReportData &
  QuantReportData &
  IndustryReportData &
  MacroReportData &
  ReactionReportData;

/** News returns an array; everything else returns a flat object. */
export type PlaygroundResult = ObjectReportData | NewsArticleData[];
