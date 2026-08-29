import { redirect } from "next/navigation";

import { legacyStoryLookup } from "@/features/story/story-data";

export default async function LegacyProposalDetail({
  params,
}: {
  params: Promise<{ proposalId: string }>;
}) {
  const { proposalId } = await params;
  redirect(
    legacyStoryLookup[proposalId] ? `/stories/${legacyStoryLookup[proposalId]}` : "/stories",
  );
}
