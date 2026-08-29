import { beforeEach, describe, expect, it, vi } from "vitest";

import LegacyProposalDetail from "@/app/(workspace)/proposals/[proposalId]/page";
import LegacyResearchPage from "@/app/(workspace)/research/page";
import LegacyShadowFundDetail from "@/app/(workspace)/shadowfund/[sessionId]/page";

const redirectMock = vi.hoisted(() => vi.fn());

vi.mock("next/navigation", () => ({ redirect: redirectMock }));

describe("legacy story-first redirects", () => {
  beforeEach(() => redirectMock.mockClear());

  it("FRS-019 sends legacy entity indexes to the story library", () => {
    LegacyResearchPage();
    expect(redirectMock).toHaveBeenCalledWith("/stories");
  });

  it("FRS-019 maps known legacy proposal identifiers to their decision story", async () => {
    await LegacyProposalDetail({
      params: Promise.resolve({ proposalId: "20000000-0000-4000-8000-000000000001" }),
    });
    expect(redirectMock).toHaveBeenCalledWith("/stories/acme-earnings-gap");
  });

  it("FRS-018 maps known ShadowFund identifiers to the alternatives workspace", async () => {
    await LegacyShadowFundDetail({
      params: Promise.resolve({ sessionId: "70000000-0000-4000-8000-000000000001" }),
    });
    expect(redirectMock).toHaveBeenCalledWith("/alternatives/session-acme-earnings");
  });
});
