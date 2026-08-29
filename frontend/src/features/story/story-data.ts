export const FIXTURE_TODAY = "2026-08-28";

export type RangePreset = "7d" | "1m" | "3m" | "ytd" | "custom";

export type DateRange = {
  preset: RangePreset;
  from: string;
  to: string;
};

export type SearchValues = Record<string, string | string[] | undefined>;

export type Provenance =
  | "active-portfolio"
  | "shadow-portfolio"
  | "market-benchmark"
  | "illustrative-paper"
  | "simulated"
  | "planned-integration";

export type StoryOutcome = "pass" | "modify" | "fail" | "no_trade" | "degraded";

export type StorySummary = {
  id: string;
  occurredAt: string;
  symbol: string;
  category: string;
  title: string;
  summary: string;
  outcome: StoryOutcome;
  ruleResult: "PASS" | "MODIFY" | "FAIL" | "NOT_EVALUATED";
  paperImpact: string;
  bestAlternativeImpact: string;
  lesson: string;
};

export type ChartPoint = {
  date: string;
  actual: string;
  alternative?: string;
  benchmark?: string;
};

export type DecisionNode = {
  id: string;
  parentId: string | null;
  label: string;
  actor: string;
  status: string;
  detail: string;
};

export type TranscriptStep = {
  id: string;
  occurredAt: string;
  kind: "agent-summary" | "tool-call" | "rule-gate";
  actor: string;
  title: string;
  summary: string;
  model?: string;
  promptVersion?: string;
  inputTokens?: number;
  outputTokens?: number;
  latencyMs?: number;
  evidenceRefs: string[];
};

export type RuleCheck = {
  name: string;
  result: "PASS" | "MODIFY" | "FAIL" | "TBD";
  explanation: string;
};

export type AlternativeBranch = {
  id: string;
  label: string;
  variation: string;
  pnl: string;
  drawdown: string;
  coverage: string;
  status: "complete" | "incomplete";
};

export type StoryDetail = StorySummary & {
  catalyst: {
    headline: string;
    source: string;
    publishedAt: string;
    classification: string;
    observedMove: string;
    expectedMove: string;
  };
  marketPath: ChartPoint[];
  decisionTree: DecisionNode[];
  transcript: TranscriptStep[];
  ruleChecks: RuleCheck[];
  paperOutcome: {
    action: string;
    status: string;
    rationale: string;
    observedAt: string;
  };
  alternatives: AlternativeBranch[];
  lessons: string[];
  evidence: Array<{ label: string; source: string; observedAt: string; provenance: Provenance }>;
};

export type PortfolioPoint = ChartPoint & {
  pnl: string;
  drawdown: string;
};

export type AlternativeSession = {
  id: string;
  storyId: string;
  occurredAt: string;
  symbol: string;
  title: string;
  summary: string;
  actualPnl: string;
  bestBranch: string;
  bestDelta: string;
  coverage: string;
  branches: AlternativeBranch[];
  path: ChartPoint[];
  limitations: string[];
};

export type AgentRun = {
  id: string;
  occurredAt: string;
  status: "complete" | "degraded" | "failed";
  trigger: string;
  durationMs: number;
  inputTokens: number;
  outputTokens: number;
  cachedTokens: number;
  summary: string;
};

export type AgentRecord = {
  id: string;
  name: string;
  role: string;
  cadence: string;
  model: string;
  promptVersion: string;
  description: string;
  dependencies: string[];
  runs: AgentRun[];
};

export type ToolRecord = {
  id: string;
  name: string;
  kind: "SDK" | "Internal" | "MCP" | "LLM";
  state: "used" | "planned";
  calls: number;
  successRate: string;
  medianLatency: string;
  purpose: string;
};

export type NewsRecord = {
  id: string;
  publishedAt: string;
  source: string;
  provider: string;
  symbols: string[];
  headline: string;
  summary: string;
  category: string;
  storyId: string | null;
  significance: "high" | "medium" | "low";
};

export type ConfigurableRule = {
  id: string;
  name: string;
  description: string;
  input: string;
  unit: string;
  activeValue: "TBD";
  effect: string;
};

const presets: Exclude<RangePreset, "custom">[] = ["7d", "1m", "3m", "ytd"];

function dateOffset(date: string, days: number) {
  const parsed = new Date(`${date}T00:00:00.000Z`);
  parsed.setUTCDate(parsed.getUTCDate() + days);
  return parsed.toISOString().slice(0, 10);
}

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

function isIsoDate(value: string | undefined): value is string {
  if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  return !Number.isNaN(new Date(`${value}T00:00:00.000Z`).valueOf());
}

export function rangeForPreset(preset: Exclude<RangePreset, "custom">): DateRange {
  if (preset === "ytd") return { preset, from: "2026-01-01", to: FIXTURE_TODAY };
  const days = preset === "7d" ? 7 : preset === "1m" ? 30 : 90;
  return { preset, from: dateOffset(FIXTURE_TODAY, -days), to: FIXTURE_TODAY };
}

export function readDateRange(values: SearchValues): DateRange {
  const requested = first(values.range);
  if (requested && presets.includes(requested as Exclude<RangePreset, "custom">)) {
    const expected = rangeForPreset(requested as Exclude<RangePreset, "custom">);
    const from = first(values.from);
    const to = first(values.to);
    return isIsoDate(from) && isIsoDate(to) && from <= to
      ? { preset: requested as Exclude<RangePreset, "custom">, from, to }
      : expected;
  }

  const from = first(values.from);
  const to = first(values.to);
  if (requested === "custom" && isIsoDate(from) && isIsoDate(to) && from <= to) {
    return { preset: "custom", from, to };
  }
  return rangeForPreset("1m");
}

export function rangeQuery(range: DateRange) {
  return new URLSearchParams({ range: range.preset, from: range.from, to: range.to }).toString();
}

function inRange(timestamp: string, range: DateRange) {
  const date = timestamp.slice(0, 10);
  return date >= range.from && date <= range.to;
}

export const storySummaries: StorySummary[] = [
  {
    id: "acme-earnings-gap",
    occurredAt: "2026-08-25T14:30:00Z",
    symbol: "ACME",
    category: "Earnings",
    title: "A muted earnings reaction became a smaller, safer idea",
    summary:
      "Research found a reaction gap, Risk AI challenged concentration, and the rules required reduced sizing before the idea could progress.",
    outcome: "modify",
    ruleResult: "MODIFY",
    paperImpact: "+$184.00",
    bestAlternativeImpact: "+$241.00",
    lesson: "Earlier spread selection would have reduced volatility exposure.",
  },
  {
    id: "nova-product-no-trade",
    occurredAt: "2026-08-21T16:10:00Z",
    symbol: "NOVA",
    category: "Product",
    title: "The announcement looked important, but the market had already priced it",
    summary:
      "The agents found no durable reaction gap. NO_TRADE preserved capital and remained a successful governed outcome.",
    outcome: "no_trade",
    ruleResult: "NOT_EVALUATED",
    paperImpact: "$0.00",
    bestAlternativeImpact: "-$96.00",
    lesson: "No action outperformed every simulated entry.",
  },
  {
    id: "orbt-macro-incomplete",
    occurredAt: "2026-08-12T13:05:00Z",
    symbol: "ORBT",
    category: "Macro",
    title: "Incomplete market context stopped the workflow before a proposal",
    summary:
      "A catalyst was detected, but stale comparison data prevented research from advancing into strategy generation.",
    outcome: "degraded",
    ruleResult: "NOT_EVALUATED",
    paperImpact: "$0.00",
    bestAlternativeImpact: "Unavailable",
    lesson: "Freshness coverage needs to be explicit before the agent run starts.",
  },
  {
    id: "vela-guidance-pass",
    occurredAt: "2026-07-29T15:20:00Z",
    symbol: "VELA",
    category: "Guidance",
    title: "A defined-risk structure passed every configured platform control",
    summary:
      "The proposal matched the synthetic evidence, used a bounded debit spread, and passed the illustrative rule trace.",
    outcome: "pass",
    ruleResult: "PASS",
    paperImpact: "+$126.00",
    bestAlternativeImpact: "+$109.00",
    lesson: "The selected hedge improved the result after volatility contracted.",
  },
  {
    id: "kite-liquidity-fail",
    occurredAt: "2026-07-08T14:42:00Z",
    symbol: "KITE",
    category: "Corporate action",
    title: "Thin synthetic option markets turned a plausible thesis into a rejection",
    summary:
      "Risk AI flagged execution uncertainty and the deterministic gate failed because required liquidity configuration was absent.",
    outcome: "fail",
    ruleResult: "FAIL",
    paperImpact: "$0.00",
    bestAlternativeImpact: "-$173.00",
    lesson: "The rejection avoided an optimistic midpoint assumption.",
  },
  {
    id: "heli-sector-rotation",
    occurredAt: "2026-05-19T17:15:00Z",
    symbol: "HELI",
    category: "Sector",
    title: "A broad sector move weakened the single-name explanation",
    summary:
      "Historical analogs showed that the apparent reaction gap was mostly explained by a wider sector rotation.",
    outcome: "no_trade",
    ruleResult: "NOT_EVALUATED",
    paperImpact: "$0.00",
    bestAlternativeImpact: "+$22.00",
    lesson: "Sector-adjusted analogs should be weighted before raw single-name moves.",
  },
  {
    id: "acme-guidance-review",
    occurredAt: "2026-03-11T14:05:00Z",
    symbol: "ACME",
    category: "Guidance",
    title: "Conflicting guidance evidence produced a deliberate fail-closed result",
    summary:
      "The research record contained contradictory sources and the workflow did not create an executable candidate.",
    outcome: "fail",
    ruleResult: "FAIL",
    paperImpact: "$0.00",
    bestAlternativeImpact: "+$31.00",
    lesson: "Source disagreement should be visible before confidence is summarized.",
  },
];

const sharedAlternatives: AlternativeBranch[] = [
  {
    id: "actual",
    label: "Active Portfolio (Paper)",
    variation: "Recorded governed outcome",
    pnl: "+$184.00",
    drawdown: "-$76.00",
    coverage: "96%",
    status: "complete",
  },
  {
    id: "no-action",
    label: "Shadow: Cash Baseline",
    variation: "Remain entirely in cash",
    pnl: "$0.00",
    drawdown: "$0.00",
    coverage: "100%",
    status: "complete",
  },
  {
    id: "reduced-size",
    label: "Shadow: Reduced Sizing",
    variation: "Half the active allocation (50% risk)",
    pnl: "+$102.00",
    drawdown: "-$38.00",
    coverage: "96%",
    status: "complete",
  },
  {
    id: "unhedged",
    label: "Shadow: Unhedged Structure",
    variation: "Long option without the short spread leg",
    pnl: "+$61.00",
    drawdown: "-$164.00",
    coverage: "82%",
    status: "incomplete",
  },
  {
    id: "agent-alternative",
    label: "Shadow: Agent Counterfactual",
    variation: "Earlier expiry with the same bounded structure",
    pnl: "+$241.00",
    drawdown: "-$91.00",
    coverage: "94%",
    status: "complete",
  },
];

function detailFor(summary: StorySummary, index: number): StoryDetail {
  const minute = String(30 + index).padStart(2, "0");
  const passed = summary.ruleResult === "PASS";
  const failed = summary.ruleResult === "FAIL";
  return {
    ...summary,
    catalyst: {
      headline: `${summary.symbol} fictional ${summary.category.toLowerCase()} update changed the evidence set`,
      source: "Illustrative Alpaca News-shaped fixture",
      publishedAt: summary.occurredAt,
      classification:
        summary.outcome === "degraded" ? "Incomplete evidence" : "Potential reaction gap",
      observedMove:
        summary.outcome === "degraded" ? "Unavailable" : `+${(1.1 + index * 0.2).toFixed(1)}%`,
      expectedMove:
        summary.outcome === "degraded" ? "Unavailable" : `+${(2.8 + index * 0.15).toFixed(1)}%`,
    },
    marketPath: [
      { date: "Pre-event", actual: "100.00", alternative: "100.00", benchmark: "100.00" },
      { date: "Catalyst", actual: "101.10", alternative: "101.10", benchmark: "100.30" },
      { date: "+30m", actual: "101.42", alternative: "101.58", benchmark: "100.44" },
      { date: "Close", actual: "102.16", alternative: "102.74", benchmark: "100.61" },
      { date: "+1 session", actual: "103.02", alternative: "103.86", benchmark: "100.92" },
    ],
    decisionTree: [
      {
        id: "catalyst",
        parentId: null,
        label: "Catalyst normalized",
        actor: "Market context",
        status: summary.outcome === "degraded" ? "incomplete" : "ready",
        detail:
          "Fictional news and synthetic bars were timestamped and treated as untrusted evidence.",
      },
      {
        id: "research",
        parentId: "catalyst",
        label: "Reaction gap assessed",
        actor: "Research agent",
        status: summary.outcome === "degraded" ? "stopped" : "complete",
        detail: "Observed movement was compared with illustrative analog outcomes and limitations.",
      },
      {
        id: "proposal",
        parentId: "research",
        label: summary.outcome === "no_trade" ? "NO_TRADE returned" : "Candidate structured",
        actor: "Proposal agent",
        status: summary.outcome === "degraded" ? "not run" : "complete",
        detail: "The agent emitted structured intent only; it did not claim authorization.",
      },
      {
        id: "risk",
        parentId: "proposal",
        label: "Contradictory evidence reviewed",
        actor: "Risk AI",
        status:
          summary.outcome === "degraded" || summary.outcome === "no_trade"
            ? "not required"
            : "complete",
        detail:
          "Portfolio context, volatility exposure, and incomplete inputs were challenged independently.",
      },
      {
        id: "rules",
        parentId: "risk",
        label: "Deterministic gate",
        actor: "Rules engine",
        status: summary.ruleResult,
        detail:
          "Only the rule result can permit progression; fixture evaluation never authorizes execution.",
      },
    ],
    transcript: [
      {
        id: `${summary.id}-step-1`,
        occurredAt: summary.occurredAt.replace(":30:00", `:${minute}:04`),
        kind: "tool-call",
        actor: "News gateway",
        title: "Normalized the catalyst",
        summary:
          "Captured headline, symbols, publication time, receipt time, and source without forwarding credentials.",
        latencyMs: 184,
        evidenceRefs: ["News fixture 01"],
      },
      {
        id: `${summary.id}-step-2`,
        occurredAt: summary.occurredAt,
        kind: "agent-summary",
        actor: "Research agent",
        title: "Compared the reaction with synthetic analogs",
        summary:
          "The initial move appeared smaller than the illustrative analog range, with sector effects retained as a limitation.",
        model: "demo-reasoning-model",
        promptVersion: "reaction-research@1.4",
        inputTokens: 3240 + index * 70,
        outputTokens: 612 + index * 18,
        latencyMs: 4210 + index * 55,
        evidenceRefs: ["News fixture 01", "Bars fixture 07", "Analog set 03"],
      },
      {
        id: `${summary.id}-step-3`,
        occurredAt: summary.occurredAt,
        kind: "agent-summary",
        actor: "Risk AI",
        title: "Challenged sizing and volatility exposure",
        summary:
          "The critique identified missing business configuration and preferred a bounded structure over unhedged exposure.",
        model: "demo-fast-model",
        promptVersion: "risk-critique@1.2",
        inputTokens: 1910 + index * 45,
        outputTokens: 388 + index * 12,
        latencyMs: 2380 + index * 40,
        evidenceRefs: ["Portfolio snapshot fixture", "Synthetic option context"],
      },
      {
        id: `${summary.id}-step-4`,
        occurredAt: summary.occurredAt,
        kind: "rule-gate",
        actor: "Deterministic rules",
        title: `${summary.ruleResult.replace("_", " ")} result recorded`,
        summary:
          "The exact synthetic inputs were checked against platform controls and unconfigured BA fields failed closed.",
        latencyMs: 18,
        evidenceRefs: ["Ruleset demo-draft", "Proposal digest fixture"],
      },
    ],
    ruleChecks: [
      {
        name: "Paper environment",
        result: "PASS",
        explanation: "The prototype represents paper-only behavior and contains no broker action.",
      },
      {
        name: "Supported strategy envelope",
        result: failed ? "FAIL" : "PASS",
        explanation: failed
          ? "The synthetic record did not have enough verified structure to progress."
          : "The illustrative candidate stayed within the documented defined-risk envelope.",
      },
      {
        name: "BA-owned concentration policy",
        result: summary.ruleResult === "MODIFY" ? "MODIFY" : "TBD",
        explanation:
          "The approved business threshold is not configured; no example value is treated as authority.",
      },
      {
        name: "Evidence freshness policy",
        result: summary.outcome === "degraded" ? "FAIL" : "TBD",
        explanation:
          "Freshness remains a configurable business field and incomplete evidence stops progression.",
      },
    ],
    paperOutcome: {
      action:
        summary.outcome === "no_trade" ||
        summary.outcome === "degraded" ||
        summary.outcome === "fail"
          ? "No paper order created"
          : passed
            ? "Illustrative paper outcome recorded"
            : "Modified candidate retained for review",
      status: summary.outcome,
      rationale: summary.summary,
      observedAt: summary.occurredAt,
    },
    alternatives: sharedAlternatives.map((branch) => ({
      ...branch,
      pnl: summary.outcome === "no_trade" && branch.id === "actual" ? "$0.00" : branch.pnl,
    })),
    lessons: [
      summary.lesson,
      "Show evidence disagreement before compressing it into a confidence summary.",
      "Treat the no-action branch as a first-class result, not as a missing trade.",
    ],
    evidence: [
      {
        label: "Catalyst article",
        source: "Alpaca News Market Feed",
        observedAt: summary.occurredAt,
        provenance: "planned-integration",
      },
      {
        label: "Active paper outcome path",
        source: "Alpaca Paper Trading Account",
        observedAt: summary.occurredAt,
        provenance: "active-portfolio",
      },
      {
        label: "ShadowFund counterfactuals",
        source: "ShadowFund Simulation Engine",
        observedAt: summary.occurredAt,
        provenance: "shadow-portfolio",
      },
    ],
  };
}

const storyDetails = storySummaries.map(detailFor);

export function listStories(range: DateRange, filters: { outcome?: string; symbol?: string } = {}) {
  return storySummaries.filter(
    (story) =>
      inRange(story.occurredAt, range) &&
      (!filters.outcome || filters.outcome === "all" || story.outcome === filters.outcome) &&
      (!filters.symbol || filters.symbol === "all" || story.symbol === filters.symbol),
  );
}

export function getStory(id: string) {
  return storyDetails.find((story) => story.id === id);
}

export const portfolioPoints: PortfolioPoint[] = [
  {
    date: "2026-01-02",
    actual: "100000.00",
    alternative: "100000.00",
    benchmark: "100000.00",
    pnl: "0.00",
    drawdown: "0.00",
  },
  {
    date: "2026-02-02",
    actual: "100640.00",
    alternative: "100410.00",
    benchmark: "100330.00",
    pnl: "640.00",
    drawdown: "-210.00",
  },
  {
    date: "2026-03-02",
    actual: "100180.00",
    alternative: "100760.00",
    benchmark: "100520.00",
    pnl: "180.00",
    drawdown: "-690.00",
  },
  {
    date: "2026-04-01",
    actual: "101220.00",
    alternative: "101090.00",
    benchmark: "100810.00",
    pnl: "1220.00",
    drawdown: "-260.00",
  },
  {
    date: "2026-05-01",
    actual: "101080.00",
    alternative: "101420.00",
    benchmark: "101120.00",
    pnl: "1080.00",
    drawdown: "-430.00",
  },
  {
    date: "2026-06-01",
    actual: "101760.00",
    alternative: "101980.00",
    benchmark: "101440.00",
    pnl: "1760.00",
    drawdown: "-220.00",
  },
  {
    date: "2026-07-01",
    actual: "102140.00",
    alternative: "102510.00",
    benchmark: "101720.00",
    pnl: "2140.00",
    drawdown: "-310.00",
  },
  {
    date: "2026-07-08",
    actual: "102040.00",
    alternative: "102620.00",
    benchmark: "101760.00",
    pnl: "2040.00",
    drawdown: "-410.00",
  },
  {
    date: "2026-07-22",
    actual: "102480.00",
    alternative: "102910.00",
    benchmark: "101880.00",
    pnl: "2480.00",
    drawdown: "-180.00",
  },
  {
    date: "2026-07-29",
    actual: "102790.00",
    alternative: "103030.00",
    benchmark: "101960.00",
    pnl: "2790.00",
    drawdown: "-140.00",
  },
  {
    date: "2026-08-05",
    actual: "102610.00",
    alternative: "103260.00",
    benchmark: "102020.00",
    pnl: "2610.00",
    drawdown: "-320.00",
  },
  {
    date: "2026-08-12",
    actual: "102920.00",
    alternative: "103410.00",
    benchmark: "102110.00",
    pnl: "2920.00",
    drawdown: "-110.00",
  },
  {
    date: "2026-08-18",
    actual: "103070.00",
    alternative: "103590.00",
    benchmark: "102160.00",
    pnl: "3070.00",
    drawdown: "-90.00",
  },
  {
    date: "2026-08-21",
    actual: "103120.00",
    alternative: "103720.00",
    benchmark: "102220.00",
    pnl: "3120.00",
    drawdown: "-76.00",
  },
  {
    date: "2026-08-22",
    actual: "103180.00",
    alternative: "103780.00",
    benchmark: "102240.00",
    pnl: "3180.00",
    drawdown: "-54.00",
  },
  {
    date: "2026-08-25",
    actual: "103364.00",
    alternative: "104021.00",
    benchmark: "102310.00",
    pnl: "3364.00",
    drawdown: "-76.00",
  },
  {
    date: "2026-08-28",
    actual: "103840.00",
    alternative: "104620.00",
    benchmark: "102440.00",
    pnl: "3840.00",
    drawdown: "-62.00",
  },
];

export function loadPortfolio(range: DateRange) {
  const points = portfolioPoints.filter(
    (point) => point.date >= range.from && point.date <= range.to,
  );
  return {
    points,
    positions: [
      {
        symbol: "ACME demo spread",
        allocation: "3.2%",
        value: "$3,306.88",
        pnl: "+$184.00",
        provenance: "Active Portfolio (Paper)",
      },
      {
        symbol: "VELA demo spread",
        allocation: "2.1%",
        value: "$2,180.64",
        pnl: "+$126.00",
        provenance: "Active Portfolio (Paper)",
      },
      {
        symbol: "Cash",
        allocation: "94.7%",
        value: "$98,352.48",
        pnl: "$0.00",
        provenance: "Active Portfolio (Paper)",
      },
    ],
    activities: [
      {
        occurredAt: "2026-08-25T19:45:00Z",
        label: "ACME active mark updated",
        detail: "Alpaca paper trading session valuation",
        amount: "+$184.00",
      },
      {
        occurredAt: "2026-08-21T16:14:00Z",
        label: "NOVA no-trade recorded",
        detail: "No account mutation (governed decision)",
        amount: "$0.00",
      },
      {
        occurredAt: "2026-07-29T19:50:00Z",
        label: "VELA active branch closed",
        detail: "Paper trade target reached",
        amount: "+$126.00",
      },
    ].filter((activity) => inRange(activity.occurredAt, range)),
    exposure: [
      { label: "Cash", value: "94.7" },
      { label: "Defined-risk spreads", value: "5.3" },
      { label: "Single-leg options", value: "0.0" },
      { label: "Other", value: "0.0" },
    ],
  };
}

export const alternativeSessions: AlternativeSession[] = [
  {
    id: "session-acme-earnings",
    storyId: "acme-earnings-gap",
    occurredAt: "2026-08-25T14:30:00Z",
    symbol: "ACME",
    title: "Which structure handled the fictional volatility contraction best?",
    summary:
      "The agent alternative finished ahead, while the unhedged branch showed the largest adverse excursion.",
    actualPnl: "+$184.00",
    bestBranch: "Shadow: Agent Counterfactual",
    bestDelta: "+$57.00",
    coverage: "94%",
    branches: sharedAlternatives,
    path: [
      { date: "Entry", actual: "0.00", alternative: "0.00", benchmark: "0.00" },
      { date: "+1h", actual: "48.00", alternative: "64.00", benchmark: "0.00" },
      { date: "Close", actual: "92.00", alternative: "128.00", benchmark: "0.00" },
      { date: "+1 session", actual: "184.00", alternative: "241.00", benchmark: "0.00" },
    ],
    limitations: [
      "All marks are synthetic and do not model queue position or market impact.",
      "The unhedged branch has incomplete quote coverage and may be optimistic.",
      "Simulated branches can inform review but can never become executable orders.",
    ],
  },
  {
    id: "session-vela-guidance",
    storyId: "vela-guidance-pass",
    occurredAt: "2026-07-29T15:20:00Z",
    symbol: "VELA",
    title: "Did the selected hedge improve the fictional guidance trade?",
    summary:
      "The governed paper path retained more value than the unhedged branch after volatility contracted.",
    actualPnl: "+$126.00",
    bestBranch: "Active Portfolio (Paper)",
    bestDelta: "+$17.00",
    coverage: "97%",
    branches: sharedAlternatives.map((branch) => ({
      ...branch,
      pnl: branch.id === "actual" ? "+$126.00" : branch.pnl,
    })),
    path: [
      { date: "Entry", actual: "0.00", alternative: "0.00", benchmark: "0.00" },
      { date: "+1h", actual: "34.00", alternative: "28.00", benchmark: "0.00" },
      { date: "Close", actual: "88.00", alternative: "77.00", benchmark: "0.00" },
      { date: "+1 session", actual: "126.00", alternative: "109.00", benchmark: "0.00" },
    ],
    limitations: [
      "Synthetic marks omit fees and assignment risk.",
      "The comparison uses one illustrative evaluation horizon.",
    ],
  },
  {
    id: "session-nova-no-trade",
    storyId: "nova-product-no-trade",
    occurredAt: "2026-08-21T16:10:00Z",
    symbol: "NOVA",
    title: "How much did no action protect after the announcement?",
    summary: "Every simulated entry finished below the cash baseline in this fictional scenario.",
    actualPnl: "$0.00",
    bestBranch: "No action",
    bestDelta: "+$96.00",
    coverage: "92%",
    branches: sharedAlternatives.map((branch) => ({
      ...branch,
      pnl: branch.id === "actual" || branch.id === "no-action" ? "$0.00" : "-$96.00",
    })),
    path: [
      { date: "Decision", actual: "0.00", alternative: "0.00", benchmark: "0.00" },
      { date: "+1h", actual: "0.00", alternative: "-24.00", benchmark: "0.00" },
      { date: "Close", actual: "0.00", alternative: "-61.00", benchmark: "0.00" },
      { date: "+1 session", actual: "0.00", alternative: "-96.00", benchmark: "0.00" },
    ],
    limitations: ["No-action is a simulated comparison baseline, not an account order."],
  },
];

export function listAlternativeSessions(range: DateRange) {
  return alternativeSessions.filter((session) => inRange(session.occurredAt, range));
}

export function getAlternativeSession(id: string) {
  return alternativeSessions.find((session) => session.id === id);
}

const runDates = [
  "2026-08-25T14:31:00Z",
  "2026-08-21T16:11:00Z",
  "2026-08-12T13:06:00Z",
  "2026-07-29T15:21:00Z",
  "2026-07-08T14:43:00Z",
  "2026-05-19T17:16:00Z",
];

function runsFor(agentId: string, tokenBase: number): AgentRun[] {
  return runDates.map((occurredAt, index) => ({
    id: `${agentId}-run-${index + 1}`,
    occurredAt,
    status: index === 2 ? "degraded" : "complete",
    trigger: index === 5 ? "scheduled review" : "market event",
    durationMs: 2100 + index * 430,
    inputTokens: tokenBase + index * 180,
    outputTokens: Math.round(tokenBase * 0.18) + index * 32,
    cachedTokens: index % 2 === 0 ? 640 + index * 20 : 0,
    summary:
      index === 2
        ? "Stopped with incomplete fixture evidence."
        : "Produced a validated illustrative artifact.",
  }));
}

export const agents: AgentRecord[] = [
  {
    id: "research-agent",
    name: "Market reaction research",
    role: "Turns normalized catalysts and market context into evidence-backed reaction reports.",
    cadence: "On normalized market event",
    model: "demo-reasoning-model",
    promptVersion: "reaction-research@1.4",
    description:
      "Compares observed moves with synthetic analogs and reports uncertainty without proposing a trade.",
    dependencies: ["News gateway", "Historical bars gateway", "Analog fixture store"],
    runs: runsFor("research", 3240),
  },
  {
    id: "proposal-agent",
    name: "Trade proposal",
    role: "Creates structured candidates or a successful NO_TRADE outcome.",
    cadence: "After validated research",
    model: "demo-reasoning-model",
    promptVersion: "proposal@1.3",
    description:
      "Expresses bounded intent and ShadowFund candidates but never claims authorization.",
    dependencies: ["Research artifact", "Synthetic portfolio snapshot", "Option resolver fixture"],
    runs: runsFor("proposal", 2810),
  },
  {
    id: "risk-agent",
    name: "Risk AI",
    role: "Challenges a candidate with contradictory evidence and portfolio context.",
    cadence: "After candidate proposal",
    model: "demo-fast-model",
    promptVersion: "risk-critique@1.2",
    description: "Provides independent critique; deterministic rules retain final authority.",
    dependencies: ["Proposal artifact", "Portfolio fixture", "Volatility fixture"],
    runs: runsFor("risk", 1910),
  },
  {
    id: "post-analysis-agent",
    name: "Post-analysis",
    role: "Reviews completed ShadowFund branches and surfaces profile recommendations.",
    cadence: "Daily after completed sessions",
    model: "demo-reasoning-model",
    promptVersion: "post-analysis@1.1",
    description:
      "Explains decision regret and possible improvements without activating configuration.",
    dependencies: ["ShadowFund fixture evaluator", "Audit fixture store"],
    runs: runsFor("post-analysis", 3560),
  },
];

export const tools: ToolRecord[] = [
  {
    id: "news-sdk",
    name: "Alpaca News gateway",
    kind: "SDK",
    state: "used",
    calls: 18,
    successRate: "94%",
    medianLatency: "184 ms",
    purpose: "Planned read-only catalyst ingestion; fixtures only in this prototype.",
  },
  {
    id: "bars-sdk",
    name: "Historical bars gateway",
    kind: "SDK",
    state: "used",
    calls: 24,
    successRate: "96%",
    medianLatency: "221 ms",
    purpose: "Planned read-only market context; fixtures only in this prototype.",
  },
  {
    id: "rules",
    name: "Deterministic rules evaluator",
    kind: "Internal",
    state: "used",
    calls: 11,
    successRate: "100%",
    medianLatency: "18 ms",
    purpose: "Illustrative PASS, MODIFY, and FAIL traces.",
  },
  {
    id: "llm",
    name: "Provider-neutral LLM adapter",
    kind: "LLM",
    state: "used",
    calls: 31,
    successRate: "90%",
    medianLatency: "3.8 s",
    purpose: "Structured demo research, proposal, risk, and post-analysis outputs.",
  },
  {
    id: "alpaca-mcp",
    name: "Alpaca research MCP",
    kind: "MCP",
    state: "planned",
    calls: 0,
    successRate: "Not used",
    medianLatency: "Not recorded",
    purpose: "Read-only developer investigation; no runtime invocation is represented.",
  },
];

export function loadAgentObservability(range: DateRange) {
  const filtered = agents.map((agent) => ({
    ...agent,
    runs: agent.runs.filter((run) => inRange(run.occurredAt, range)),
  }));
  return { agents: filtered, tools };
}

export function getAgent(id: string) {
  return agents.find((agent) => agent.id === id);
}

export const newsRecords: NewsRecord[] = [
  {
    id: "news-acme",
    publishedAt: "2026-08-25T14:30:00Z",
    source: "Illustrative Market Wire",
    provider: "Alpaca News-shaped fixture",
    symbols: ["ACME"],
    headline: "ACME fictional earnings update arrives above the synthetic comparison set",
    summary:
      "A deterministic article fixture used to demonstrate catalyst linkage and event-time filtering.",
    category: "Earnings",
    storyId: "acme-earnings-gap",
    significance: "high",
  },
  {
    id: "news-nova",
    publishedAt: "2026-08-21T16:10:00Z",
    source: "Illustrative Business Desk",
    provider: "Alpaca News-shaped fixture",
    symbols: ["NOVA"],
    headline: "NOVA announces a fictional product milestone",
    summary:
      "The synthetic market response already reflected the headline by the time research completed.",
    category: "Product",
    storyId: "nova-product-no-trade",
    significance: "medium",
  },
  {
    id: "news-orbt",
    publishedAt: "2026-08-12T13:05:00Z",
    source: "Illustrative Macro Desk",
    provider: "Alpaca News-shaped fixture",
    symbols: ["ORBT"],
    headline: "Synthetic macro release changes the sector context",
    summary: "Comparison bars were intentionally incomplete to exercise a degraded workflow.",
    category: "Macro",
    storyId: "orbt-macro-incomplete",
    significance: "high",
  },
  {
    id: "news-vela",
    publishedAt: "2026-07-29T15:20:00Z",
    source: "Illustrative Market Wire",
    provider: "Alpaca News-shaped fixture",
    symbols: ["VELA"],
    headline: "VELA raises fictional guidance for the next reporting period",
    summary: "A bounded fixture scenario connected to a PASS story and ShadowFund comparison.",
    category: "Guidance",
    storyId: "vela-guidance-pass",
    significance: "high",
  },
  {
    id: "news-kite",
    publishedAt: "2026-07-08T14:42:00Z",
    source: "Illustrative Corporate Desk",
    provider: "Alpaca News-shaped fixture",
    symbols: ["KITE"],
    headline: "KITE files a fictional corporate-action update",
    summary:
      "The story demonstrates why a plausible thesis can still fail on missing liquidity configuration.",
    category: "Corporate action",
    storyId: "kite-liquidity-fail",
    significance: "medium",
  },
  {
    id: "news-heli",
    publishedAt: "2026-05-19T17:15:00Z",
    source: "Illustrative Sector Desk",
    provider: "Alpaca News-shaped fixture",
    symbols: ["HELI"],
    headline: "Synthetic sector rotation lifts multiple fictional names",
    summary: "The wider move weakened the single-name explanation and produced NO_TRADE.",
    category: "Sector",
    storyId: "heli-sector-rotation",
    significance: "low",
  },
  {
    id: "news-acme-old",
    publishedAt: "2026-03-11T14:05:00Z",
    source: "Illustrative Business Desk",
    provider: "Alpaca News-shaped fixture",
    symbols: ["ACME"],
    headline: "Conflicting fictional guidance sources create an incomplete evidence set",
    summary: "The fixture retains source disagreement rather than collapsing it into certainty.",
    category: "Guidance",
    storyId: "acme-guidance-review",
    significance: "medium",
  },
];

export function listNews(
  range: DateRange,
  filters: { symbol?: string; significance?: string } = {},
) {
  return newsRecords.filter(
    (record) =>
      inRange(record.publishedAt, range) &&
      (!filters.symbol || filters.symbol === "all" || record.symbols.includes(filters.symbol)) &&
      (!filters.significance ||
        filters.significance === "all" ||
        record.significance === filters.significance),
  );
}

export const hardRules = [
  {
    name: "Paper environment only",
    explanation: "Any live configuration stops startup or execution.",
  },
  {
    name: "Deterministic authorization",
    explanation: "Agent output can inform a proposal but cannot authorize it.",
  },
  {
    name: "Supported option envelope",
    explanation: "Only documented long options and defined-risk debit spreads may progress.",
  },
  {
    name: "Exact payload binding",
    explanation: "Any modified payload requires a new digest and authorization.",
  },
  {
    name: "ShadowFund isolation",
    explanation: "Simulated branches cannot submit, amend, or cancel an order.",
  },
];

export const configurableRules: ConfigurableRule[] = [
  {
    id: "concentration",
    name: "Position concentration",
    description: "Limits how much of the paper portfolio one governed idea may represent.",
    input: "Proposed exposure ÷ observed portfolio equity",
    unit: "% of equity",
    activeValue: "TBD",
    effect:
      "PASS below the approved limit; otherwise MODIFY or FAIL as the approved ruleset specifies.",
  },
  {
    id: "freshness",
    name: "Evidence freshness",
    description: "Defines how old required market and account observations may be.",
    input: "Decision time − received observation time",
    unit: "seconds",
    activeValue: "TBD",
    effect: "Missing or stale required evidence fails closed.",
  },
  {
    id: "liquidity",
    name: "Liquidity floor",
    description: "Requires an approved minimum quality for synthetic quote and volume evidence.",
    input: "Spread width, quote quality, and volume inputs",
    unit: "policy value",
    activeValue: "TBD",
    effect: "Insufficient evidence rejects the candidate rather than assuming a favorable fill.",
  },
  {
    id: "confidence",
    name: "Research confidence",
    description: "Defines the minimum validated confidence required before proposal generation.",
    input: "Validated research confidence",
    unit: "decimal 0–1",
    activeValue: "TBD",
    effect: "Low confidence produces NO_TRADE or FAIL according to the approved ruleset.",
  },
  {
    id: "drawdown",
    name: "Portfolio drawdown response",
    description: "Controls when new risk must be reduced or blocked after portfolio losses.",
    input: "Current equity versus approved peak reference",
    unit: "% drawdown",
    activeValue: "TBD",
    effect: "The approved policy may MODIFY size or FAIL new proposals.",
  },
];

export const ruleVersions = [
  {
    version: "demo-draft.3",
    state: "Draft",
    changedAt: "2026-08-26T10:00:00Z",
    summary: "User-editable prototype fields; not active.",
  },
  {
    version: "platform-controls.1",
    state: "Enforced",
    changedAt: "2026-08-01T00:00:00Z",
    summary: "Immutable platform safety controls.",
  },
  {
    version: "demo-draft.2",
    state: "Superseded demo",
    changedAt: "2026-07-18T09:20:00Z",
    summary: "Illustrative history only.",
  },
];

export function loadDashboard(range: DateRange) {
  const stories = listStories(range);
  const portfolio = loadPortfolio(range);
  const observability = loadAgentObservability(range);
  const tokenTotal = observability.agents.reduce(
    (total, agent) =>
      total +
      agent.runs.reduce(
        (agentTotal, run) => agentTotal + run.inputTokens + run.outputTokens + run.cachedTokens,
        0,
      ),
    0,
  );
  const outcomes = ["pass", "modify", "fail", "no_trade", "degraded"].map((outcome) => ({
    label: outcome.replace("_", " "),
    value: String(stories.filter((story) => story.outcome === outcome).length),
  }));
  return {
    stories,
    portfolio,
    tokenTotal,
    outcomes,
    recommendations: [
      "Show freshness gaps before the research summary is accepted.",
      "Prefer bounded spread structures when synthetic volatility is elevated.",
      "Promote no-action outcomes when every comparable branch loses value.",
    ],
  };
}

export const legacyStoryLookup: Record<string, string> = {
  "10000000-0000-4000-8000-000000000001": "acme-earnings-gap",
  "20000000-0000-4000-8000-000000000001": "acme-earnings-gap",
  "60000000-0000-4000-8000-000000000001": "acme-earnings-gap",
  "00000000-0000-4000-8000-000000000001": "acme-earnings-gap",
};

export const legacyAlternativeLookup: Record<string, string> = {
  "70000000-0000-4000-8000-000000000001": "session-acme-earnings",
};
