import { ArrowUpRight } from "lucide-react";
import Link from "next/link";

import { StateBadge } from "@/components/product/workspace-ui";
import { formatDate } from "@/features/story/formatters";
import type { StorySummary } from "@/features/story/story-data";

export function StoryList({ stories }: { stories: StorySummary[] }) {
  if (stories.length === 0) {
    return (
      <div className="inline-empty">
        <strong>No decision stories in this range.</strong>
        <span>Choose a wider period or clear the outcome and symbol filters.</span>
      </div>
    );
  }

  return (
    <ol className="story-list">
      {stories.map((story, index) => (
        <li
          key={story.id}
          className="prism-glass-interactive transition-all hover:-translate-y-0.5"
        >
          <div className="story-index font-mono" aria-hidden="true">
            {String(index + 1).padStart(2, "0")}
          </div>
          <div className="story-copy">
            <div className="story-kicker">
              <time dateTime={story.occurredAt}>{formatDate(story.occurredAt)}</time>
              <span className="font-semibold text-[#38BDF8]">{story.symbol}</span>
              <span>{story.category}</span>
            </div>
            <h3>
              <Link
                href={`/stories/${story.id}`}
                className="hover:text-[#547D83] transition-colors"
              >
                {story.title}
              </Link>
            </h3>
            <p>{story.summary}</p>
            <div className="story-lesson">
              <strong>Key Insight</strong>
              <span>{story.lesson}</span>
            </div>
          </div>
          <div className="story-result">
            <StateBadge state={story.outcome} />
            <dl>
              <div>
                <dt>Active Outcome</dt>
                <dd className="font-mono tabular-nums font-semibold text-[#00D084]">
                  {story.paperImpact}
                </dd>
              </div>
              <div>
                <dt>Best Shadow Path</dt>
                <dd className="font-mono tabular-nums text-[#818CF8]">
                  {story.bestAlternativeImpact}
                </dd>
              </div>
            </dl>
            <Link
              href={`/stories/${story.id}`}
              aria-label={`Open ${story.title}`}
              className="icon-link group"
            >
              <ArrowUpRight
                aria-hidden="true"
                className="transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
              />
            </Link>
          </div>
        </li>
      ))}
    </ol>
  );
}
