export type OverviewRange = "7D" | "1M" | "3M" | "YTD";

export type Decision = {
  title: string;
  perspective: string;
  outcome: "Positive" | "Neutral" | "Negative";
  paper: number;
  alt: number;
  storyId?: string;
};

export type OverviewPoint = {
  date: string;
  time: string;
  actual: number;
  alt: number;
  bench: number;
  decision: Decision | null;
  tokens: number;
};

export type RecentDecision = {
  sym: string;
  date: string;
  title: string;
  reasoning: string;
  outcome: "Modify" | "Pass" | "No trade";
  paper: number;
  alt: number;
  agent: "risk" | "proposal" | "research";
  agentLabel: string;
};

export type Outcome = {
  label: "Positive" | "Neutral" | "Negative";
  count: number;
  color: string;
};

export type Exposure = {
  label: string;
  pct: number;
};

/** Percent change of `value` relative to `base`, guarding against a zero base. */
export function percentChange(base: number, value: number) {
  if (base === 0) return 0;
  return ((value - base) / base) * 100;
}

export function formatCurrency(value: number) {
  return `$${Math.round(value).toLocaleString()}`;
}

export function formatSignedCurrency(value: number) {
  const rounded = Math.round(value);
  return `${rounded >= 0 ? "+" : "-"}$${Math.abs(rounded).toLocaleString()}`;
}

export function formatSignedPercent(value: number) {
  return `${value >= 0 ? "+" : ""}${value.toFixed(1)}%`;
}

export const overviewDatasets: Record<OverviewRange, OverviewPoint[]> = {
  "7D": [
    {
      date: "Aug 23",
      time: "9:30 AM",
      actual: 101900,
      alt: 102400,
      bench: 101200,
      decision: null,
      tokens: 2100,
    },
    {
      date: "Aug 24",
      time: "2:30 PM",
      actual: 104820,
      alt: 106140,
      bench: 103910,
      decision: {
        title: "Increased AAPL position",
        perspective: "Earnings momentum",
        outcome: "Positive",
        paper: 1240,
        alt: 1610,
      },
      tokens: 8400,
    },
    {
      date: "Aug 25",
      time: "11:00 AM",
      actual: 103900,
      alt: 106900,
      bench: 104100,
      decision: null,
      tokens: 1800,
    },
    {
      date: "Aug 26",
      time: "1:15 PM",
      actual: 104500,
      alt: 107600,
      bench: 104300,
      decision: null,
      tokens: 2300,
    },
    {
      date: "Aug 27",
      time: "10:05 AM",
      actual: 106060,
      alt: 107890,
      bench: 104550,
      decision: {
        title: "Trimmed NVDA on volatility spike",
        perspective: "Risk containment",
        outcome: "Positive",
        paper: 1240,
        alt: 1890,
      },
      tokens: 9200,
    },
    {
      date: "Aug 28",
      time: "3:40 PM",
      actual: 105300,
      alt: 108100,
      bench: 104700,
      decision: null,
      tokens: 1900,
    },
    {
      date: "Aug 29",
      time: "9:11 AM",
      actual: 105100,
      alt: 108300,
      bench: 101800,
      decision: null,
      tokens: 1500,
    },
  ],

  "1M": [
    {
      date: "Aug 1",
      time: "9:30 AM",
      actual: 100000,
      alt: 100000,
      bench: 100000,
      decision: null,
      tokens: 1600,
    },
    {
      date: "Aug 6",
      time: "2:00 PM",
      actual: 101200,
      alt: 101800,
      bench: 100500,
      decision: null,
      tokens: 1900,
    },
    {
      date: "Aug 11",
      time: "11:20 AM",
      actual: 102500,
      alt: 103200,
      bench: 100900,
      decision: {
        title: "Skipped breakout entry",
        perspective: "Conviction filter",
        outcome: "Negative",
        paper: 0,
        alt: 2100,
      },
      tokens: 7600,
    },
    {
      date: "Aug 16",
      time: "1:45 PM",
      actual: 101800,
      alt: 104100,
      bench: 100600,
      decision: null,
      tokens: 2000,
    },
    {
      date: "Aug 20",
      time: "10:30 AM",
      actual: 103400,
      alt: 105500,
      bench: 101200,
      decision: null,
      tokens: 2200,
    },
    {
      date: "Aug 24",
      time: "2:30 PM",
      actual: 104200,
      alt: 106800,
      bench: 101500,
      decision: {
        title: "Held through delivery miss",
        perspective: "Thesis conviction",
        outcome: "Neutral",
        paper: -310,
        alt: -310,
      },
      tokens: 8900,
    },
    {
      date: "Aug 29",
      time: "9:11 AM",
      actual: 105100,
      alt: 108300,
      bench: 101800,
      decision: null,
      tokens: 1700,
    },
  ],

  "3M": [
    {
      date: "Jun 1",
      time: "9:30 AM",
      actual: 97000,
      alt: 97000,
      bench: 97000,
      decision: null,
      tokens: 2800,
    },
    {
      date: "Jun 20",
      time: "1:00 PM",
      actual: 98600,
      alt: 99400,
      bench: 97900,
      decision: null,
      tokens: 3100,
    },
    {
      date: "Jul 8",
      time: "11:10 AM",
      actual: 100200,
      alt: 101900,
      bench: 98700,
      decision: {
        title: "Rotated out of regional banks",
        perspective: "Macro risk",
        outcome: "Positive",
        paper: 860,
        alt: 1040,
      },
      tokens: 11200,
    },
    {
      date: "Jul 25",
      time: "3:20 PM",
      actual: 99400,
      alt: 103200,
      bench: 99100,
      decision: null,
      tokens: 2600,
    },
    {
      date: "Aug 10",
      time: "10:45 AM",
      actual: 102100,
      alt: 105600,
      bench: 100200,
      decision: null,
      tokens: 3400,
    },
    {
      date: "Aug 29",
      time: "9:11 AM",
      actual: 105100,
      alt: 108300,
      bench: 101800,
      decision: null,
      tokens: 2900,
    },
  ],

  YTD: [
    {
      date: "Jan 1",
      time: "9:30 AM",
      actual: 92000,
      alt: 92000,
      bench: 92000,
      decision: null,
      tokens: 4200,
    },
    {
      date: "Feb 15",
      time: "1:00 PM",
      actual: 93800,
      alt: 94600,
      bench: 92900,
      decision: null,
      tokens: 4800,
    },
    {
      date: "Apr 3",
      time: "11:30 AM",
      actual: 96500,
      alt: 98100,
      bench: 94500,
      decision: {
        title: "Added semiconductor exposure",
        perspective: "Cycle timing",
        outcome: "Positive",
        paper: 2140,
        alt: 2480,
      },
      tokens: 15600,
    },
    {
      date: "Jun 12",
      time: "2:15 PM",
      actual: 98900,
      alt: 102400,
      bench: 96800,
      decision: null,
      tokens: 5100,
    },
    {
      date: "Aug 29",
      time: "9:11 AM",
      actual: 105100,
      alt: 108300,
      bench: 101800,
      decision: null,
      tokens: 4900,
    },
  ],
};

export const recentDecisions: RecentDecision[] = [
  {
    sym: "NVDA",
    date: "Aug 27",
    title: "Trimmed on volatility spike",
    reasoning: '"Risk containment took priority over upside."',
    outcome: "Modify",
    paper: 1240,
    alt: 1890,
    agent: "risk",
    agentLabel: "Risk Agent",
  },
  {
    sym: "TSLA",
    date: "Aug 24",
    title: "Held through delivery miss",
    reasoning: '"Thesis intact despite the quarterly miss."',
    outcome: "Pass",
    paper: -310,
    alt: -310,
    agent: "proposal",
    agentLabel: "Proposal Agent",
  },
  {
    sym: "AVGO",
    date: "Aug 21",
    title: "Skipped breakout entry",
    reasoning: '"Conviction filter wasn\'t met."',
    outcome: "No trade",
    paper: 0,
    alt: 2100,
    agent: "research",
    agentLabel: "Research Agent",
  },
];

export const outcomes: Outcome[] = [
  {
    label: "Positive",
    count: 7,
    color: "#00D084",
  },
  {
    label: "Neutral",
    count: 3,
    color: "#547D83",
  },
  {
    label: "Negative",
    count: 2,
    color: "#FF6B6B",
  },
];

/**
 * Total count of decision stories in the full illustrative journal. This is
 * independent of the selected chart range (it is not "decisions visible in
 * this range"), so it is defined once here rather than being duplicated as a
 * literal in both the sidebar snapshot and the bottom ticker.
 */
export const totalDecisionStories = 12;

export const exposures: Exposure[] = [
  {
    label: "Technology",
    pct: 42,
  },
  {
    label: "Healthcare",
    pct: 24,
  },
  {
    label: "Financials",
    pct: 18,
  },
  {
    label: "Other",
    pct: 16,
  },
];