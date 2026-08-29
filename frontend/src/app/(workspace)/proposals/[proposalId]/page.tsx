import { redirect } from "next/navigation";

import { legacyStoryLookup } from "@/features/story/presentation-api";

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
