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
        <li key={story.id}>
          <div className="story-index" aria-hidden="true">
            {String(index + 1).padStart(2, "0")}
          </div>
          <div className="story-copy">
            <div className="story-kicker">
              <time dateTime={story.occurredAt}>{formatDate(story.occurredAt)}</time>
              <span>{story.symbol}</span>
              <span>{story.category}</span>
            </div>
            <h3>
              <Link href={`/stories/${story.id}`}>{story.title}</Link>
            </h3>
            <p>{story.summary}</p>
            <div className="story-lesson">
              <strong>Lesson</strong>
              <span>{story.lesson}</span>
            </div>
          </div>
          <div className="story-result">
            <StateBadge state={story.outcome} />
            <dl>
              <div>
                <dt>Paper result</dt>
                <dd>{story.paperImpact}</dd>
              </div>
              <div>
                <dt>Best alternative</dt>
                <dd>{story.bestAlternativeImpact}</dd>
              </div>
            </dl>
            <Link href={`/stories/${story.id}`} aria-label={`Open ${story.title}`}>
              <ArrowUpRight aria-hidden="true" />
            </Link>
          </div>
        </li>
      ))}
    </ol>
  );
}
