import { describe, expect, it } from "vitest";

import {
  getStory,
  listAlternativeSessions,
  listNews,
  listStories,
  loadAgentObservability,
  readDateRange,
} from "@/features/story/story-data";

describe("story fixture repository", () => {
  it("FRS-019 filters every narrative collection with the same custom UTC range", () => {
    const range = readDateRange({ range: "custom", from: "2026-08-20", to: "2026-08-28" });
    expect(listStories(range).map((story) => story.id)).toEqual([
      "acme-earnings-gap",
      "nova-product-no-trade",
    ]);
    expect(listAlternativeSessions(range)).toHaveLength(2);
    expect(listNews(range)).toHaveLength(2);
  });

  it("FRS-019 keeps all six authority-ordered story chapters available", () => {
    const story = getStory("acme-earnings-gap");
    expect(story).toBeDefined();
    expect(story?.decisionTree.map((node) => node.actor)).toEqual([
      "Market context",
      "Research agent",
      "Proposal agent",
      "Risk AI",
      "Rules engine",
    ]);
    expect(story?.transcript.every((step) => step.summary.length > 0)).toBe(true);
    expect(story?.lessons).toHaveLength(3);
    expect(getStory("unknown-story")).toBeUndefined();
  });

  it("FRS-022 distinguishes planned MCP capability from recorded fixture use", () => {
    const observability = loadAgentObservability(
      readDateRange({ range: "ytd", from: "2026-01-01", to: "2026-08-28" }),
    );
    const mcp = observability.tools.find((tool) => tool.kind === "MCP");
    expect(mcp).toMatchObject({ state: "planned", calls: 0, successRate: "Not used" });
  });

  it("NFRS-003 falls back from invalid custom dates to the deterministic one-month range", () => {
    expect(readDateRange({ range: "custom", from: "2026-08-29", to: "2026-08-28" })).toEqual({
      preset: "1m",
      from: "2026-07-29",
      to: "2026-08-28",
    });
  });
});
