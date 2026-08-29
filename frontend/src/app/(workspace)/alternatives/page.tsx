import { ArrowUpRight, GitCompareArrows } from "lucide-react";
import Link from "next/link";

import { DateRangeControl } from "@/components/product/date-range-control";
import { DemoDataNotice, PageHeader, StateBadge } from "@/components/product/workspace-ui";
import { formatDate } from "@/features/story/formatters";
import {
  listAlternativeSessions,
  readDateRange,
  type SearchValues,
} from "@/features/story/story-data";

export default async function AlternativesPage({
  searchParams,
}: {
  searchParams: Promise<SearchValues>;
}) {
  const range = readDateRange(await searchParams);
  const sessions = listAlternativeSessions(range);
  return (
    <>
      <PageHeader
        eyebrow="ShadowFund alternatives"
        title="Compare the paths not taken"
        description="Each session changes one controlled assumption and remains simulated, review-only, and non-executable."
      />
      <DemoDataNotice />
      <DateRangeControl range={range} />
      <div className="layer-map" aria-label="ShadowFund analysis layers">
        <div>
          <span>Layer 01</span>
          <h2>Trade-level counterfactuals</h2>
          <p>Paper-shaped, no-action, reduced-size, and unhedged paths.</p>
        </div>
        <div>
          <span>Layer 02</span>
          <h2>Agent alternatives</h2>
          <p>Structured variations extracted with the original fictional proposal.</p>
        </div>
        <div>
          <span>Layer 03</span>
          <h2>Portfolio lessons</h2>
          <p>Repeated branch evidence becomes a review prompt, never an automatic change.</p>
        </div>
      </div>
      {sessions.length > 0 ? (
        <ol className="alternative-list">
          {sessions.map((session) => (
            <li key={session.id}>
              <div className="alternative-mark">
                <GitCompareArrows aria-hidden="true" />
              </div>
              <div>
                <div className="story-kicker">
                  <time>{formatDate(session.occurredAt)}</time>
                  <span>{session.symbol}</span>
                  <StateBadge state="simulated" />
                </div>
                <h2>
                  <Link href={`/alternatives/${session.id}`}>{session.title}</Link>
                </h2>
                <p>{session.summary}</p>
              </div>
              <dl>
                <div>
                  <dt>Paper result</dt>
                  <dd>{session.actualPnl}</dd>
                </div>
                <div>
                  <dt>Best branch</dt>
                  <dd>{session.bestBranch}</dd>
                </div>
                <div>
                  <dt>Delta</dt>
                  <dd>{session.bestDelta}</dd>
                </div>
                <div>
                  <dt>Coverage</dt>
                  <dd>{session.coverage}</dd>
                </div>
              </dl>
              <Link
                className="icon-link"
                href={`/alternatives/${session.id}`}
                aria-label={`Open ${session.title}`}
              >
                <ArrowUpRight aria-hidden="true" />
              </Link>
            </li>
          ))}
        </ol>
      ) : (
        <p className="inline-empty">No completed alternative sessions fall inside this range.</p>
      )}
    </>
  );
}
