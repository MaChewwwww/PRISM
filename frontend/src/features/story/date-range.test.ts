import { describe, expect, it } from "vitest";

import { apiRangeQuery, readDateRange } from "@/features/story/date-range";

describe("shared UTC date range", () => {
  it("FRS-019 preserves a valid custom range", () => {
    expect(
      readDateRange({ range: "custom", from: "2026-08-20", to: "2026-08-28" }, "2026-08-28"),
    ).toEqual({
      preset: "custom",
      from: "2026-08-20",
      to: "2026-08-28",
      timezone: "UTC",
    });
  });

  it("NFRS-003 rejects reversed custom dates and uses the anchored one-month range", () => {
    expect(
      readDateRange({ range: "custom", from: "2026-08-29", to: "2026-08-28" }, "2026-08-28"),
    ).toEqual({
      preset: "1m",
      from: "2026-07-29",
      to: "2026-08-28",
      timezone: "UTC",
    });
  });

  it("sends timezone-aware UTC timestamps to presentation APIs", () => {
    const range = readDateRange(
      { range: "custom", from: "2026-08-20", to: "2026-08-28" },
      "2026-08-28",
    );
    expect(apiRangeQuery(range)).toEqual({
      from: "2026-08-20T00:00:00Z",
      to: "2026-08-28T23:59:59Z",
    });
  });
});
