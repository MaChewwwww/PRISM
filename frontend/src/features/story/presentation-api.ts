import { cookies } from "next/headers";

import { apiRangeQuery, type DateRange } from "@/features/story/date-range";
import type { components } from "@/types/api.generated";

export type Provenance = components["schemas"]["Provenance"];
export type StorySummary = components["schemas"]["StorySummary"];
export type StoryDetail = components["schemas"]["StoryDetail"];
export type ChartPoint = components["schemas"]["ChartPoint"];
export type Portfolio = components["schemas"]["Portfolio"];
export type AlternativeSession = components["schemas"]["AlternativeSession"];
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

export class PresentationApiError extends Error {
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
  if (!session) throw new PresentationApiError("Authentication required", 401);
  const url = new URL(`${apiBaseUrl()}${path}`);
  Object.entries(query ?? {}).forEach(([key, value]) => {
    if (value) url.searchParams.set(key, value);
  });
  const response = await fetch(url, {
    headers: { Cookie: `prism_session=${encodeURIComponent(session)}` },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new PresentationApiError(
      response.status === 404 ? "Presentation record not found" : "Presentation API unavailable",
      response.status,
    );
  }
  return (await response.json()) as T;
}

export async function loadDashboard(range: DateRange) {
  return (await apiGet<OverviewEnvelope>("/presentation/overview", apiRangeQuery(range))).data;
}

export async function listStories(
  range: DateRange,
  filters: { outcome?: string; symbol?: string } = {},
) {
  const envelope = await apiGet<DecisionsEnvelope>("/presentation/decisions", {
    ...apiRangeQuery(range),
    ...filters,
  });
  return envelope.data;
}

export async function getStory(id: string) {
  try {
    return (await apiGet<DecisionEnvelope>(`/presentation/decisions/${id}`)).data;
  } catch (error) {
    if (error instanceof PresentationApiError && error.status === 404) return null;
    throw error;
  }
}

export async function loadPortfolio(range: DateRange) {
  return (await apiGet<PortfolioEnvelope>("/presentation/portfolio", apiRangeQuery(range))).data;
}

export async function listAlternativeSessions(range: DateRange) {
  return (await apiGet<AlternativesEnvelope>("/presentation/alternatives", apiRangeQuery(range)))
    .data;
}

export async function getAlternativeSession(id: string) {
  try {
    return (await apiGet<AlternativeEnvelope>(`/presentation/alternatives/${id}`)).data;
  } catch (error) {
    if (error instanceof PresentationApiError && error.status === 404) return null;
    throw error;
  }
}

export async function loadAgentObservability(range: DateRange) {
  return (await apiGet<AgentsEnvelope>("/presentation/agents", apiRangeQuery(range))).data;
}

export async function getAgent(id: string) {
  try {
    return (await apiGet<AgentEnvelope>(`/presentation/agents/${id}`)).data;
  } catch (error) {
    if (error instanceof PresentationApiError && error.status === 404) return null;
    throw error;
  }
}

export async function listNews(
  range: DateRange,
  filters: { symbol?: string; significance?: string } = {},
) {
  return (
    await apiGet<NewsEnvelope>("/presentation/news", {
      ...apiRangeQuery(range),
      ...filters,
    })
  ).data;
}

export async function getGovernance() {
  return (await apiGet<GovernanceEnvelope>("/presentation/governance")).data;
}

export async function getWeeklySummary() {
  return (await apiGet<WeeklySummaryEnvelope>("/presentation/weekly-summary")).data;
}
