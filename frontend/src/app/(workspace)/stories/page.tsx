import { PageHeader } from "@/components/product/workspace-ui";
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
      <div className="result-count" role="status">
        {stories.length} illustrative {stories.length === 1 ? "story" : "stories"}
      </div>
      <StoryList stories={stories} />
    </>
  );
}
