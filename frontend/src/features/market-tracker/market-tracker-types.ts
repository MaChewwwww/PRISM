export const marketActivityKinds = [
  {
    id: "fill",
    label: "Verified fills",
    description: "Confirmed Alpaca paper fills only",
    color: "#00D084",
  },
  {
    id: "order",
    label: "Orders",
    description: "Paper order lifecycle",
    color: "#10B981",
  },
  {
    id: "proposal",
    label: "Proposals",
    description: "Trading Decision proposals",
    color: "#38BDF8",
  },
  {
    id: "decision",
    label: "Decisions",
    description: "Authorized or rejected decisions",
    color: "#547D83",
  },
  {
    id: "no_trade",
    label: "NO_TRADE",
    description: "Terminal no-action decisions",
    color: "#94A3B8",
  },
  {
    id: "shadow",
    label: "ShadowFund",
    description: "Simulated branch events",
    color: "#818CF8",
  },
] as const;

export type MarketActivityKind = (typeof marketActivityKinds)[number]["id"];

export const marketTimeframes = ["1Min", "5Min", "15Min", "1Hour", "1Day"] as const;
export type MarketTimeframe = (typeof marketTimeframes)[number];

export function isVerifiedTrade(kind: MarketActivityKind) {
  return kind === "fill";
}
