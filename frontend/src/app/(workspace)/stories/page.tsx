import { Network } from "lucide-react";

import { PageHeader } from "@/components/workspace/workspace-ui";
import { RangePresets } from "@/components/workspace/range-presets";
import { readDateRange, type SearchValues } from "@/features/story/date-range";
import { listStories } from "@/features/story/presentation-api";
import { StoryList } from "@/features/story/story-list";

export default async function StoriesPage({
  searchParams,
}: {
  searchParams: Promise<SearchValues>;
}) {
  const values = await searchParams;
  const range = readDateRange(values);
  const collection = await listStories(range);
  const stories = collection.stories;

  return (
    <>
      <PageHeader
        eyebrow="Decision log"
        title="Decision Stories"
        description="A scannable feed of the narrative takeaway and the counterfactual impact behind every call the agent stack made."
      />

      <section aria-labelledby="story-feed" className="mt-6">
        <StoryList
          stories={stories}
          rangeControl={<RangePresets range={range} />}
          heading={
            <div>
              <h2
                id="story-feed"
                className="flex items-center gap-2.5 text-lg font-semibold tracking-tight text-[#F8FAFC]"
              >
                <span className="grid h-7 w-7 shrink-0 place-items-center rounded-md border border-[#547D83]/40 bg-[#547D83]/20 text-[#B2D8DC]">
                  <Network className="h-3.5 w-3.5" aria-hidden="true" />
                </span>
                Decision Feed
              </h2>
              <p className="mt-1 text-[12px] text-[#64748B]">
                {stories.length} illustrative {stories.length === 1 ? "story" : "stories"} in this
                range.
              </p>
            </div>
          }
        />
      </section>
    </>
  );
}
