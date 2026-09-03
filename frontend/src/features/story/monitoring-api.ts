import { cookies } from "next/headers";

import { apiRangeQuery, rangeForPreset, type DateRange } from "@/features/story/date-range";
import type { components } from "@/types/api.generated";

export type Provenance = components["schemas"]["Provenance"];
export type StorySummary = components["schemas"]["StorySummary"];
export type StoryDetail = components["schemas"]["StoryDetail"];
export type AgentPerspective = components["schemas"]["AgentPerspective"];
export type ChartPoint = components["schemas"]["ChartPoint"];
export type Portfolio = components["schemas"]["Portfolio"];
export type AlternativeSession = components["schemas"]["AlternativeSession"];
export type AlternativeCollection = components["schemas"]["AlternativeCollection"];
export type MonitoringDataMode = components["schemas"]["DataMode"];
export type AgentRecord = components["schemas"]["AgentRecord"];
export type AgentObservability = components["schemas"]["AgentObservability"];
export type NewsRecord = components["schemas"]["NewsRecord"];
export type Governance = components["schemas"]["Governance"];
export type WeeklySummary = components["schemas"]["WeeklySummary"];

type OverviewEnvelope = components["schemas"]["PresentationEnvelope_Overview_"];
type DecisionsEnvelope = components["schemas"]["PresentationEnvelope_DecisionCollection_"];
type DecisionEnvelope = components["schemas"]["PresentationEnvelope_StoryDetail_"];
type PortfolioEnvelope = components["schemas"]["PresentationEnvelope_Portfolio_"];
type AlternativesEnvelope = components["schemas"]["PresentationEnvelope_AlternativeCollection_"];
type AlternativeEnvelope = components["schemas"]["PresentationEnvelope_AlternativeSession_"];
type AgentsEnvelope = components["schemas"]["PresentationEnvelope_AgentObservability_"];
type AgentEnvelope = components["schemas"]["PresentationEnvelope_AgentRecord_"];
type NewsEnvelope = components["schemas"]["PresentationEnvelope_NewsCollection_"];
type GovernanceEnvelope = components["schemas"]["PresentationEnvelope_Governance_"];
type WeeklySummaryEnvelope = components["schemas"]["PresentationEnvelope_WeeklySummary_"];

export class MonitoringApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

function apiBaseUrl() {
  return process.env.API_INTERNAL_URL ?? "http://localhost:8000/api/v1";
}

async function apiGet<T>(path: string, query?: Record<string, string | undefined>): Promise<T> {
  const session = (await cookies()).get("prism_session")?.value;
  if (!session) throw new MonitoringApiError("Authentication required", 401);
  const url = new URL(`${apiBaseUrl()}${path}`);
  Object.entries(query ?? {}).forEach(([key, value]) => {
    if (value) url.searchParams.set(key, value);
  });
  const response = await fetch(url, {
    headers: { Cookie: `prism_session=${encodeURIComponent(session)}` },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new MonitoringApiError(
      response.status === 404 ? "Recorded monitoring data not found" : "Monitoring API unavailable",
      response.status,
    );
  }
  return (await response.json()) as T;
}

export async function loadDashboard(range: DateRange) {
  const envelope = await apiGet<OverviewEnvelope>("/monitoring/overview", apiRangeQuery(range));
  // Keep the server's as-of/generated timestamp beside the projection so the
  // Overview can show an honest "Checked at (UTC)" instead of a client clock.
  return { ...envelope.data, asOf: envelope.meta.asOf };
}

export async function listStories(
  range: DateRange,
  filters: { outcome?: string; symbol?: string } = {},
) {
  return (
    await apiGet<DecisionsEnvelope>("/monitoring/decisions", {
      ...apiRangeQuery(range),
      ...filters,
    })
  ).data;
}

export async function getStory(id: string) {
  try {
    return (await apiGet<DecisionEnvelope>(`/monitoring/decisions/${id}`)).data;
  } catch (error) {
    if (error instanceof MonitoringApiError && error.status === 404) return null;
    throw error;
  }
}

export async function loadPortfolio(range: DateRange) {
  return (await apiGet<PortfolioEnvelope>("/monitoring/portfolio", apiRangeQuery(range))).data;
}

export async function listAlternativeSessions(range: DateRange) {
  const envelope = await apiGet<AlternativesEnvelope>(
    "/monitoring/alternatives",
    apiRangeQuery(range),
  );
  // Keep the server-reported mode beside the projection. The client must not
  // infer production from a build-time environment variable: the API is the
  // authoritative provenance boundary for monitoring data.
  return { ...envelope.data, dataMode: envelope.meta.dataMode } as AlternativeCollection & {
    dataMode: MonitoringDataMode;
  };
}

export async function getAlternativeSession(id: string) {
  try {
    return (await apiGet<AlternativeEnvelope>(`/monitoring/alternatives/${id}`)).data;
  } catch (error) {
    if (error instanceof MonitoringApiError && error.status === 404) return null;
    throw error;
  }
}

export async function loadAgentObservability(range: DateRange) {
  return (await apiGet<AgentsEnvelope>("/monitoring/agents", apiRangeQuery(range))).data;
}

export async function getAgent(id: string, range = rangeForPreset("1m")) {
  try {
    return (await apiGet<AgentEnvelope>(`/monitoring/agents/${id}`, apiRangeQuery(range))).data;
  } catch (error) {
    if (error instanceof MonitoringApiError && error.status === 404) return null;
    throw error;
  }
}

export async function listNews(
  range: DateRange,
  filters: { symbol?: string; significance?: string } = {},
) {
  return (await apiGet<NewsEnvelope>("/monitoring/news", { ...apiRangeQuery(range), ...filters }))
    .data;
}

export async function getGovernance() {
  return (await apiGet<GovernanceEnvelope>("/monitoring/governance")).data;
}

export async function getWeeklySummary() {
  return (await apiGet<WeeklySummaryEnvelope>("/monitoring/weekly-summary")).data;
}

export type MarketBar = components["schemas"]["MarketBar"];
export type MarketBarsData = components["schemas"]["MarketBarsData"];
type MarketBarsEnvelope = components["schemas"]["PresentationEnvelope_MarketBarsData_"];

export async function loadMarketBars(
  symbol = "NVDA",
  timeframe = "1Day",
  limit = 30,
): Promise<MarketBarsData> {
  const envelope = await apiGet<MarketBarsEnvelope>("/monitoring/market-bars", {
    symbol,
    timeframe,
    limit: String(limit),
  });
  return envelope.data;
}
