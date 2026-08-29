import { redirect } from "next/navigation";

import { legacyStoryLookup } from "@/features/story/presentation-api";

export default async function LegacyResearchDetail({
  params,
}: {
  params: Promise<{ researchId: string }>;
}) {
  const { researchId } = await params;
  redirect(
    legacyStoryLookup[researchId] ? `/stories/${legacyStoryLookup[researchId]}` : "/stories",
  );
}
