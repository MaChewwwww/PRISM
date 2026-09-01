export function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    year: "numeric",
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  }).format(new Date(value.includes("T") ? value : `${value}T00:00:00Z`));
}

export function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
    timeZoneName: "short",
  }).format(new Date(value));
}

export function formatTokens(value: number) {
  return new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 }).format(
    value,
  );
}

/**
 * Plain-language "what if" framing for a ShadowFund branch. ShadowFund answers
 * "what would have happened if the decision were different?", so the UI leads
 * with the question rather than the internal branch name. Keyed off the stable
 * semantic branch key, with a label-based fallback. The key is distinct from
 * the persisted UUID so recorded and simulated sessions use the same labels.
 */
export function branchWhatIf(
  branchKey: string,
  label: string,
): { question: string; plain: string } {
  switch (branchKey) {
    case "chosen":
      return label.toLowerCase().includes("simulated")
        ? { question: "Chosen strategy (simulated)", plain: "Chosen strategy" }
        : { question: "What PRISM actually did", plain: "Active Portfolio" };
    case "cash":
    case "no-action":
      return { question: "What if it had not traded?", plain: "Stay in cash" };
    case "half_size":
    case "reduced-size":
      return { question: "What if it had traded half size?", plain: "Half position (50%)" };
    case "contrarian":
    case "unhedged":
      return { question: "What if the thesis had been reversed?", plain: "Contrarian strategy" };
    case "ai_alternative":
    case "agent-alternative":
      return { question: "What if it used the agent's alternative?", plain: "Agent alternative" };
    default: {
      // Fall back to the raw label, stripping the "Shadow: " prefix if present.
      const plain = label
        .replace(/^Shadow:\s*/i, "")
        .replace("Illustrative governed path", "Active Portfolio");
      return { question: plain, plain };
    }
  }
}

/** Parse a money string like "+$184.00", "$0.00", "-$96.00" into a number. */
export function parseMoney(value: string): number {
  const cleaned = value.replace(/[^0-9.-]/g, "");
  const parsed = Number(cleaned);
  return Number.isFinite(parsed) ? parsed : Number.NaN;
}

/**
 * Human-readable takeaway comparing the best alternative against the chosen
 * path. Returns null when there is nothing meaningful to say. Display-only; it
 * summarizes the existing branch numbers, it does not compute new ones.
 */
export function branchTakeaway(bestPlainLabel: string, bestDelta: string): string | null {
  const delta = parseMoney(bestDelta);
  if (!Number.isFinite(delta) || delta === 0 || bestDelta === "\u2014") {
    return "What PRISM chose was the best available path in this comparison.";
  }
  const amount = `$${Math.abs(delta).toFixed(2)}`;
  if (delta > 0) {
    return `${bestPlainLabel} would have earned ${amount} more.`;
  }
  return `What PRISM chose earned ${amount} more than the best alternative.`;
}

/**
 * Plain-language label for the decision a ShadowFund session studies, derived
 * only from data we actually have (symbol + whether the chosen path traded).
 * We do not invent quantities or structures that are not in the contract.
 */
export function decisionLabel(
  symbol: string,
  chosenPnl: string,
): {
  headline: string;
  question: string;
} {
  const traded = parseMoney(chosenPnl) !== 0;
  if (traded) {
    return {
      headline: `Opened a position in ${symbol}`,
      question: "What if we had made a different choice?",
    };
  }
  return {
    headline: `No trade \u2014 ${symbol}`,
    question: "What if we had taken a different action?",
  };
}

/**
 * Plain-language decision label for a decision story, derived from the real
 * outcome enum and symbol. No quantities or structures are invented; the label
 * only reflects what the outcome tells us actually happened.
 */
export function storyDecisionLabel(symbol: string, outcome: string): string {
  switch (outcome) {
    case "pass":
    case "modify":
      return `Opened a position in ${symbol}`;
    case "no_trade":
      return `No trade \u2014 ${symbol}`;
    case "fail":
      return `Rejected the proposed ${symbol} trade`;
    case "degraded":
      return `Halted \u2014 ${symbol} (incomplete evidence)`;
    case "retrospective":
      return `Success \u2014 ${symbol}`;
    default:
      return symbol;
  }
}
